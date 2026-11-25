"""Download the logo of every app in the catalog into ``app/catalog/logos/<slug>.png``.

The panel never asks a third party for a logo at run time; this script runs once by hand when apps
are added to ``app/catalog/apps.json``, and the PNG files are committed. It reads the app's website,
takes its largest raster icon (apple-touch-icon, ``<link rel=icon sizes>``, web manifest), falls back
to Google's favicon service, and stores a 128x128 PNG. It prints each site's ``<title>`` so a wrong
website is easy to spot. Entries with ``logo`` (they reuse another app's file) or ``"fetch_logo": false``
(the site's icon is wrong, the app shows initials) are skipped.

Run on the host (it needs Pillow), from ``open-revoke/backend``::

    uv run --no-project --with httpx --with pillow --with beautifulsoup4 \
        python scripts/fetch_catalog_logos.py [--force] [slug ...]
"""

import argparse
import io
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from PIL import Image

CATALOG = Path(__file__).resolve().parent.parent / "app" / "catalog"
SIZE = 128
PADDING = 12  # margin around a transparent mark, in px of the 128 px square
MIN_SOURCE = 32  # smaller icons look blurry at 44 px; better initials than a smudge
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
)


def _size_of(value: str | None) -> int:
    best = 0
    for part in (value or "").lower().split():
        width = part.split("x")[0]
        if width.isdigit():
            best = max(best, int(width))
        elif part == "any":
            best = max(best, 512)
    return best


def _candidates(client: httpx.Client, base: str, html: str) -> list[tuple[int, str]]:
    """Icon URLs from the page, biggest first. SVG is skipped: Pillow cannot draw it."""
    soup = BeautifulSoup(html, "html.parser")
    found: list[tuple[int, str]] = []
    for link in soup.find_all("link", href=True):
        rel = " ".join(link.get("rel") or []).lower()
        if "icon" not in rel or "mask-icon" in rel:
            continue
        href = urljoin(base, link["href"])
        if href.lower().split("?")[0].endswith(".svg") or link.get("type") == "image/svg+xml":
            continue
        size = _size_of(link.get("sizes")) or (180 if "apple-touch-icon" in rel else 16)
        found.append((size, href))
    manifest = soup.find("link", rel=lambda value: value and "manifest" in value)
    if manifest and manifest.get("href"):
        try:
            data = client.get(urljoin(base, manifest["href"])).json()
            for icon in data.get("icons", []):
                src = icon.get("src")
                if src and not src.lower().split("?")[0].endswith(".svg"):
                    found.append((_size_of(icon.get("sizes")), urljoin(base, src)))
        except httpx.HTTPError, ValueError, AttributeError:
            pass
    found.append((180, urljoin(base, "/apple-touch-icon.png")))
    return sorted(found, key=lambda item: -item[0])


def _load(client: httpx.Client, url: str) -> Image.Image | None:
    if not url.startswith(("http://", "https://")):
        return None
    try:
        response = client.get(url)
    except httpx.HTTPError, ValueError:
        return None
    if response.status_code != 200 or not response.content:
        return None
    try:
        image = Image.open(io.BytesIO(response.content))
        if image.format == "ICO":
            image.size = max(image.ico.sizes())  # the largest frame of the .ico
        image.load()
    except OSError, ValueError, AttributeError:
        return None
    if min(image.size) < MIN_SOURCE:
        return None
    return image.convert("RGBA")


def _square(image: Image.Image) -> Image.Image:
    """Trim transparent edges, then fit into SIZE x SIZE on a transparent canvas, scaling up small icons.

    A full-bleed icon (no transparency) fills the square; a transparent mark keeps a margin.
    """
    bbox = image.getchannel("A").getbbox()
    if bbox:
        image = image.crop(bbox)
    opaque = image.getchannel("A").getextrema()[0] == 255
    inner = SIZE if opaque else SIZE - 2 * PADDING
    scale = inner / max(image.size)
    image = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS
    )
    # A light mark on a transparent background would vanish on the panel's white tile: give it a dark one.
    background = (23, 23, 23, 255) if not opaque and _is_light(image) else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (SIZE, SIZE), background)
    canvas.paste(image, ((SIZE - image.width) // 2, (SIZE - image.height) // 2), image)
    return canvas


def _is_light(image: Image.Image) -> bool:
    """True when almost every visible pixel is near white (a white mark, not a white app icon with a logo)."""
    mask = image.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    histogram = image.convert("L").histogram(mask=mask)
    visible = sum(histogram)
    return visible > 0 and sum(histogram[235:]) / visible > 0.97


def fetch(client: httpx.Client, app: dict) -> tuple[str, str]:
    website = app["website"]
    title = "?"
    sources: list[tuple[int, str]] = []
    try:
        page = client.get(website)
        base = str(page.url)
        soup = BeautifulSoup(page.text, "html.parser")
        title = (soup.title.string or "").strip()[:70] if soup.title else f"HTTP {page.status_code}"
        sources = _candidates(client, base, page.text)
    except httpx.HTTPError as error:
        title = f"error: {type(error).__name__}"
    host = urlparse(website).hostname or ""
    sources.append((128, f"https://www.google.com/s2/favicons?domain={host}&sz=128"))
    for _, url in sources:
        image = _load(client, url)
        if image is not None:
            _square(image).save(CATALOG / "logos" / f"{app['slug']}.png", optimize=True)
            return title, url
    return title, "no logo"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="download again even when the file exists")
    parser.add_argument("slugs", nargs="*")
    args = parser.parse_args()
    apps = json.loads((CATALOG / "apps.json").read_text())["apps"]
    (CATALOG / "logos").mkdir(exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=15, headers={"User-Agent": USER_AGENT}) as client:
        for app in apps:
            if args.slugs and app["slug"] not in args.slugs:
                continue
            target = CATALOG / "logos" / f"{app['slug']}.png"
            if app.get("logo") or app.get("fetch_logo") is False or (target.exists() and not args.force):
                continue
            title, source = fetch(client, app)
            print(f"{app['slug']:24} {title:72} {source}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
