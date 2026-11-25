"""Slack Web API calls over httpx. Slack answers HTTP 200 with ``ok: false`` on errors."""

import asyncio
from typing import Any

import httpx

API_URL = "https://slack.com/api/{method}"
TIMEOUT_SECONDS = 20.0
RATE_LIMIT_RETRIES = 2
MAX_RETRY_AFTER_SECONDS = 30.0
# Errors that mean the token is wrong, expired or revoked.
AUTH_ERRORS = frozenset({"invalid_auth", "not_authed", "token_revoked", "token_expired", "account_inactive"})


class SlackApiError(Exception):
    def __init__(self, method: str, error: str, detail: str | None = None) -> None:
        self.method = method
        self.error = error
        self.detail = detail
        super().__init__(f"Slack {method} failed: {error}" + (f" ({detail})" if detail else ""))

    @property
    def is_auth(self) -> bool:
        return self.error in AUTH_ERRORS


async def call(
    method: str,
    token: str | None,
    *,
    data: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> dict[str, Any]:
    """POST one Web API method. ``json`` for methods with blocks, ``data`` (form) for the rest."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                response = await client.post(
                    API_URL.format(method=method), headers=headers, data=data, json=json, files=files
                )
            except httpx.HTTPError as exc:
                raise SlackApiError(method, "network_error", str(exc)) from exc
            if response.status_code == 429 and attempt < RATE_LIMIT_RETRIES:
                await asyncio.sleep(_retry_after(response))
                continue
            break
    try:
        body = response.json()
    except ValueError as exc:
        raise SlackApiError(method, f"http_{response.status_code}") from exc
    if not isinstance(body, dict):
        raise SlackApiError(method, "unexpected_response")
    if body.get("ok") is not True:
        raise SlackApiError(method, str(body.get("error") or "unknown_error"), _detail(body))
    return body


def _retry_after(response: httpx.Response) -> float:
    try:
        return min(float(response.headers.get("retry-after", "5")), MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        return 5.0


def _detail(body: dict[str, Any]) -> str | None:
    """Manifest validation errors come as ``errors: [{message, pointer}]``."""
    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        parts = [f"{e.get('pointer', '')}: {e.get('message', '')}".strip(": ") for e in errors if isinstance(e, dict)]
        return "; ".join(parts) or None
    needed = body.get("needed")
    return f"needs scope {needed}" if needed else None
