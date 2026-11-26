"""Task tools about connections: which connectors exist, connecting an app, checking and syncing it."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.base import APP_ARG, AgentTool, ToolError, schema

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


async def list_connectors(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/connectors")
    return {
        "connectors": [
            {
                "key": item["key"],
                "name": item["display_name"],
                "method": item["integration"],
                "can": item["capabilities"],
                "settings": item["config_schema"].get("properties", {}),
                "required_settings": item["config_schema"].get("required", []),
                "secret_fields": item["secret_fields"],
                "login_url": item.get("login_url"),
                "suspends_instead_of_delete": item.get("delete_suspends", False),
            }
            for item in page["items"]
        ],
        "note": "browser connectors need an admin to sign in once in the panel (Browser); "
        "Google Workspace connects with 'Connect with Google' in the panel.",
    }


async def connect_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    connectors = {item["key"]: item for item in (await api.get("/connectors"))["items"]}
    connector = connectors.get(args["connector"])
    if connector is None:
        raise ToolError(f"No connector {args['connector']!r}. Keys: {', '.join(connectors)}.")
    if app["integration"] != connector["integration"]:  # the API connects only an app of the same method
        await api.patch(f"/apps/{app['id']}", {"integration": connector["integration"]})
    current = app.get("connection") if (app.get("connection") or {}).get("connector_key") == args["connector"] else None
    current = current or {}  # a call that leaves a field out keeps what the connection has
    body = {
        "connector_key": args["connector"],
        "config": {**current.get("config", {}), **(args.get("settings") or {})},
        "secrets": args.get("secrets"),
        "is_people_source": args.get("is_people_source", current.get("is_people_source", False)),
        "writes_enabled": args.get("writes_enabled", current.get("writes_enabled", False)),
    }
    connection = await api.put(f"/apps/{app['id']}/connection", body)
    check = await api.post(f"/apps/{app['id']}/connection/check")
    return {
        "app": app["name"],
        "connector": connection.get("connector_key"),
        "writes_enabled": connection.get("writes_enabled"),
        "check": {"ok": check["ok"], "status": check["status"], "message": check.get("message")},
        "next": _connect_next(check["ok"], connection.get("writes_enabled", False)),
    }


def _connect_next(ok: bool, writes_enabled: bool) -> str:
    if not ok:
        return "Fix the settings or sign in, then check_connection."
    if writes_enabled:
        return "Writes are on: offboarding and onboarding change accounts in the app after approve_actions."
    return "sync_app reads the accounts. Keep writes off until a sync shows the list you expect."


async def check_connection(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    if not app.get("connector_key"):
        raise ToolError(f"{app['name']} has no connection. list_connectors, then connect_app.")
    check = await api.post(f"/apps/{app['id']}/connection/check")
    return {"app": app["name"], **check}


async def sync_app(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    if not app.get("connector_key"):
        raise ToolError(f"{app['name']} has no connection: its accounts are kept by hand.")
    run = await api.post(f"/apps/{app['id']}/connection/sync", force=True if args.get("force") else None)
    return {
        "app": app["name"],
        "sync_run_id": run["id"],
        "status": run["status"],
        "next": "The sync runs in the background; get_sync_history shows the result.",
    }


async def get_sync_history(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    page = await api.get(f"/apps/{app['id']}/sync-runs", limit=args.get("limit", 5))
    runs = [
        {
            key: run.get(key)
            for key in (
                "started_at",
                "finished_at",
                "status",
                "accounts_seen",
                "accounts_added",
                "accounts_removed",
                "error",
            )
        }
        for run in page["items"]
    ]
    return {"app": app["name"], "connection_status": app.get("connection_status"), "runs": runs}


TOOLS = (
    AgentTool(
        name="list_connectors",
        title="Available connectors",
        description=(
            "Every connector with its method (API, SCIM, browser), what it can do (read, create, delete), its "
            "settings and which fields are secrets. Read before connect_app."
        ),
        input_schema=schema(),
        handler=list_connectors,
    ),
    AgentTool(
        name="connect_app",
        title="Connect an app",
        description=(
            "Saves an app's connection (connector, settings, secrets such as an API or SCIM token) and checks it. "
            "Secrets are encrypted and never returned. Writes stay off unless writes_enabled: then offboarding "
            "removes accounts in the app automatically."
        ),
        input_schema=schema(
            {
                "app": APP_ARG,
                "connector": {"type": "string", "description": "Connector key from list_connectors"},
                "settings": {
                    "type": "object",
                    "description": "Connector settings without secret fields; omit to keep the stored ones",
                },
                "secrets": {"type": "object", "description": "Secret fields; omit to keep the stored ones"},
                "writes_enabled": {
                    "type": "boolean",
                    "default": False,
                    "description": "Only after a successful sync: connect, sync_app, then connect_app again with true",
                },
                "is_people_source": {
                    "type": "boolean",
                    "default": False,
                    "description": "Its users are the company's people (Google Workspace)",
                },
            },
            required=("app", "connector"),
        ),
        handler=connect_app,
        read_only=False,
    ),
    AgentTool(
        name="check_connection",
        title="Check a connection",
        description="Tests an app's connection: credentials, a signed-in browser session. Changes nothing.",
        input_schema=schema({"app": APP_ARG}, required=("app",)),
        handler=check_connection,
    ),
    AgentTool(
        name="sync_app",
        title="Sync an app's accounts now",
        description=(
            "Reads the app's account list again in the background (it also runs on a schedule). A sync that "
            "would remove more than 30% of the accounts stops; force runs it anyway when the removals are real."
        ),
        input_schema=schema({"app": APP_ARG, "force": {"type": "boolean", "default": False}}, required=("app",)),
        handler=sync_app,
        read_only=False,
    ),
    AgentTool(
        name="get_sync_history",
        title="Recent syncs of an app",
        description="The last syncs of an app: status, accounts seen, added and removed, the error of a failed one.",
        input_schema=schema(
            {"app": APP_ARG, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, required=("app",)
        ),
        handler=get_sync_history,
    ),
)
