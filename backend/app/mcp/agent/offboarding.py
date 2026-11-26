"""Task tools of offboarding: plan, then start. Nothing is removed before approve_actions (``actions.py``)."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import PERSON_ARG, AgentTool, schema
from app.mcp.agent.views import account_line, action_line, name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


FINISHED = {"done", "failed", "cancelled"}


def _removes(action: dict[str, Any]) -> bool:
    operation = (action.get("payload") or {}).get("operation")
    return action["kind"] == "delete_account" or (action["kind"] == "manual_task" and operation == "delete_account")


async def plan_offboarding(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    apps = {app["id"]: app for app in await api.apps()}
    open_actions = (await api.get("/actions", person_id=person["id"], limit=PAGE_LIMIT))["items"]
    busy = {
        a["account"]["account_id"]
        for a in open_actions
        if a.get("account") and a["status"] not in FINISHED and _removes(a)
    }
    removals, skipped, in_progress = [], [], []
    for account in person["accounts"]:
        if account["status"] == "removed":
            continue
        line = account_line(account, apps.get(account["app_id"]))
        if account["kind"] == "service":
            skipped.append(line)
        elif account["id"] in busy:
            in_progress.append(line)
        else:
            removals.append(line)
    automatic = sum(1 for line in removals if line.get("removal", "").startswith("automatic"))
    blocked = sum(1 for line in removals if line.get("removal", "").startswith("blocked"))
    return {
        "person": name(person),
        "email": person["primary_email"],
        "status": person["status"],
        "will_remove": removals,
        "skipped_service_accounts": skipped,
        "skipped_removal_already_open": in_progress,
        "summary": f"{automatic} removed automatically, {blocked} blocked until writes are on, "
        f"{len(removals) - automatic - blocked} manual task(s).",
        "next": (
            "Nothing changed yet. start_offboarding marks the person as left and creates these actions; "
            "they still wait for approve_actions."
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
            "approve_actions with this batch_id only after a clear yes."
        ),
    }


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
            "approval in one batch. Nothing is removed in other apps until approve_actions. "
            "Ask the user before calling it."
        ),
        input_schema=schema({"person": PERSON_ARG}, required=("person",)),
        handler=start_offboarding,
        read_only=False,
        destructive=True,
    ),
)
