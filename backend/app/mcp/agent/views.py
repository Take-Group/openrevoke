"""Compact shapes of API records for an assistant: names instead of ids where a person reads them."""

from typing import Any

# How offboarding removes an account in an app, from the app's ``delete_mode``.
REMOVAL = {
    "automatic": "automatic: Open Revoke removes it through the app's API, SCIM or the signed-in browser",
    "writes_disabled": "manual task: the app is connected, but writes are off for this connection",
    "manual": "manual task: no connector can remove accounts in this app, an admin removes it by hand",
}


def money(value: dict[str, Any] | None) -> str | None:
    return f"{value['amount']} {value['currency']}" if value else None


def name(person: dict[str, Any]) -> str:
    return f"{person['first_name']} {person['last_name']}".strip()


def person_line(person: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": person["id"],
        "name": name(person),
        "email": person["primary_email"],
        "status": person["status"],
        "left_at": person.get("left_at"),
        "job_title": person.get("job_title"),
        "department": person.get("department"),
        "apps": [app["name"] for app in person.get("apps", [])],
        "monthly_cost": money(person.get("monthly_cost_total")),
    }


def account_line(account: dict[str, Any], app: dict[str, Any] | None) -> dict[str, Any]:
    line = {
        "app": account["app"]["name"],
        "role": account.get("role"),
        "status": account["status"],
        "kind": account["kind"],
        "monthly_cost": money(account.get("monthly_cost_converted") or account.get("monthly_cost")),
    }
    if app is not None:
        line["removal"] = removal(app)
    return line


def removal(app: dict[str, Any]) -> str:
    text = REMOVAL.get(app["delete_mode"], app["delete_mode"])
    if app["delete_mode"] == "automatic" and app.get("delete_suspends"):
        text += " (suspends the user, never deletes)"
    return text


def action_line(action: dict[str, Any]) -> dict[str, Any]:
    line = {
        "id": action["id"],
        "app": action["app"]["name"],
        "kind": action["kind"],
        "status": action["status"],
    }
    if action.get("person"):
        line["person"] = name(action["person"])
    if action.get("account"):
        line["account"] = action["account"].get("email") or action["account"].get("external_id")
    if action.get("error"):
        line["error"] = action["error"]
    return line
