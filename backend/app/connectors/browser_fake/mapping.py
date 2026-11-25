"""The fake panel's data and its parsing. Invented people on example.com only.

The panel itself is served by the app (``app/api/dev_panel.py``) so the real
browser can log in to it and the connector can read it with ``fetch()``.
"""

from typing import Any

from app.connectors.base import ConnectorError, RemoteAccount

STATES = {"active": "active", "invited": "invited", "deactivated": "suspended"}
NAMES = ("Ada Testowa", "Borys Przykładowy", "Celina Fikcyjna", "Dawid Wzorcowy")


def panel_users(count: int, domain: str = "example.com") -> list[dict[str, Any]]:
    """``count`` users as the fake panel returns them: the first is an admin, the last deactivated."""
    users = []
    for index in range(count):
        state = "deactivated" if index == count - 1 and count > 2 else "active"
        users.append(
            {
                "id": f"panel-{index + 1}",
                "email": f"panel{index + 1}@{domain}",
                "name": NAMES[index % len(NAMES)],
                "role": "admin" if index == 0 else "member",
                "state": state,
            }
        )
    return users


def panel_page(users: list[dict[str, Any]], page: int, per_page: int) -> dict[str, Any]:
    start = (page - 1) * per_page
    chunk = users[start : start + per_page]
    has_next = start + per_page < len(users)
    return {"users": chunk, "next_page": page + 1 if has_next else None, "total": len(users)}


def parse_page(body: Any) -> tuple[list[dict[str, Any]], int | None]:
    if not isinstance(body, dict) or not isinstance(body.get("users"), list):
        raise ConnectorError("Fake panel returned an unexpected users response")
    next_page = body.get("next_page")
    return body["users"], next_page if isinstance(next_page, int) else None


def user_to_account(user: dict[str, Any]) -> RemoteAccount:
    if not user.get("id"):
        raise ConnectorError("Fake panel returned a user without id")
    state = STATES.get(str(user.get("state")))
    if state is None:
        raise ConnectorError(f"Fake panel returned an unknown user state: {user.get('state')!r}")
    email = user.get("email")
    return RemoteAccount(
        external_id=str(user["id"]),
        email=email.lower() if isinstance(email, str) else None,
        display_name=user.get("name"),
        username=None,
        role=user.get("role"),
        status=state,  # type: ignore[arg-type]
        raw={key: user[key] for key in ("id", "role", "state") if key in user},
    )
