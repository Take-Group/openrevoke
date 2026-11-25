"""Users the fake panel invited or removed, kept in Redis. Read by the panel (``app/api/dev_panel.py``).

The connector never touches this module: it invites and removes through the
panel's own API in the browser, like a real browser connector.
"""

import json
import secrets
from typing import Any

from app.redis import redis_client

INVITED_KEY = "open-revoke:fake-panel:invited"
REMOVED_KEY = "open-revoke:fake-panel:removed"


async def current_users(generated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    invited = [json.loads(value) for value in await redis_client.hvals(INVITED_KEY)]
    removed = set(await redis_client.smembers(REMOVED_KEY))
    users = [*generated, *sorted(invited, key=lambda user: user["id"])]
    return [user for user in users if user["id"] not in removed]


async def invite(email: str, role: str | None) -> dict[str, Any]:
    user = {
        "id": f"panel-new-{secrets.token_hex(4)}",
        "email": email,
        "name": email.split("@")[0],
        "role": role or "member",
        "state": "invited",
    }
    await redis_client.hset(INVITED_KEY, user["id"], json.dumps(user))
    return user


async def remove(user_id: str) -> None:
    await redis_client.hdel(INVITED_KEY, user_id)
    await redis_client.sadd(REMOVED_KEY, user_id)


UI_KEY = "open-revoke:fake-panel:ui-version"
UI_VERSIONS = (1, 2)


async def ui_version() -> int:
    """Look of the admin page: 2 renames the buttons, to break a click recipe on purpose."""
    value = await redis_client.get(UI_KEY)
    return int(value) if value in {str(version) for version in UI_VERSIONS} else 1


async def set_ui_version(version: int) -> None:
    await redis_client.set(UI_KEY, str(version))
