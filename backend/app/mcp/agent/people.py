"""Task tools about people: who works here, what each person has, who left with access."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import PAGE_LIMIT
from app.mcp.agent.base import PERSON_ARG, AgentTool, schema
from app.mcp.agent.errors import ToolError
from app.mcp.agent.views import account_line, money, name, person_line

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi


async def find_people(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/people", q=args.get("query"), status=args.get("status"), limit=args.get("limit", 50))
    return {"total": page["total"], "people": [person_line(p) for p in page["items"]]}


async def get_person_access(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    apps = {app["id"]: app for app in await api.apps()}
    accounts = [account_line(a, apps.get(a["app_id"])) for a in person["accounts"] if a["status"] != "removed"]
    return {
        "person": {**person_line(person), "manager": person["manager"] and name(person["manager"])},
        "accounts": accounts,
        "monthly_cost": money(person.get("monthly_cost_total")),
        "next": "plan_offboarding shows what offboarding this person would do."
        if person["status"] == "active"
        else "start_offboarding creates removal actions for the accounts that are still open.",
    }


async def list_leavers_with_access(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/people", status="left", limit=PAGE_LIMIT)
    leavers = [person_line(p) | {"open_accounts": p["accounts_count"]} for p in page["items"] if p["accounts_count"]]
    leavers.sort(key=lambda p: p["open_accounts"], reverse=True)
    return {
        "people_left": page["total"],
        "with_open_accounts": len(leavers),
        "people": leavers,
        "next": "get_person_access lists one person's accounts; start_offboarding removes them." if leavers else None,
    }


async def add_person(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    body = {key: args.get(key) for key in ("first_name", "last_name", "job_title", "department")}
    body["primary_email"] = args["email"]
    if args.get("manager"):
        body["manager_id"] = (await api.person(args["manager"]))["id"]
    person = await api.post("/people", body)
    return {
        "person": person_line(person),
        "next": "onboard_person creates their accounts, or assign_access_profile gives a role's set of apps.",
    }


async def update_person(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    body: dict[str, Any] = {key: args[key] for key in ("job_title", "department", "notes") if key in args}
    if "email" in args:
        body["primary_email"] = args["email"]
    if "is_service_account" in args:
        body["kind"] = "service" if args["is_service_account"] else "human"
    if "aliases" in args:
        body["aliases"] = args["aliases"]
    if "manager" in args:
        body["manager_id"] = (await api.person(args["manager"]))["id"] if args["manager"] else None
    if not body:
        raise ToolError("Nothing to change: pass at least one field.")
    updated = await api.patch(f"/people/{person['id']}", body)
    return {"person": {**person_line(updated), "manager": updated["manager"] and name(updated["manager"])}}


TOOLS = (
    AgentTool(
        name="find_people",
        title="Find people",
        description=(
            "Search the company's people (employees and service accounts) by name, e-mail or job title. "
            "Each result has the apps the person has an account in and their monthly cost."
        ),
        input_schema=schema(
            {
                "query": {"type": "string", "description": "Text to search in name, e-mail and job title"},
                "status": {"type": "string", "enum": ["active", "left"], "description": "Only people with this status"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50},
            }
        ),
        handler=find_people,
    ),
    AgentTool(
        name="get_person_access",
        title="What a person has access to",
        description=(
            "Every open account of one person: app, role, status, monthly cost and how offboarding would remove it "
            "(automatic through the app, or a manual task for an admin). Use it to answer 'what does X have?'."
        ),
        input_schema=schema({"person": PERSON_ARG}, required=("person",)),
        handler=get_person_access,
    ),
    AgentTool(
        name="list_leavers_with_access",
        title="People who left but still have accounts",
        description=(
            "People marked as left who still have open accounts in any app: the access a company forgets to "
            "remove. Sorted by the number of open accounts."
        ),
        input_schema=schema(),
        handler=list_leavers_with_access,
    ),
    AgentTool(
        name="add_person",
        title="Add a person",
        description=(
            "Adds an employee by hand (people usually come from Google Workspace or a CSV import). "
            "Creates no accounts: follow with onboard_person or assign_access_profile."
        ),
        input_schema=schema(
            {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "email": {"type": "string", "description": "Work e-mail; accounts in apps are matched by it"},
                "job_title": {"type": "string"},
                "department": {"type": "string"},
                "manager": {**PERSON_ARG, "description": "The manager: e-mail, name or id"},
            },
            required=("first_name", "last_name", "email"),
        ),
        handler=add_person,
        read_only=False,
    ),
    AgentTool(
        name="update_person",
        title="Change a person's details",
        description=(
            "Changes job title, department, manager, notes, work e-mail, alias e-mails (other addresses "
            "accounts are matched by) or marks the record as a service account. To mark someone as left, "
            "use start_offboarding."
        ),
        input_schema=schema(
            {
                "person": PERSON_ARG,
                "job_title": {"type": "string"},
                "department": {"type": "string"},
                "notes": {"type": "string"},
                "email": {"type": "string", "description": "New work e-mail"},
                "aliases": {"type": "array", "items": {"type": "string"}, "description": "All alias e-mails"},
                "manager": {"type": ["string", "null"], "description": "The manager: e-mail, name or id; null clears"},
                "is_service_account": {"type": "boolean", "description": "A shared or technical identity"},
            },
            required=("person",),
        ),
        handler=update_person,
        read_only=False,
    ),
)
