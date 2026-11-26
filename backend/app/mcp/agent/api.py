"""The panel's API for task tools: in-process HTTP requests with the caller's API token."""

import uuid
from typing import TYPE_CHECKING, Any

from app.api.auth_deps import CLIENT_HEADER
from app.mcp.agent.base import ToolError

if TYPE_CHECKING:
    import httpx

PAGE_LIMIT = 500  # the API's maximum ``limit``


class AgentApi:
    def __init__(self, client: httpx.AsyncClient, token: str) -> None:
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}", CLIENT_HEADER: "mcp"}

    async def get(self, path: str, **params: Any) -> Any:
        clean = {name: value for name, value in params.items() if value is not None}
        return await self._request("GET", path, params=clean)

    async def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, json=body)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self.client.request(method, f"/api{path}", headers=self.headers, **kwargs)
        if response.status_code >= 400:
            raise ToolError(f"HTTP {response.status_code}: {_detail(response)}")
        return response.json() if response.content else None

    async def apps(self) -> list[dict[str, Any]]:
        page = await self.get("/apps", limit=PAGE_LIMIT)
        return page["items"]

    async def person(self, reference: str) -> dict[str, Any]:
        """``reference`` is an id, an e-mail or a name; exactly one person must match."""
        reference = reference.strip()
        if _is_uuid(reference):
            return await self.get(f"/people/{reference}")
        page = await self.get("/people", q=reference, limit=20)
        people = page["items"]
        exact = [
            p
            for p in people
            if p["primary_email"].lower() == reference.lower() or _full_name(p).lower() == reference.lower()
        ]
        matches = exact or people
        if not matches:
            raise ToolError(f"No person matches {reference!r}. Call find_people to search.")
        if len(matches) > 1:
            names = "; ".join(f"{_full_name(p)} <{p['primary_email']}> ({p['status']})" for p in matches[:10])
            raise ToolError(f"{len(matches)} people match {reference!r}: {names}. Call again with the e-mail.")
        return await self.get(f"/people/{matches[0]['id']}")

    async def app(self, reference: str) -> dict[str, Any]:
        reference = reference.strip()
        if _is_uuid(reference):
            return await self.get(f"/apps/{reference}")
        apps = await self.apps()
        wanted = reference.lower()
        exact = [a for a in apps if wanted in (a["name"].lower(), a["slug"].lower())]
        matches = exact or [a for a in apps if wanted in a["name"].lower()]
        if not matches:
            raise ToolError(f"No app matches {reference!r}. Call get_spend_by_app for the list of apps.")
        if len(matches) > 1:
            raise ToolError(f"Several apps match {reference!r}: {', '.join(a['name'] for a in matches[:10])}.")
        return await self.get(f"/apps/{matches[0]['id']}")


def _full_name(person: dict[str, Any]) -> str:
    return f"{person['first_name']} {person['last_name']}".strip()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError, AttributeError:
        return response.text[:500] or response.reason_phrase
    if isinstance(detail, list):
        return "; ".join(str(item.get("msg")) for item in detail)
    return str(detail)
