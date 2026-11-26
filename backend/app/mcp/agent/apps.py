"""Task tools about apps: the overview, the spend per app, who has access to one app, adding and pricing apps."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import APP_ARG, AgentTool, schema
from app.mcp.agent.errors import ToolError
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


async def add_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    default_model = "free" if args.get("price") is None else "per_seat"  # a paid model needs a price
    body: dict[str, Any] = {"pricing_model": args.get("pricing_model", default_model)}
    if args.get("price") is not None:
        body["price"] = _price(args)
    hits = (await api.get("/catalog/search", q=args["name"], limit=5))["items"]
    known = next((hit for hit in hits if hit["name"].lower() == args["name"].strip().lower()), None)
    if known and known.get("already_added"):
        raise ToolError(f"{known['name']} is already in Open Revoke. Use get_app_access or update_app.")
    if known:
        body["catalog_key"] = known["slug"]
    else:
        body["name"] = args["name"].strip()
    for key in ("website", "category", "admin_url"):
        if args.get(key):
            body[key] = args[key]
    app = await api.post("/apps", body)
    return {
        "app": app["name"],
        "id": app["id"],
        "from_catalog": known is not None,
        "connector_available": bool(known and known.get("connector_key")),
        "next": "connect_app syncs its accounts (list_connectors for the settings); without a connector, "
        "add_account keeps them by hand.",
    }


async def update_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    body: dict[str, Any] = {
        key: args[key] for key in ("pricing_model", "admin_url", "category", "notes", "request_policy") if key in args
    }
    if args.get("price") is not None:
        body["price"] = _price(args)
    if not body:
        raise ToolError("Nothing to change: pass at least one field.")
    updated = await api.patch(f"/apps/{app['id']}", body)
    return {
        "app": updated["name"],
        "pricing": updated["pricing_model"],
        "price": updated.get("price"),
        "request_policy": updated["request_policy"],
        "monthly_cost": money(updated.get("monthly_cost_converted") or updated.get("monthly_cost")),
    }


def _price(args: dict[str, Any]) -> dict[str, Any]:
    if not args.get("currency"):
        raise ToolError("A price needs its currency (ISO code, e.g. EUR).")
    return {
        "amount": str(args["price"]),
        "currency": args["currency"].upper(),
        "billing_period": args.get("billing_period", "monthly"),
    }


PRICE_ARGS = {
    "pricing_model": {
        "type": "string",
        "enum": ["per_seat", "flat", "free"],
        "description": "per_seat: price times active seats; flat: one price for the whole company",
    },
    "price": {"type": "string", "description": 'Decimal amount, e.g. "12.50"'},
    "currency": {"type": "string", "description": "ISO code of the price, e.g. EUR or USD"},
    "billing_period": {"type": "string", "enum": ["monthly", "yearly"], "default": "monthly"},
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
        name="add_app",
        title="Add an app",
        description=(
            'Adds a SaaS app the company pays for. A name the catalog knows ("Notion", "Figma") brings its '
            "website, logo and the connector, if there is one. Optional price."
        ),
        input_schema=schema(
            {
                "name": {"type": "string"},
                **PRICE_ARGS,
                "website": {"type": "string"},
                "category": {"type": "string"},
                "admin_url": {"type": "string", "description": "Where the app's admin panel is"},
            },
            required=("name",),
        ),
        handler=add_app,
        read_only=False,
    ),
    AgentTool(
        name="update_app",
        title="Change an app's price or settings",
        description=(
            "Sets the price and pricing model, the admin panel link, category, notes, or who approves "
            "access requests for the app (request_policy)."
        ),
        input_schema=schema(
            {
                "app": APP_ARG,
                **PRICE_ARGS,
                "admin_url": {"type": "string"},
                "category": {"type": "string"},
                "notes": {"type": "string"},
                "request_policy": {
                    "type": "string",
                    "enum": ["off", "automatic", "manager", "manager_then_admin", "admin"],
                    "description": "Access requests: off (not requestable), automatic, or who approves",
                },
            },
            required=("app",),
        ),
        handler=update_app,
        read_only=False,
    ),
)
