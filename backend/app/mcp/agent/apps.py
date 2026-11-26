"""Task tools about apps: the overview, the spend per app, who has access to one app, shadow IT."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import APP_ARG, AgentTool, schema
from app.mcp.agent.views import money, name, removal

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


async def get_overview(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    dashboard = await api.get("/dashboard")
    return {
        "counts": dashboard["counts"],
        "monthly_cost": money(dashboard.get("monthly_cost_total")),
        "alerts": [
            {"severity": alert["severity"], "kind": alert["kind"], "message": alert["message"]}
            for alert in dashboard["alerts"]
        ],
    }


async def get_spend_by_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    apps = await api.apps()
    rows = [
        {
            "app": app["name"],
            "category": app.get("category"),
            "pricing": app["pricing_model"],
            "active_seats": app["active_seats"],
            "monthly_cost": money(app.get("monthly_cost_converted") or app.get("monthly_cost")),
            "_sort": float((app.get("monthly_cost_converted") or app.get("monthly_cost") or {}).get("amount") or 0),
        }
        for app in apps
    ]
    rows.sort(key=lambda row: row["_sort"], reverse=True)
    for row in rows:
        del row["_sort"]
    dashboard = await api.get("/dashboard")
    return {"monthly_cost_total": money(dashboard.get("monthly_cost_total")), "apps": rows}


async def get_app_access(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    page = await api.get(f"/apps/{app['id']}/accounts", status=args.get("status"), limit=PAGE_LIMIT)
    accounts = [
        {
            "person": name(account["person"]) if account.get("person") else None,
            "person_status": account["person"]["status"] if account.get("person") else None,
            "email": account.get("email") or account.get("username"),
            "role": account.get("role"),
            "status": account["status"],
            "kind": account["kind"],
        }
        for account in page["items"]
        if args.get("status") or account["status"] != "removed"
    ]
    return {
        "app": app["name"],
        "connected": app.get("connector_key") is not None,
        "connection_status": app.get("connection_status"),
        "last_synced_at": app.get("last_synced_at"),
        "removal": removal(app),
        "active_seats": app["active_seats"],
        "monthly_cost": money(app.get("monthly_cost_converted") or app.get("monthly_cost")),
        "unassigned_accounts": app["unassigned_count"],
        "accounts": accounts,
    }


async def list_discovered_apps(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/discovery/apps", at_risk=True if args.get("at_risk_only") else None, limit=PAGE_LIMIT)
    return {
        "total": page["total"],
        "apps": [
            {
                "name": item["name"],
                "status": item["status"],
                "tracked_as": item["app"]["name"] if item.get("app") else None,
                "users": item["users"],
                "users_who_left": item["users_at_risk"],
                "last_seen_at": item.get("last_seen_at"),
            }
            for item in page["items"]
        ],
    }


TOOLS = (
    AgentTool(
        name="get_overview",
        title="Company overview",
        description=(
            "Start here. Counts of people, apps and accounts, the total monthly SaaS cost and the alerts an admin "
            "should act on (people who left with open accounts, failed removals, connections that need a login)."
        ),
        input_schema=schema(),
        handler=get_overview,
    ),
    AgentTool(
        name="get_spend_by_app",
        title="Monthly cost per app",
        description=(
            "Every app with its pricing model, active seats and monthly cost in the company's currency, "
            "most expensive first, plus the total."
        ),
        input_schema=schema(),
        handler=get_spend_by_app,
    ),
    AgentTool(
        name="get_app_access",
        title="Who has access to an app",
        description=(
            "Accounts in one app with the person each belongs to (or none: unassigned), role and status, "
            "how offboarding removes accounts there and the app's monthly cost."
        ),
        input_schema=schema(
            {
                "app": APP_ARG,
                "status": {
                    "type": "string",
                    "enum": ["active", "invited", "suspended", "removed"],
                    "description": "Only accounts with this status (default: all but removed)",
                },
            },
            required=("app",),
        ),
        handler=get_app_access,
    ),
    AgentTool(
        name="list_discovered_apps",
        title="Apps found in Google sign-ins",
        description=(
            "Third-party apps people signed in to with the company Google account (shadow IT), with the number "
            "of users and of users who already left. Needs the Google Workspace discovery scan."
        ),
        input_schema=schema(
            {"at_risk_only": {"type": "boolean", "description": "Only apps still used by people who left"}}
        ),
        handler=list_discovered_apps,
    ),
)
