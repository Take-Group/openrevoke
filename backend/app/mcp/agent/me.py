"""Task tools of a member (panel role user): my accounts, asking for access, deciding for my team."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import match_app
from app.mcp.agent.base import PERSON_ARG, AgentTool, schema
from app.mcp.agent.errors import ToolError
from app.mcp.agent.requests import request_line
from app.mcp.agent.views import name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


async def get_my_access(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    me = await api.get("/me/access")
    return {
        "me": name(me["person"]) if me.get("person") else None,
        "accounts": [
            {"app": a["app"]["name"], "role": a.get("role"), "status": a["status"], "email": a.get("email")}
            for a in me["accounts"]
        ],
        "my_requests": [
            {"app": r["app"]["name"], "status": r["status"], "waiting_for": r.get("waiting_for")}
            for r in me["requests"]
        ],
        "can_request": [{"app": r["app"]["name"], "roles": r["roles"]} for r in me["requestable_apps"]],
    }


async def request_access(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    me = await api.get("/me/access")
    requestable = [{**item["app"], "id": item["app"]["app_id"]} for item in me["requestable_apps"]]
    if not requestable:
        raise ToolError("No app can be requested here; ask an admin.")
    app = match_app(requestable, args["app"], hint="get_my_access")
    body: dict[str, Any] = {"app_id": app["id"], "justification": args["justification"], "role": args.get("role")}
    if args.get("for_person"):
        team = (await api.get("/me/team"))["reports"]
        wanted = args["for_person"].strip().lower()
        member = next(
            (m["person"] for m in team if wanted in (m["person"]["primary_email"].lower(), name(m["person"]).lower())),
            None,
        )
        if member is None:
            raise ToolError("That person is not one of your reports.")
        body["person_id"] = member["person_id"]
    result = await api.post("/me/access-requests", body)
    return {"app": result["app_name"], "outcome": result["outcome"], "note": result.get("note")}


async def list_my_approvals(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/me/approvals", status="pending_manager" if args.get("pending_only", True) else None)
    return {"pending": page["pending"], "requests": [request_line(item) for item in page["items"]]}


async def decide_my_approval(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    verb = "approve" if args["decision"] == "approve" else "reject"
    result = await api.post(f"/me/approvals/{args['request_id']}/{verb}", {"comment": args.get("comment")})
    return {"request": request_line(result)}


TOOLS = (
    AgentTool(
        name="get_my_access",
        title="My accounts",
        description="Your own accounts in the company's apps, your open requests and the apps you can ask for.",
        input_schema=schema(),
        handler=get_my_access,
        audience="user",
    ),
    AgentTool(
        name="request_access",
        title="Ask for access to an app",
        description=(
            "Asks for an account in an app, for yourself or for one of your reports. The app's policy decides "
            "who approves: your manager, an admin, both or nobody."
        ),
        input_schema=schema(
            {
                "app": {"type": "string", "description": "App name, one of can_request in get_my_access"},
                "justification": {"type": "string", "description": "Why you need it"},
                "role": {"type": "string"},
                "for_person": {**PERSON_ARG, "description": "One of your reports (default: yourself)"},
            },
            required=("app", "justification"),
        ),
        handler=request_access,
        read_only=False,
        audience="user",
    ),
    AgentTool(
        name="list_my_approvals",
        title="Requests waiting for me",
        description="Access requests of your reports that wait for your decision as their manager.",
        input_schema=schema({"pending_only": {"type": "boolean", "default": True}}),
        handler=list_my_approvals,
        audience="user",
    ),
    AgentTool(
        name="decide_my_approval",
        title="Approve or reject a report's request",
        description="Your decision as the manager on one access request. Only on the user's word.",
        input_schema=schema(
            {
                "request_id": {"type": "string"},
                "decision": {"type": "string", "enum": ["approve", "reject"]},
                "comment": {"type": "string"},
            },
            required=("request_id", "decision"),
        ),
        handler=decide_my_approval,
        read_only=False,
        audience="user",
    ),
)
