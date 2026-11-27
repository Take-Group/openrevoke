"""Runs a click recipe in its own tab of the shared browser (docs/browser-recipes.md).

Deterministic: no language model here. For every step the runner tries the
local fixes first, then the recipe's ``target`` candidates in order; the first
that matches exactly one visible element wins. When none does and a
``RecipeSupport`` is given, it asks for an AI repair: a repaired ordinary step
runs on, a repaired irreversible click or removal step stops the run until an admin approves
the fix. An ``expect`` whose element lacks the text is never repaired: that is
the safety check. A failed step comes back with a screenshot of the tab. The
tab is closed after the run, so the panel tab used by ``fetch()`` and the
admin's tabs stay as they were.
"""

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

import structlog
from playwright.async_api import Error as PlaywrightError

from app.connectors.errors import NeedsLogin
from app.recipes.model import Locator, RecipeError, RecipeStepError, Step, render_value
from app.recipes.repair import Alternative, ProbeResult, RepairRequest

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page
    from playwright.async_api import Locator as PwLocator

    from app.recipes.repair import RecipeSupport

logger = structlog.get_logger()

FIND_TIMEOUT_SECONDS = 10.0
POLL_SECONDS = 0.25
ACTION_TIMEOUT_MS = 10_000
NAVIGATION_TIMEOUT_MS = 45_000
# Repairs in one run: a page that changed everywhere is a job for a person.
MAX_REPAIRS = 3
OUTLINE_LIMIT = 40_000
# Text of a probed element: enough to check an expect and to see a too-large pick.
TEXT_LIMIT = 5000


class _NotFoundError(Exception):
    pass


class _RepairStopError(Exception):
    """The repair found nothing usable; the note says why."""


class _ExpectMismatchError(Exception):
    """An ``expect`` element lacks the text: the safety stop, never repaired."""


async def run_steps(
    context: BrowserContext,
    steps: list[Step],
    *,
    origin: str,
    app_name: str,
    recipe_action: str = "",
    params: dict[str, str] | None = None,
    fixes: dict[str, list[Alternative]] | None = None,
    support: RecipeSupport | None = None,
) -> None:
    """Run rendered ``steps`` in a new tab. ``origin`` is the panel's; leaving it on a goto means a lost session.

    ``fixes`` (with ``{{param}}`` placeholders) are rendered with ``params``; a fix whose parameter is
    missing is skipped. Without ``support`` a step that finds nothing fails at once.
    """
    params = params or {}
    rendered = _render_fixes(fixes or {}, params)
    page = await context.new_page()
    repairs = 0
    try:
        for index, step in enumerate(steps, start=1):
            logger.info("recipe_step", app=app_name, step=index, do=step.do)
            extra = rendered.get(step.id, [])
            try:
                try:
                    await _run_step(page, step, extra, origin=origin, app_name=app_name)
                except _NotFoundError as exc:
                    if support is None or repairs >= MAX_REPAIRS:
                        raise
                    repairs += 1
                    request = RepairRequest(
                        recipe_app=app_name,
                        recipe_action=recipe_action,
                        step_index=index,
                        step=step,
                        params=params,
                        url=page.url,
                        problem=str(exc),
                        page_outline=await _outline(page),
                    )
                    repair = await support.repair(request, lambda alt: _probe(page, alt))
                    if repair.alternative is None or not repair.usable:
                        raise _RepairStopError(f"{exc}. {repair.note.rstrip('.')}") from exc
                    logger.info("recipe_step_repaired", app=app_name, step=index)
                    await _run_step(page, step, [repair.alternative], origin=origin, app_name=app_name, only=True)
            except RecipeStepError, NeedsLogin:
                raise
            except PlaywrightError as exc:
                raise await _step_error(index, step, page, _short(exc)) from exc
            except (_NotFoundError, _RepairStopError, _ExpectMismatchError) as exc:
                raise await _step_error(index, step, page, str(exc)) from exc
    finally:
        with contextlib.suppress(PlaywrightError):
            await page.close()


async def _run_step(
    page: Page, step: Step, extra: list[Alternative], *, origin: str, app_name: str, only: bool = False
) -> None:
    if step.do == "goto":
        assert step.url is not None
        await page.goto(step.url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        with contextlib.suppress(PlaywrightError):
            await page.wait_for_load_state("load", timeout=ACTION_TIMEOUT_MS)
        if not page.url.lower().startswith(origin):
            raise NeedsLogin(f"{app_name} sent the browser away from {origin}: log in again on the Browser page.")
        return
    if step.do == "press" and not step.target:
        await page.keyboard.press(step.value or "")
        return
    element = await _find(page, extra if only else [*extra, *_own(step)])
    if step.do == "press":
        await element.press(step.value or "", timeout=ACTION_TIMEOUT_MS)
    elif step.do == "click":
        await element.click(timeout=ACTION_TIMEOUT_MS)
    elif step.do == "fill":
        await element.fill(step.value or "", timeout=ACTION_TIMEOUT_MS)
    elif step.do == "expect":
        content = await element.inner_text(timeout=ACTION_TIMEOUT_MS)
        if (step.text or "").casefold() not in content.casefold():
            raise _ExpectMismatchError(f"the element does not contain {step.text!r}")


def _own(step: Step) -> list[Alternative]:
    return [Alternative(within=step.within, target=candidate) for candidate in step.target]


async def _find(page: Page, alternatives: list[Alternative]) -> PwLocator:
    """The single visible element of the first matching alternative, waiting up to ``FIND_TIMEOUT_SECONDS``."""
    deadline = time.monotonic() + FIND_TIMEOUT_SECONDS
    while True:
        counts: list[str] = []
        for alternative in alternatives:
            locator, count = await _resolve(page, alternative)
            if locator is not None:
                return locator
            counts.append(f"{alternative.describe()} -> {count}")
        if time.monotonic() >= deadline:
            raise _NotFoundError(f"no candidate matched exactly one visible element ({'; '.join(counts)})")
        await asyncio.sleep(POLL_SECONDS)


async def _resolve(page: Page, alternative: Alternative) -> tuple[PwLocator | None, int]:
    """The locator when it matches exactly one visible element, and the count (0 when the container is not one)."""
    scope: Page | PwLocator = page
    if alternative.within is not None:
        container = _locator(page, alternative.within)
        if await container.count() != 1:
            return None, 0
        scope = container
    locator = _locator(scope, alternative.target)
    count = await locator.count()
    return (locator if count == 1 else None), count


async def _probe(page: Page, alternative: Alternative) -> ProbeResult:
    try:
        locator, count = await _resolve(page, alternative)
        if locator is None:
            return ProbeResult(count=count, text="")
        text = await locator.inner_text(timeout=ACTION_TIMEOUT_MS)
    except PlaywrightError as exc:
        raise ValueError(_short(exc)) from exc
    return ProbeResult(count=1, text=" ".join(text.split())[:TEXT_LIMIT])


def _locator(scope: Page | PwLocator, candidate: Locator) -> PwLocator:
    if candidate.role is not None:
        role = candidate.role
        if candidate.name:
            locator = scope.get_by_role(role, name=candidate.name[0], exact=True)  # type: ignore[arg-type]
            for name in candidate.name[1:]:
                locator = locator.or_(scope.get_by_role(role, name=name, exact=True))  # type: ignore[arg-type]
        else:
            locator = scope.get_by_role(role)  # type: ignore[arg-type]
    elif candidate.label is not None:
        locator = scope.get_by_label(candidate.label, exact=True)
    elif candidate.test_id is not None:
        locator = scope.get_by_test_id(candidate.test_id)
    elif candidate.text is not None:
        locator = scope.get_by_text(candidate.text, exact=True)
    elif candidate.css is not None:
        locator = scope.locator(candidate.css)
    else:  # the model validator forbids it
        raise RecipeError(f"Empty locator: {candidate.describe()}")
    if candidate.has_text:
        locator = locator.filter(has_text=candidate.has_text)
    return locator.filter(visible=True)


def _render_fixes(fixes: dict[str, list[Alternative]], params: dict[str, str]) -> dict[str, list[Alternative]]:
    rendered: dict[str, list[Alternative]] = {}
    for step_id, alternatives in fixes.items():
        for alternative in alternatives:
            try:
                data = render_value(alternative.model_dump(exclude_none=True), params)
            except RecipeError:
                continue
            rendered.setdefault(step_id, []).append(Alternative.model_validate(data))
    return rendered


async def _outline(page: Page) -> str:
    """The page as the accessibility tree sees it (roles, names), for the AI."""
    try:
        outline = await page.locator("body").aria_snapshot(timeout=ACTION_TIMEOUT_MS)
    except PlaywrightError as exc:
        return f"(no accessibility snapshot: {_short(exc)})"
    return outline[:OUTLINE_LIMIT]


async def _step_error(index: int, step: Step, page: Page, reason: str) -> RecipeStepError:
    done = {1: "Nothing was done", 2: "Step 1 was done"}.get(index, f"Steps 1-{index - 1} were done")
    screenshot = None
    with contextlib.suppress(PlaywrightError):
        screenshot = await page.screenshot(type="png", timeout=ACTION_TIMEOUT_MS)
    return RecipeStepError(
        f"step {index} ({step.describe()}) failed on {page.url}: {reason}. {done}.",
        step_index=index,
        step=step,
        url=page.url,
        screenshot=screenshot,
    )


def _short(exc: BaseException) -> str:
    text = str(exc).strip()
    return text.splitlines()[0][:300] if text else exc.__class__.__name__
