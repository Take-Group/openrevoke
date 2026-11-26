"""Task tools of app discovery: apps people sign in to with the company Google account (shadow IT)."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import AgentTool, schema

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

DISCOVERED_ARG = {
    "type": "string",
    "description": "Name of the discovered app (as list_discovered_apps shows it) or id",
}


async def list_discovered_apps(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get(
        "/discovery/apps",
        at_risk=True if args.get("at_risk_only") else None,
        status=args.get("status"),
        limit=PAGE_LIMIT,
    )
    return {
        "total": page["total"],
        "apps": [
            {
                "name": item["name"],
                "status": item["status"],
                "tracked_as": item["app"]["name"] if item.get("app") else None,
                "users": item["users"],
                "users_at_risk": item["users_at_risk"],  # left, suspended or deleted in the directory
                "last_seen_at": item.get("last_seen_at"),
            }
            for item in page["items"]
        ],
    }


async def get_discovered_app_users(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    item = await api.discovered_app(args["app"])
    return {
        "name": item["name"],
        "status": item["status"],
        "scopes": item["scopes"],
        "users": [
            {
                "email": grant["email"],
                "person": grant["person"]["name"] if grant.get("person") else None,
                "person_status": grant["person"]["status"] if grant.get("person") else None,
                "risk": grant.get("risk"),
                "token_active": grant.get("token_active"),
                "last_seen_at": grant.get("last_seen_at"),
            }
            for grant in item["grants"]
        ],
        "next": "track_discovered_app adds it as an app with these users as accounts; ignore_discovered_app hides it.",
    }


async def track_discovered_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    item = await api.discovered_app(args["app"])
    result = await api.post(f"/discovery/apps/{item['id']}/track", {"create_accounts": True})
    return {
        "name": result["name"],
        "tracked_as": result["app"]["name"] if result.get("app") else None,
        "accounts_created": result.get("accounts_created"),
        "next": "update_app sets its price; offboarding now includes these accounts.",
    }


async def ignore_discovered_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    item = await api.discovered_app(args["app"])
    result = await api.patch(f"/discovery/apps/{item['id']}", {"status": "ignored"})
    return {"name": result["name"], "status": result["status"]}


async def run_discovery_scan(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    run = await api.post("/discovery/scan")
    return {
        "scan_id": run.get("id"),
        "status": run.get("status"),
        "next": "The scan runs in the background; list_discovered_apps shows the result.",
    }


TOOLS = (
    AgentTool(
        name="list_discovered_apps",
        title="Apps found in Google sign-ins",
        description=(
            "Third-party apps people signed in to with the company Google account (shadow IT), with the number "
            "of users and of users at risk (left, or suspended or deleted in Google). Needs the discovery scan."
        ),
        input_schema=schema(
            {
                "at_risk_only": {
                    "type": "boolean",
                    "description": "Only apps with users at risk (left, suspended, deleted)",
                },
                "status": {"type": "string", "enum": ["new", "tracked", "ignored"]},
            }
        ),
        handler=list_discovered_apps,
    ),
    AgentTool(
        name="get_discovered_app_users",
        title="Who signs in to a discovered app",
        description=(
            "Every user of one discovered app: e-mail, the matched person, risk (left, suspended, deleted), "
            "whether the Google token is still active, and the permissions (scopes) the app holds."
        ),
        input_schema=schema({"app": DISCOVERED_ARG}, required=("app",)),
        handler=get_discovered_app_users,
    ),
    AgentTool(
        name="track_discovered_app",
        title="Track a discovered app",
        description=(
            "Adds a discovered app to the inventory (or links the app already there) and records its users as "
            "accounts, so they show in costs and offboarding."
        ),
        input_schema=schema({"app": DISCOVERED_ARG}, required=("app",)),
        handler=track_discovered_app,
        read_only=False,
    ),
    AgentTool(
        name="ignore_discovered_app",
        title="Ignore a discovered app",
        description="Hides a discovered app the company does not care about (a sign-in helper, a free tool).",
        input_schema=schema({"app": DISCOVERED_ARG}, required=("app",)),
        handler=ignore_discovered_app,
        read_only=False,
    ),
    AgentTool(
        name="run_discovery_scan",
        title="Scan Google sign-ins now",
        description="Starts a new scan of the Google Workspace sign-in logs in the background (it also runs daily).",
        input_schema=schema(),
        handler=run_discovery_scan,
        read_only=False,
    ),
)
