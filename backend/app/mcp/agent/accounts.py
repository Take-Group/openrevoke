"""Task tools about accounts: seats nobody owns, assigning them, accounts kept by hand."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import APP_ARG, PERSON_ARG, AgentTool, schema
from app.mcp.agent.errors import ToolError
from app.mcp.agent.views import name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


async def list_unassigned_accounts(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    apps = [await api.app(args["app"])] if args.get("app") else [a for a in await api.apps() if a["unassigned_count"]]
    result = []
    for app in apps:
        page = await api.get(f"/apps/{app['id']}/accounts", unassigned=True, limit=PAGE_LIMIT)
        result += [
            {
                "account_id": account["id"],
                "app": app["name"],
                "email": account.get("email"),
                "username": account.get("username"),
                "display_name": account.get("display_name"),
                "role": account.get("role"),
                "status": account["status"],
                "kind": account["kind"],
            }
            for account in page["items"]
            if account["status"] != "removed"
        ]
    return {
        "total": len(result),
        "accounts": result,
        "next": "assign_account gives an account its owner, or marks it as a service account." if result else None,
    }


async def assign_account(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if args.get("person"):
        body["person_id"] = (await api.person(args["person"]))["id"]
    if "is_service_account" in args:
        body["kind"] = "service" if args["is_service_account"] else "person"
    if args.get("role"):
        body["role"] = args["role"]
    if not body:
        raise ToolError("Pass person, is_service_account or role.")
    account = await api.patch(f"/accounts/{args['account_id']}", body)
    return {
        "account_id": account["id"],
        "email": account.get("email") or account.get("username"),
        "person": name(account["person"]) if account.get("person") else None,
        "kind": account["kind"],
        "role": account.get("role"),
        "note": "An owner set by hand stays across syncs.",
    }


async def add_account(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    app = await api.app(args["app"])
    body: dict[str, Any] = {"status": "active"}
    for key in ("email", "username", "role"):
        if args.get(key):
            body[key] = args[key]
    if args.get("person"):
        body["person_id"] = (await api.person(args["person"]))["id"]
    if "email" not in body and "username" not in body and "person_id" not in body:
        raise ToolError("Pass the account's email, username or person.")
    account = await api.post(f"/apps/{app['id']}/accounts", body)
    return {
        "app": app["name"],
        "account_id": account["id"],
        "person": name(account["person"]) if account.get("person") else None,
        "note": "Recorded in Open Revoke only: nothing is created in the app itself (onboard_person does that).",
    }


TOOLS = (
    AgentTool(
        name="list_unassigned_accounts",
        title="Accounts without an owner",
        description=(
            "Accounts no person is matched to (an e-mail that is not anyone's work or alias e-mail): "
            "ex-employees, contractors, shared logins. They cost money and offboarding cannot find them."
        ),
        input_schema=schema({"app": {**APP_ARG, "description": "Only this app (default: every app)"}}),
        handler=list_unassigned_accounts,
    ),
    AgentTool(
        name="assign_account",
        title="Give an account its owner",
        description=(
            "Sets who an account belongs to, marks it as a service account (skipped by offboarding) or "
            "changes its role. account_id comes from list_unassigned_accounts or get_app_access."
        ),
        input_schema=schema(
            {
                "account_id": {"type": "string"},
                "person": PERSON_ARG,
                "is_service_account": {"type": "boolean"},
                "role": {"type": "string"},
            },
            required=("account_id",),
        ),
        handler=assign_account,
        read_only=False,
    ),
    AgentTool(
        name="add_account",
        title="Record an account by hand",
        description=(
            "Records an existing account in an app without a connector (kept by hand), so it shows in the "
            "inventory, costs and offboarding. Does not create anything in the app."
        ),
        input_schema=schema(
            {
                "app": APP_ARG,
                "email": {"type": "string"},
                "username": {"type": "string"},
                "role": {"type": "string"},
                "person": {**PERSON_ARG, "description": "Owner (default: matched by e-mail)"},
            },
            required=("app",),
        ),
        handler=add_account,
        read_only=False,
    ),
)
