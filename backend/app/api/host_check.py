"""Refuse requests addressed to a host name the panel does not use (DNS rebinding).

The API listens on 127.0.0.1 only.
A website the admin visits could still reach it through DNS rebinding: its
own name resolves to 127.0.0.1, so the browser sends ``Host: evil.example``
and treats the answer as same-origin. Checking ``Host`` stops that. Requests
proxied by the panel (Next.js rewrites ``/api``) arrive with the API's own
host and the panel's host in ``X-Forwarded-Host``, which Next.js sets from the
original request, so that header is checked as well.
"""

from typing import TYPE_CHECKING

from starlette.responses import JSONResponse

from app.config import settings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from starlette.types import ASGIApp, Receive, Scope, Send


def host_name(value: str) -> str:
    """``Host`` header without the port, lower case. ``[::1]:8000`` gives ``[::1]``."""
    value = value.strip().lower()
    if value.startswith("["):
        return value.split("]", 1)[0] + "]"
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


class AllowedHostsMiddleware:
    def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str]) -> None:
        self.app = app
        self.allowed = {host.strip().lower() for host in allowed_hosts}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket") or "*" in self.allowed:
            await self.app(scope, receive, send)
            return
        headers = {name.decode("latin-1"): value.decode("latin-1") for name, value in scope["headers"]}
        hosts = [headers.get("host", "")]
        if "x-forwarded-host" in headers:
            hosts += headers["x-forwarded-host"].split(",")
        if all(host_name(host) in self.allowed for host in hosts):
            await self.app(scope, receive, send)
            return
        response = JSONResponse({"detail": wrong_address_message(hosts[-1])}, status_code=400)
        await response(scope, receive, send)


def wrong_address_message(host: str) -> str:
    """Shown by the panel when it is opened under an address the API does not answer to."""
    return (
        f"Open Revoke does not answer to the address {host_name(host) or '(none)'}. "
        f"Open it at {settings.public_url}, or set PUBLIC_URL in .env to the address you use and restart."
    )
