"""Task tools of offboarding: plan, start, approve, follow. Nothing is removed before an approve."""

from collections import Counter
from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import PERSON_ARG, AgentTool, schema
from app.mcp.agent.views import account_line, action_line, name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

BATCH_ARG = {"type": "string", "description": "batch_id returned by start_offboarding"}
FINISHED = {"done", "failed", "cancelled"}


async def plan_offboarding(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    apps = {app["id"]: app for app in await api.apps()}
    removals, skipped = [], []
    for account in person["accounts"]:
        if account["status"] == "removed":
            continue
        line = account_line(account, apps.get(account["app_id"]))
        (skipped if account["kind"] == "service" else removals).append(line)
    automatic = sum(1 for line in removals if line.get("removal", "").startswith("automatic"))
    return {
        "person": name(person),
        "email": person["primary_email"],
        "status": person["status"],
        "will_remove": removals,
        "skipped_service_accounts": skipped,
        "summary": f"{automatic} account(s) removed automatically, {len(removals) - automatic} manual task(s).",
        "next": (
            "Nothing changed yet. start_offboarding marks the person as left and creates these actions; "
            "they still wait for approve_offboarding."
        ),
    }


async def start_offboarding(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    result = await api.post(f"/people/{person['id']}/offboard")
    return {
        "batch_id": result["batch_id"],
        "person": name(result["person"]),
        "actions": [action_line(action) for action in result["actions"]],
        "skipped": [{"app": item["app"]["name"], "reason": item["reason"]} for item in result["skipped"]],
        "next": (
            "The person is now marked as left. The actions wait for approval: show them to the user and call "
            "approve_offboarding with this batch_id only after a clear yes."
        ),
    }


async def approve_offboarding(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    result = await api.post(f"/actions/batch/{args['batch_id']}/approve")
    return {
        "approved": [action_line(action) for action in result["items"]],
        "not_approved": [{**action_line(item["action"]), "reason": item["reason"]} for item in result["not_approved"]],
        "next": (
            "Removals run in the background and are verified by reading the app's accounts again. "
            "Follow them with get_offboarding_status."
        ),
    }


async def get_offboarding_status(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/actions", batch_id=args["batch_id"], limit=PAGE_LIMIT)
    actions = [action_line(action) for action in page["items"]]
    counts = Counter(action["status"] for action in actions)
    finished = all(action["status"] in FINISHED for action in actions)
    manual_open = any(a["kind"] == "manual_task" and a["status"] not in FINISHED for a in actions)
    return {
        "finished": finished,
        "counts": dict(counts),
        "actions": actions,
        "next": "Manual tasks stay open until an admin removes the account by hand and marks it done in the "
        "panel (Actions)."
        if manual_open
        else None,
    }


async def list_pending_approvals(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/actions", status="pending_approval", limit=PAGE_LIMIT)
    batches: dict[str, dict[str, Any]] = {}
    for action in page["items"]:
        key = action.get("batch_id") or action["id"]
        batch = batches.setdefault(
            key,
            {"batch_id": action.get("batch_id"), "reason": action["reason"], "actions": []},
        )
        batch["actions"].append(action_line(action))
    return {"total": page["total"], "batches": list(batches.values())}


TOOLS = (
    AgentTool(
        name="plan_offboarding",
        title="Plan an offboarding (no changes)",
        description=(
            "What offboarding one person would do, without changing anything: each open account, removed "
            "automatically through the app or as a manual task for an admin. Service accounts are skipped. "
            "Show this to the user before start_offboarding."
        ),
        input_schema=schema({"person": PERSON_ARG}, required=("person",)),
        handler=plan_offboarding,
    ),
    AgentTool(
        name="start_offboarding",
        title="Start an offboarding",
        description=(
            "Marks the person as left and creates one removal action per open account, all waiting for "
            "approval in one batch. Nothing is removed in other apps until approve_offboarding. "
            "Ask the user before calling it."
        ),
        input_schema=schema({"person": PERSON_ARG}, required=("person",)),
        handler=start_offboarding,
        read_only=False,
        destructive=True,
    ),
    AgentTool(
        name="approve_offboarding",
        title="Approve an offboarding batch",
        description=(
            "Runs the removals of one batch: accounts are really removed or suspended in other apps, manual "
            "tasks go to the admins. Only after the user said yes to the list from start_offboarding."
        ),
        input_schema=schema({"batch_id": BATCH_ARG}, required=("batch_id",)),
        handler=approve_offboarding,
        read_only=False,
        destructive=True,
    ),
    AgentTool(
        name="get_offboarding_status",
        title="Offboarding progress",
        description=(
            "Status of every action in one batch (pending_approval, running, verifying, done, failed) and "
            "whether the batch is finished. A failed action has its error."
        ),
        input_schema=schema({"batch_id": BATCH_ARG}, required=("batch_id",)),
        handler=get_offboarding_status,
    ),
    AgentTool(
        name="list_pending_approvals",
        title="Actions waiting for approval",
        description="Every action waiting for an admin's approval, grouped by batch (offboarding, onboarding).",
        input_schema=schema(),
        handler=list_pending_approvals,
    ),
)
