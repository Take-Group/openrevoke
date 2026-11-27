"""Find the Google OAuth client id and consent-screen name of catalog apps from their public sign-in pages.

A "Sign in with Google" button sends the app's OAuth client id to Google in the URL, and Google's
sign-in page names the app ("to continue to Fathom"): the same id and name a Google Workspace scan
records. The script opens each app's sign-in page in headless Chromium, collects client ids from
requests to accounts.google.com (clicking a Google button when the page has one) and never signs
in. It only writes a report; ``--apply`` adds the ids to ``app/catalog/apps.json`` after you read it.

Run on the host (Playwright's Chromium), from ``open-revoke/backend``::

    uv run --no-project --with playwright python scripts/probe_google_sign_in.py \
        --out /tmp/probe.json [--all] [--more] [slug ...]
    uv run --no-project python scripts/probe_google_sign_in.py --apply /tmp/probe.json

An id found on two apps' pages is shared (an auth provider's development keys) and is dropped.
An entry's optional ``login_url`` is tried first.
"""

import argparse
import asyncio
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse, urlsplit

CATALOG = Path(__file__).resolve().parent.parent / "app" / "catalog" / "apps.json"
CLIENT_ID = re.compile(r"\d{6,}-[a-z0-9]{20,40}\.apps\.googleusercontent\.com")
CONTINUE_TO = re.compile(r"(?:to continue to|continue to)\s+(.+)", re.I)
GOOGLE_BUTTON = re.compile(r"(?:(?:sign ?in|log ?in|continue|sign ?up).{0,12}google)|(?:^google$)", re.I)
PARALLEL = 6
PAGE_TIMEOUT = 20_000


def _candidates(app: dict, more: bool) -> list[str]:
    """Sign-in pages to try; ``more`` is a second, slower round with less common addresses."""
    website = app["website"].rstrip("/")
    host = (urlparse(website).hostname or "").removeprefix("www.")
    urls = [app["login_url"]] if app.get("login_url") else []
    if more:
        urls += [
            f"https://app.{host}/signin",
            f"https://accounts.{host}/login",
            f"https://login.{host}",
            f"https://{host}/users/sign_in",
            f"https://app.{host}",
        ]
    else:
        urls += [f"https://app.{host}/login", f"{website}/login", f"https://{host}/signin"]
    return list(dict.fromkeys(urls))


def _ids_in(url: str) -> list[str]:
    found = CLIENT_ID.findall(unquote(url))
    query = parse_qs(urlparse(url).query)
    found += [value for value in query.get("client_id", []) if CLIENT_ID.fullmatch(value)]
    return found


async def _google_name(page) -> str | None:
    try:
        text = await page.inner_text("body", timeout=5000)
    except Exception:  # noqa: BLE001 - any failure means no name
        return None
    match = CONTINUE_TO.search(text)
    return match.group(1).strip().splitlines()[0].strip()[:120] if match else None


async def _probe_url(context, url: str) -> dict:
    page = await context.new_page()
    seen: list[str] = []
    google_pages: list = []
    page.on("request", lambda request: seen.extend(_ids_in(request.url)) if "google" in request.url else None)
    context.on("page", lambda popup: google_pages.append(popup))
    result: dict = {"url": url, "ids": [], "via": None, "google_name": None}
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        if response is None or response.status >= 400:
            result["via"] = f"http {response.status if response else '?'}"
            return result
        await page.wait_for_timeout(2500)
        if not seen:
            buttons = page.locator("button, a, [role=button], div[role=link]").filter(has_text=GOOGLE_BUTTON)
            if await buttons.count():
                try:
                    await buttons.first.click(timeout=4000)
                    await page.wait_for_timeout(4000)
                    result["via"] = "click"
                except Exception:  # noqa: BLE001 - a click that fails leaves what the page loaded
                    pass
        else:
            result["via"] = "page load"
        for target in [page, *google_pages]:
            if urlsplit(target.url).hostname == "accounts.google.com":
                seen.extend(_ids_in(target.url))
                result["google_name"] = await _google_name(target)
        if not seen:
            html = await page.content()
            in_html = sorted(set(CLIENT_ID.findall(html)))
            if len(in_html) == 1:
                seen.extend(in_html)
                result["via"] = "html"
    except Exception as error:  # noqa: BLE001 - one site failing must not stop the run
        result["via"] = f"error {type(error).__name__}"
    finally:
        await page.close()
    result["ids"] = sorted(set(seen))
    return result


async def _probe(browser, app: dict, limit: asyncio.Semaphore, more: bool) -> dict:
    async with limit:
        tried = []
        for url in _candidates(app, more):
            context = await browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
            try:
                result = await _probe_url(context, url)
            finally:
                await context.close()
            tried.append(result)
            if result["ids"]:
                print(f"{app['slug']:24} {', '.join(result['ids'])}  [{result['via']}] {result['google_name'] or ''}")
                return {"slug": app["slug"], **result}
        print(f"{app['slug']:24} -")
        return {"slug": app["slug"], "ids": [], "tried": tried}


async def probe(slugs: list[str], every: bool, more: bool, out: Path) -> None:
    from playwright.async_api import async_playwright

    apps = json.loads(CATALOG.read_text())["apps"]
    if slugs:
        apps = [app for app in apps if app["slug"] in slugs]
    elif not every:
        apps = [app for app in apps if not app.get("google_client_ids")]
    limit = asyncio.Semaphore(PARALLEL)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        results = await asyncio.gather(*(_probe(browser, app, limit, more) for app in apps))
        await browser.close()
    counts = Counter(client_id for result in results for client_id in result["ids"])
    for result in results:
        result["shared"] = [client_id for client_id in result["ids"] if counts[client_id] > 1]
        result["ids"] = [client_id for client_id in result["ids"] if counts[client_id] == 1]
    out.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"{sum(bool(r['ids']) for r in results)} of {len(results)} apps with a client id -> {out}")


def apply(report: Path) -> None:
    data = json.loads(CATALOG.read_text())
    taken = {client_id: app["slug"] for app in data["apps"] for client_id in app.get("google_client_ids", [])}
    found = {result["slug"]: result for result in json.loads(report.read_text())}
    for app in data["apps"]:
        result = found.get(app["slug"])
        if not result:
            continue
        new = [client_id for client_id in result["ids"] if taken.get(client_id, app["slug"]) == app["slug"]]
        if new:
            app["google_client_ids"] = sorted(set(app.get("google_client_ids", [])) | set(new))
    lines = ",\n".join("    " + json.dumps(app, ensure_ascii=False) for app in data["apps"])
    CATALOG.write_text('{\n  "apps": [\n' + lines + "\n  ]\n}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/tmp/probe.json"))
    parser.add_argument("--all", action="store_true", help="also apps that already have client ids")
    parser.add_argument("--more", action="store_true", help="second round: less common sign-in addresses")
    parser.add_argument("--apply", type=Path, help="add the ids of a report to apps.json")
    parser.add_argument("slugs", nargs="*")
    args = parser.parse_args()
    if args.apply:
        apply(args.apply)
    else:
        asyncio.run(probe(args.slugs, args.all, args.more, args.out))


if __name__ == "__main__":
    main()
