"""Task tools of access requests (from Slack, the panel or an assistant) and of the audit log."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.base import APP_ARG, PERSON_ARG, AgentTool, schema
from app.mcp.agent.views import name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

OPEN = ("pending_manager", "pending_admin")


def request_line(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": item["id"],
        "person": name(item["person"]),
        "app": item["app"]["name"],
        "role": item.get("role"),
        "status": item["status"],
        "waiting_for": item.get("waiting_for"),
        "approver": name(item["approver"]) if item.get("approver") else None,
        "justification": item.get("justification"),
        "channel": item.get("channel"),
        "created_at": item["created_at"],
    }


async def list_access_requests(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    status = args.get("status")
    page = await api.get("/access-requests", status=None if status == "open" else status, limit=200)
    items = [i for i in page["items"] if status != "open" or i["status"] in OPEN] if status else page["items"]
    return {"total": len(items), "requests": [request_line(item) for item in items]}


async def decide_access_request(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    verb = "approve" if args["decision"] == "approve" else "reject"
    result = await api.post(f"/access-requests/{args['request_id']}/{verb}", {"comment": args.get("comment")})
    return {
        "request": request_line(result),
        "next": "An approved request becomes an account creation; follow it with list_pending_approvals."
        if verb == "approve"
        else None,
    }


async def get_audit_log(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"q": args.get("query"), "limit": args.get("limit", 50)}
    if args.get("person"):
        params["person_id"] = (await api.person(args["person"]))["id"]
    if args.get("app"):
        params["app_id"] = (await api.app(args["app"]))["id"]
    page = await api.get("/audit", **params)
    return {
        "total": page["total"],
        "events": [
            {key: event.get(key) for key in ("at", "actor", "event", "entity_type", "data")} for event in page["items"]
        ],
    }


TOOLS = (
    AgentTool(
        name="list_access_requests",
        title="Access requests",
        description=(
            'Requests for an account in an app ("I need Figma"), from Slack, the panel or an assistant: who, '
            "which app, the justification and whose decision they wait for."
        ),
        input_schema=schema(
            {
                "status": {
                    "type": "string",
                    "enum": ["open", "pending_manager", "pending_admin", "approved", "done", "rejected", "failed"],
                    "description": "open: waiting for a manager or an admin",
                }
            }
        ),
        handler=list_access_requests,
    ),
    AgentTool(
        name="decide_access_request",
        title="Approve or reject an access request",
        description=(
            "The admin's decision on a request (also overriding a manager who has not decided). Approval "
            "creates the account creation action. Only on the user's word."
        ),
        input_schema=schema(
            {
                "request_id": {"type": "string"},
                "decision": {"type": "string", "enum": ["approve", "reject"]},
                "comment": {"type": "string", "description": "Shown to the requester; say why on a rejection"},
            },
            required=("request_id", "decision"),
        ),
        handler=decide_access_request,
        read_only=False,
    ),
    AgentTool(
        name="get_audit_log",
        title="Who changed what",
        description=(
            "The append-only audit log, newest first: every change in Open Revoke with its actor (a panel user, "
            "an API token, the system), filtered by person, app or text."
        ),
        input_schema=schema(
            {
                "person": PERSON_ARG,
                "app": APP_ARG,
                "query": {"type": "string", "description": "Text in the event name or data"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50},
            }
        ),
        handler=get_audit_log,
    ),
)
