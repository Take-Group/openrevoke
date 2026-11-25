"""HTTP helpers shared by API connectors: the client and error mapping."""

from typing import TYPE_CHECKING, Any

import httpx
import structlog

from app.connectors.base import ConnectorError, IncompleteListError, NeedsLogin

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = structlog.get_logger()

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
USER_AGENT = "OpenRevoke/0.1 (+https://github.com/Take-Group/openrevoke)"
# Upper bound on pages per list. A list longer than this is an error, not a silent cut.
MAX_PAGES = 1000


async def _log_response(response: httpx.Response) -> None:
    request = response.request
    # Path only: query strings may carry filters with e-mails, headers carry tokens.
    logger.info(
        "connector_http",
        method=request.method,
        host=request.url.host,
        path=request.url.path,
        status=response.status_code,
    )


def build_http_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    """Client for connectors: timeout, user agent, no redirects, one log line per response."""
    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=False,
        event_hooks={"response": [_log_response]},
        transport=transport,
    )


def raise_for_app_error(response: httpx.Response, app_name: str, auth_statuses: Iterable[int] = (401,)) -> None:
    """Map an error response: rejected credentials raise ``NeedsLogin``, others ``ConnectorError``."""
    if response.is_success:
        return
    detail = _short_body(response)
    if response.status_code in set(auth_statuses):
        raise NeedsLogin(
            f"{app_name} rejected the credentials (HTTP {response.status_code}). "
            f"Update them in the connection settings.{detail}"
        )
    raise ConnectorError(f"{app_name} returned HTTP {response.status_code} for {response.request.url.path}.{detail}")


def json_body(response: httpx.Response, app_name: str) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise ConnectorError(f"{app_name} returned a response that is not JSON") from exc


def check_page_limit(pages: int, app_name: str) -> None:
    if pages > MAX_PAGES:
        raise IncompleteListError(f"{app_name} returned more than {MAX_PAGES} pages; the list was not read in full")


def _short_body(response: httpx.Response) -> str:
    text = response.text.strip().replace("\n", " ")
    if not text:
        return ""
    return f" Response: {text[:300]}"
