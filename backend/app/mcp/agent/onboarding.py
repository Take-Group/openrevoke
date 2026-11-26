"""Task tools of onboarding: accounts for a new person, by app or through an access profile (a role)."""

from typing import TYPE_CHECKING, Any

from app.mcp.agent.api import match_app
from app.mcp.agent.base import PERSON_ARG, AgentTool, ToolError, schema
from app.mcp.agent.views import action_line, money, name

if TYPE_CHECKING:
    from app.mcp.agent.api import AgentApi

APPROVE_NEXT = (
    "The creations wait for approval: show them to the user and call approve_actions with this batch_id "
    "after a clear yes."
)


async def onboard_person(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    apps = await api.apps()
    chosen = []
    for item in args["apps"]:
        app = match_app(apps, item["app"] if isinstance(item, dict) else item)
        chosen.append({"app_id": app["id"], "role": item.get("role") if isinstance(item, dict) else None})
    result = await api.post(f"/people/{person['id']}/onboard", {"apps": chosen})
    return {
        "batch_id": result["batch_id"],
        "person": name(result["person"]),
        "actions": [action_line(action) for action in result["actions"]],
        "skipped": [{"app": item["app"]["name"], "reason": item["reason"]} for item in result["skipped"]],
        "next": APPROVE_NEXT,
    }


async def list_access_profiles(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    page = await api.get("/access-profiles")
    return {
        "profiles": [
            {
                "id": profile["id"],
                "name": profile["name"],
                "description": profile.get("description"),
                "apps": [{"app": item["app"]["name"], "role": item.get("role")} for item in profile["apps"]],
                "members": profile["member_count"],
                "members_missing_access": profile["members_missing_access"],
                "cost_per_person": money(profile.get("cost_per_person_total")),
            }
            for profile in page["items"]
        ]
    }


async def assign_access_profile(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    profiles = (await api.get("/access-profiles"))["items"]
    wanted = args["profile"].strip().lower()
    profile = next((p for p in profiles if wanted in (p["id"], p["name"].lower())), None)
    if profile is None:
        raise ToolError(f"No access profile {args['profile']!r}: {', '.join(p['name'] for p in profiles) or 'none'}.")
    dry_run = args.get("dry_run", True)
    body = {"profile_ids": [profile["id"]], "dry_run": dry_run, "create_actions": True}
    result = await api.post(f"/people/{person['id']}/access-profiles", body)
    return {
        "person": name(result["person"]),
        "profile": profile["name"],
        "dry_run": dry_run,
        "will_create": [{"app": item["app"]["name"], "role": item.get("role")} for item in result["planned"]],
        "skipped": [{"app": item["app"]["name"], "reason": item["reason"]} for item in result["skipped"]],
        "warnings": result["warnings"],
        "monthly_cost": money(result.get("monthly_cost_total")),
        "batch_id": result.get("batch_id"),
        "next": "Nothing changed. Call again with dry_run false to assign it." if dry_run else APPROVE_NEXT,
    }


async def get_access_drift(api: AgentApi, args: dict[str, Any]) -> dict[str, Any]:
    person = await api.person(args["person"])
    drift = await api.get(f"/people/{person['id']}/access-drift")
    return {
        "person": name(drift["person"]),
        "profiles": [profile["name"] for profile in drift["profiles"]],
        "missing": [{"app": item["app"]["name"], "role": item.get("role")} for item in drift["missing"]],
        "extra": [{"app": item["app"]["name"], "role": item.get("role")} for item in drift["extra"]],
        "role_mismatch": drift["role_mismatch"],
    }


TOOLS = (
    AgentTool(
        name="onboard_person",
        title="Onboard a person",
        description=(
            "Creates accounts for a person in the chosen apps: one creation per app in one batch, waiting for "
            "approval. Apps without a connector that can create accounts get a manual task. Ask the user first."
        ),
        input_schema=schema(
            {
                "person": PERSON_ARG,
                "apps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {"app": {"type": "string"}, "role": {"type": "string"}},
                        "required": ["app"],
                    },
                    "description": 'Apps by name, each with an optional role: [{"app": "Notion", "role": "member"}]',
                },
            },
            required=("person", "apps"),
        ),
        handler=onboard_person,
        read_only=False,
        destructive=True,
    ),
    AgentTool(
        name="list_access_profiles",
        title="Access profiles (roles)",
        description=(
            'Named sets of apps with roles a role gets ("Developer": GitHub, Slack, Linear), with members, '
            "how many miss some access, and the monthly cost per person."
        ),
        input_schema=schema(),
        handler=list_access_profiles,
    ),
    AgentTool(
        name="assign_access_profile",
        title="Give a person an access profile",
        description=(
            "Assigns a profile and creates the missing accounts as one onboarding batch. dry_run (default) only "
            "shows what would be created and what it costs."
        ),
        input_schema=schema(
            {
                "person": PERSON_ARG,
                "profile": {"type": "string", "description": "Profile name or id"},
                "dry_run": {"type": "boolean", "default": True},
            },
            required=("person", "profile"),
        ),
        handler=assign_access_profile,
        read_only=False,
    ),
    AgentTool(
        name="get_access_drift",
        title="Access a person misses or should not have",
        description=(
            "Compares a person's accounts with their access profiles: apps missing, accounts beyond the "
            "profiles, roles that differ."
        ),
        input_schema=schema({"person": PERSON_ARG}, required=("person",)),
        handler=get_access_drift,
    ),
)
