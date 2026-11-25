"""Auth headers the admin panels send, kept in memory per host.

Many panels keep their API token in JavaScript memory and send it as a header
(``authorization``, ``x-csrf-token``...). The listener records the last value
of such headers per host, so a connector can send the same header from the
same tab. Values live only in this process's memory for one hour. They are
never logged, stored or returned by the API.
"""

import re
import time
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Request

TTL_SECONDS = 60 * 60
EXACT_NAMES = frozenset({"authorization", "x-csrf-token", "x-xsrf-token", "x-csrftoken"})
NAME_PREFIXES = ("x-slack-",)
NAME_PATTERN = re.compile(r"csrf|xsrf", re.IGNORECASE)


def is_auth_header(name: str) -> bool:
    lower = name.lower()
    return lower in EXACT_NAMES or lower.startswith(NAME_PREFIXES) or bool(NAME_PATTERN.search(lower))


class HeaderCapture:
    """Last auth headers per host with a TTL. One instance per browser connection."""

    def __init__(self, ttl_seconds: float = TTL_SECONDS, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._headers: dict[str, dict[str, tuple[str, float]]] = {}

    def attach(self, context: BrowserContext) -> None:
        context.on("request", self._on_request)

    def _on_request(self, request: Request) -> None:
        host = urlsplit(request.url).hostname
        if host:
            # ``headers`` has the headers the page set (authorization, csrf);
            # it leaves out cookies, which fetch() sends by itself anyway.
            self.record(host, request.headers)

    def record(self, host: str, headers: Mapping[str, str]) -> None:
        now = self._clock()
        for name, value in headers.items():
            if value and is_auth_header(name):
                self._headers.setdefault(host.lower(), {})[name.lower()] = (value, now)

    def get(self, host: str, name: str) -> str | None:
        entry = self._headers.get(host.lower(), {}).get(name.lower())
        if entry is None:
            return None
        value, seen_at = entry
        if self._clock() - seen_at > self._ttl:
            del self._headers[host.lower()][name.lower()]
            return None
        return value

    def headers_for(self, host: str) -> dict[str, str]:
        names = list(self._headers.get(host.lower(), {}))
        found = {name: self.get(host, name) for name in names}
        return {name: value for name, value in found.items() if value is not None}

    def clear(self) -> None:
        self._headers.clear()
