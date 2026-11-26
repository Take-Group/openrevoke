"""Task tools of actions (writes in other apps and manual tasks): approve, cancel, follow, finish, retry."""

from collections import Counter
from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import AgentTool, schema
from app.mcp.agent.errors import ToolError
from app.mcp.agent.views import action_line

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

FINISHED = {"done", "failed", "cancelled"}
TARGET_ARGS = {
    "batch_id": {
        "type": "string",
        "description": "batch_id from start_offboarding, onboard_person or assign_access_profile",
    },
    "action_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Single actions, when there is no batch",
    },
}


async def _targets(api: AgentApi, args: dict[str, Any]) -> list[dict[str, Any]]:
    if args.get("batch_id"):
        page = await api.get("/actions", batch_id=args["batch_id"], limit=PAGE_LIMIT)
        return page["items"]
    if args.get("action_ids"):  # the API has no read of one action: the newest page holds open ones
        wanted = set(args["action_ids"])
        page = await api.get("/actions", limit=PAGE_LIMIT)
        return [action for action in page["items"] if action["id"] in wanted]
    raise ToolError("Pass batch_id or action_ids.")


async def approve_actions(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    if args.get("batch_id"):
        result = await api.post(f"/actions/batch/{args['batch_id']}/approve")
        approved = result["items"]
        refused = [{**action_line(item["action"]), "reason": item["reason"]} for item in result["not_approved"]]
    elif args.get("action_ids"):
        approved, refused = [], []
        for action_id in args["action_ids"]:
            try:
                approved.append(await api.post(f"/actions/{action_id}/approve"))
            except ToolError as error:
                refused.append({"id": action_id, "reason": str(error)})
    else:
        raise ToolError("Pass batch_id or action_ids.")
    return {
        "approved": [action_line(action) for action in approved],
        "not_approved": refused,
        "next": "Writes run in the background and are verified by reading the app's accounts again; manual tasks "
        "go to the admins. Follow with get_actions_status.",
    }


async def cancel_actions(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    cancelled, kept = [], []
    for action in await _targets(api, args):
        if action["status"] in {"done", "cancelled"}:  # a failed action can still be cancelled
            continue
        try:
            cancelled.append(await api.post(f"/actions/{action['id']}/cancel"))
        except ToolError as error:
            kept.append({**action_line(action), "reason": str(error)})
    return {"cancelled": [action_line(action) for action in cancelled], "not_cancelled": kept}


async def get_actions_status(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    actions = [action_line(action) for action in await _targets(api, args)]
    counts = Counter(action["status"] for action in actions)
    manual_open = any(a["kind"] == "manual_task" and a["status"] not in FINISHED for a in actions)
    return {
        "finished": all(action["status"] in FINISHED for action in actions),
        "counts": dict(counts),
        "actions": actions,
        "next": "Manual tasks stay open until an admin does them by hand; then complete_manual_task."
        if manual_open
        else None,
    }


async def list_pending_approvals(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/actions", status="pending_approval", limit=PAGE_LIMIT)
    return {"total": page["total"], "batches": _batches(page["items"])}


async def list_open_manual_tasks(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/actions", status="approved", limit=PAGE_LIMIT)
    tasks = [action_line(action) for action in page["items"] if action["kind"] == "manual_task"]
    return {"total": len(tasks), "tasks": tasks}


async def list_failed_actions(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/actions", status="failed", limit=PAGE_LIMIT)
    return {
        "total": page["total"],
        "actions": [action_line(action) for action in page["items"]],
        "next": "retry_action reads the app first and runs the write again; cancel_actions gives up.",
    }


async def complete_manual_task(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    action = await api.post(f"/actions/{args['action_id']}/complete")
    return {"action": action_line(action)}


async def retry_action(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    action = await api.post(f"/actions/{args['action_id']}/retry")
    return {"action": action_line(action), "next": "Follow it with get_actions_status."}


def _batches(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    batches: dict[str, dict[str, Any]] = {}
    for action in actions:
        key = action.get("batch_id") or action["id"]
        batch = batches.setdefault(key, {"batch_id": action.get("batch_id"), "reason": action["reason"], "actions": []})
        batch["actions"].append(action_line(action))
    return list(batches.values())


ACTION_ID = {"action_id": {"type": "string"}}

TOOLS = (
    AgentTool(
        name="list_pending_approvals",
        title="Actions waiting for approval",
        description=(
            "Every action waiting for an admin's approval, grouped by batch: offboarding removals, onboarding "
            "creations, approved access requests."
        ),
        input_schema=schema(),
        handler=list_pending_approvals,
    ),
    AgentTool(
        name="approve_actions",
        title="Approve actions",
        description=(
            "Runs the writes of one batch (or of single actions): accounts are really created, removed or "
            "suspended in other apps; manual tasks go to the admins. Only after the user said yes to the list."
        ),
        input_schema=schema(TARGET_ARGS),
        handler=approve_actions,
        read_only=False,
        destructive=True,
    ),
    AgentTool(
        name="cancel_actions",
        title="Cancel actions",
        description=(
            "Cancels the actions of a batch (or single actions) that have not finished. Nothing runs in the apps."
        ),
        input_schema=schema(TARGET_ARGS),
        handler=cancel_actions,
        read_only=False,
    ),
    AgentTool(
        name="get_actions_status",
        title="Progress of actions",
        description=(
            "Status of every action of a batch (pending_approval, approved, running, verifying, done, failed, "
            "cancelled) and whether all finished. A failed action has its error."
        ),
        input_schema=schema(TARGET_ARGS),
        handler=get_actions_status,
    ),
    AgentTool(
        name="list_open_manual_tasks",
        title="Manual tasks to do",
        description=(
            "Approved manual tasks: accounts an admin must create or remove by hand, in apps without a "
            "connector or with writes off."
        ),
        input_schema=schema(),
        handler=list_open_manual_tasks,
    ),
    AgentTool(
        name="complete_manual_task",
        title="Mark a manual task done",
        description=(
            "Closes a manual task after the admin did it in the app. Only when the user says it is done: "
            "the account is then recorded as removed (or created)."
        ),
        input_schema=schema(ACTION_ID, required=("action_id",)),
        handler=complete_manual_task,
        read_only=False,
    ),
    AgentTool(
        name="list_failed_actions",
        title="Failed actions",
        description="Writes that failed (the app refused, the read-back did not confirm it), with their error.",
        input_schema=schema(),
        handler=list_failed_actions,
    ),
    AgentTool(
        name="retry_action",
        title="Retry a failed action",
        description="Reads the app's accounts first (the write may have worked), then runs a failed write again.",
        input_schema=schema(ACTION_ID, required=("action_id",)),
        handler=retry_action,
        read_only=False,
        destructive=True,
    ),
)
