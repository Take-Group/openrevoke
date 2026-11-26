"""Task tools of offboarding: plan, then start. Nothing is removed before approve_actions (``actions.py``)."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.base import PERSON_ARG, AgentTool, schema
from app.mcp.agent.views import account_line, action_line, name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


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
