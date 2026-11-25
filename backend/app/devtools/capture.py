"""Record the fetch/XHR traffic of an admin panel to a JSONL file, for writing a connector.

Run in the app container while you click through the admin panel in the live
view (page Browser of the Open Revoke panel):

    docker compose exec app python -m app.devtools.capture --host app.slack.com --out captures/slack.jsonl

One line per response: method, URL, status, request headers with auth values
masked, request body and response body (each cut at 200 KB, token-like values
masked). Stops with Ctrl+C (or after ``--seconds``). ``./captures`` on the host
is mounted at ``/app/captures``. The file holds real people's data: keep it out
of git and delete it when the connector is written. Skill:
skills/backend/browser.md.
"""

import argparse
import asyncio
import contextlib
import json
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError

from app.browser.provider import LocalChromiumProvider
from app.config import settings
from app.connectors.browser_api import BrowserUnavailableError
from app.devtools.masking import mask_body, mask_headers, truncate

if TYPE_CHECKING:
    from playwright.async_api import Response

BODY_LIMIT = 200 * 1024
RESOURCE_TYPES = frozenset({"fetch", "xhr"})


def host_matches(url: str, host: str, include_subdomains: bool) -> bool:
    hostname = (urlsplit(url).hostname or "").lower()
    host = host.lower()
    return hostname == host or (include_subdomains and hostname.endswith("." + host))


async def response_record(response: Response) -> dict[str, Any]:
    request = response.request
    try:
        body: str | None = await response.text()
    except (PlaywrightError, UnicodeDecodeError) as exc:
        body = f"<body not available: {str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__}>"
    request_body, request_cut = truncate(mask_body(request.post_data), BODY_LIMIT)
    response_body, response_cut = truncate(mask_body(body), BODY_LIMIT)
    return {
        "at": datetime.now(UTC).isoformat(),
        "method": request.method,
        "url": mask_body(request.url),  # query strings can carry tokens too
        "resource_type": request.resource_type,
        "status": response.status,
        "request_headers": mask_headers(dict(request.headers)),
        "request_body": request_body,
        "request_body_truncated": request_cut,
        "response_headers": mask_headers(dict(response.headers)),
        "response_body": response_body,
        "response_body_truncated": response_cut,
    }


class Recorder:
    def __init__(self, out: TextIO, host: str, include_subdomains: bool) -> None:
        self._out = out
        self._host = host
        self._subdomains = include_subdomains
        self._tasks: set[asyncio.Task[None]] = set()
        self.count = 0

    def on_response(self, response: Response) -> None:
        request = response.request
        if request.resource_type not in RESOURCE_TYPES or not host_matches(request.url, self._host, self._subdomains):
            return
        task = asyncio.create_task(self._write(response))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _write(self, response: Response) -> None:
        record = await response_record(response)
        self._out.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._out.flush()
        self.count += 1
        print(f"{record['status']} {record['method']} {urlsplit(record['url']).path}", file=sys.stderr)

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


async def record(host: str, out_path: Path, seconds: float | None, include_subdomains: bool) -> int:
    provider = LocalChromiumProvider(settings.browser_cdp_host, settings.browser_cdp_port, None)
    try:
        context = await provider.connect()
    except BrowserUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    with out_path.open("a", encoding="utf-8") as out:
        recorder = Recorder(out, host, include_subdomains)
        context.on("response", recorder.on_response)
        print(f"Recording fetch/XHR to {host} into {out_path}. Ctrl+C stops.", file=sys.stderr)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=seconds)
        context.remove_listener("response", recorder.on_response)
        await recorder.drain()
    await provider.disconnect()  # never browser.close(): that would close the admin's Chromium
    print(f"Saved {recorder.count} requests to {out_path}.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", required=True, help="Host to record, e.g. app.slack.com")
    parser.add_argument("--out", required=True, type=Path, help="JSONL file, e.g. captures/slack.jsonl (appended)")
    parser.add_argument("--subdomains", action="store_true", help="Also record subdomains of --host")
    parser.add_argument("--seconds", type=float, default=None, help="Stop after this many seconds (default: Ctrl+C)")
    args = parser.parse_args(argv)
    return asyncio.run(record(args.host, args.out, args.seconds, args.subdomains))


if __name__ == "__main__":
    sys.exit(main())
