"""AI repair of a click recipe step (docs/browser-recipes.md, "When a recipe breaks", step 2).

``RecipeRepairService`` is the ``RecipeSupport`` a write gives the browser
session. When a step finds no element, the model from the AI settings gets the
step's goal, what its candidates found and the page's accessibility snapshot.
It tests locators on the live page (``try_locator``) and picks one
(``use_locator``); the runner's probe checks every pick, so a fix always
matches exactly one visible element. The fix is stored with ``{{param}}``
placeholders: an ordinary step as ``active`` (used now and by later runs), an
irreversible click as ``proposed`` (an admin approves it, then retries).
"""

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import ValidationError

from app.ai.base import AiError, ChatTurn, ToolError, ToolSpec
from app.database import async_session
from app.models import RecipeFix
from app.models.enums import RecipeFixStatus
from app.recipes.model import unrender_value
from app.recipes.repair import Alternative, Repair
from app.services import ai_settings, audit, recipe_fixes

if TYPE_CHECKING:
    import uuid

    from app.recipes.repair import Probe, ProbeResult, RepairRequest

logger = structlog.get_logger()

# An expect must still check a small element (a dialog, a row), not the whole page.
EXPECT_MAX_TEXT = 2000
SHOWN_TEXT = 300
# Run values shown to the model: identity and form values, not long config strings.
PARAM_LIMIT = 200

SYSTEM = """You repair one step of a click recipe that Open Revoke runs in the admin panel of a SaaS app \
(it invites or removes a user account). The panel changed, so the step's own locators no longer find \
its element. Find the element on the current page that achieves the step's goal.

Rules:
- Test every idea with try_locator. It runs on the live page and says how many visible elements match \
and the text of a single match.
- Prefer a role with its exact accessible name (role "button", name ["Deactivate"]). When the element \
repeats in every row, add "within": the row (role "row", has_text the person's e-mail) or the dialog. \
Use css only on stable attributes (id, data-*, aria-*), never on generated class names.
- Pick only an element that does what the goal says and nothing more. Never pick an element that deletes, \
deactivates, confirms or sends unless the goal (or the step before a confirmation) is exactly that, and never \
one that acts on another person than the one in the run values.
- When exactly one element matches and fits the goal, call use_locator once, then stop.
- When nothing on the page fits, do not call use_locator; answer with one sentence saying why."""

LOCATOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Exactly one of role, label, test_id, text, css; name and has_text narrow it",
    "properties": {
        "role": {"type": "string", "description": "ARIA role: button, menuitem, link, row, dialog, textbox, ..."},
        "name": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exact accessible names, any of them (only with role)",
        },
        "label": {"type": "string", "description": "Exact label of a form field"},
        "test_id": {"type": "string", "description": "Value of data-testid"},
        "text": {"type": "string", "description": "Exact visible text"},
        "css": {"type": "string", "description": "CSS selector on a stable attribute"},
        "has_text": {"type": "string", "description": "Keep only elements that contain this text"},
    },
}
ALTERNATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target": LOCATOR_SCHEMA,
        "within": {**LOCATOR_SCHEMA, "description": "Optional container that must match exactly one element"},
        "reason": {"type": "string", "description": "Why this element fits the goal (use_locator only)"},
    },
    "required": ["target"],
}
# What the whole recipe does, so a renamed control ("Deactivate" instead of "Remove") is recognised.
PURPOSE = {
    "delete_account": (
        "This recipe takes the person's access away. Panels call it Remove, Delete, Deactivate, Suspend, "
        "Disable or Revoke; any of them is the right operation here (a deactivated account counts as removed)."
    ),
    "create_account": "This recipe gives the person an account. Panels call it Invite, Add member, Add user or Create.",
}

TOOLS = [
    ToolSpec("try_locator", "Count the visible elements this locator matches on the live page.", ALTERNATIVE_SCHEMA),
    ToolSpec("use_locator", "Choose this locator for the step. It must match exactly one element.", ALTERNATIVE_SCHEMA),
]


class RecipeRepairService:
    """``RecipeSupport`` for the writes of one action (``action_id`` links the fixes to it)."""

    def __init__(self, action_id: uuid.UUID | None) -> None:
        self.action_id = action_id

    async def fixes(self, recipe_app: str, recipe_action: str) -> dict[str, list[Alternative]]:
        async with async_session() as session:
            return await recipe_fixes.active_fixes(session, recipe_app, recipe_action)

    async def repair(self, request: RepairRequest, probe: Probe) -> Repair:
        async with async_session() as session:
            row = await ai_settings.get_row(session)
            model = await ai_settings.load_model(session)
        if row is None or model is None:
            return Repair(None, False, "AI repair is off: choose a model in Settings > AI")
        chosen: list[tuple[Alternative, ProbeResult, str]] = []

        async def execute(name: str, arguments: dict[str, Any]) -> str:
            alternative = _parse(arguments)
            try:
                result = await probe(alternative)
            except ValueError as exc:
                raise ToolError(f"The page refused this locator: {exc}") from exc
            if name == "try_locator":
                return _describe(result)
            if name != "use_locator":
                raise ToolError(f"Unknown tool {name}")
            problem = _refusal(request, result)
            if problem:
                raise ToolError(problem)
            chosen.append((alternative, result, str(arguments.get("reason") or "").strip()))
            return "Accepted. Stop now."

        try:
            answer = await model.reply(
                system=SYSTEM, history=[ChatTurn(role="user", text=_prompt(request))], tools=TOOLS, execute=execute
            )
        except AiError as exc:
            logger.warning("recipe_repair_failed", app=request.recipe_app, step=request.step_index, error=str(exc))
            return Repair(None, False, f"AI repair failed: {exc}")
        if not chosen:
            reason = " ".join(answer.split())[:300]
            return Repair(None, False, f"AI repair found no fitting element: {reason or 'no answer'}")
        alternative, result, reason = chosen[-1]
        fix = await self._store(request, alternative, result, reason, author=f"ai:{row.model}")
        if request.step.irreversible:
            return Repair(
                alternative,
                False,
                f"AI proposes {alternative.describe()} for this irreversible click. "
                "Review the fix on the action, approve it, then retry",
            )
        return Repair(alternative, True, fix.note)

    async def _store(
        self, request: RepairRequest, alternative: Alternative, result: ProbeResult, reason: str, *, author: str
    ) -> RecipeFix:
        data = unrender_value(alternative.model_dump(exclude_none=True), request.params)
        shown = " ".join(result.text.split())[:120]
        note = f"Instead of the recipe's locators, {alternative.describe()} (text: “{shown}”)."
        if reason:
            note = f"{note} {reason}"
        status = RecipeFixStatus.PROPOSED if request.step.irreversible else RecipeFixStatus.ACTIVE
        async with async_session() as session:
            fix = RecipeFix(
                recipe_app=request.recipe_app,
                recipe_action=request.recipe_action,
                step_id=request.step.id,
                step_goal=request.step.goal,
                irreversible=request.step.irreversible,
                within=data.get("within"),
                target=data["target"],
                status=status,
                author=author[:200],
                note=note[:2000],
                action_id=self.action_id,
            )
            session.add(fix)
            await session.flush()
            await audit.record(
                session,
                "recipe_fix.created",
                "recipe_fix",
                fix.id,
                {
                    "recipe": f"{request.recipe_app}/{request.recipe_action}",
                    "step_id": request.step.id,
                    "status": str(status),
                    "action_id": str(self.action_id) if self.action_id else None,
                },
            )
            await session.commit()
        logger.info("recipe_fix_created", app=request.recipe_app, step=request.step.id, status=str(status))
        return fix


def _parse(arguments: dict[str, Any]) -> Alternative:
    try:
        return Alternative.model_validate(
            {"within": arguments.get("within") or None, "target": arguments.get("target")}
        )
    except ValidationError as exc:
        problems = "; ".join(error["msg"] for error in exc.errors())
        raise ToolError(f"Invalid locator: {problems}") from exc


def _describe(result: ProbeResult) -> str:
    if result.count != 1:
        return f"{result.count} visible elements match (need exactly 1)"
    return f"1 visible element matches; its text: “{' '.join(result.text.split())[:SHOWN_TEXT]}”"


def _refusal(request: RepairRequest, result: ProbeResult) -> str | None:
    """Why the pick cannot be used, or ``None``."""
    if result.count != 1:
        return f"{result.count} visible elements match; a step needs exactly one"
    step = request.step
    if step.do == "expect":
        if (step.text or "").casefold() not in result.text.casefold():
            return f"The element must contain {step.text!r}"
        if len(result.text) > EXPECT_MAX_TEXT:
            return "The element is too large (the whole page?); pick the dialog or row that names the person"
    return None


def _prompt(request: RepairRequest) -> str:
    step = request.step
    lines = [
        f'Step {request.step_index} ("{step.id}") of the {request.recipe_action} recipe of {request.recipe_app} '
        "found no element.",
        PURPOSE.get(request.recipe_action, ""),
        f"Goal: {step.goal or '(none given)'}",
        f"Kind: {step.do}",
    ]
    if step.do == "fill":
        lines.append(f"Value to type: {step.value}")
    if step.do == "expect":
        lines.append(f"The element must contain the text: {step.text}")
    if step.irreversible:
        lines.append("This click cannot be undone. An admin sees your pick before anything is clicked.")
    lines += [
        f"What the recipe's own locators found: {request.problem}",
        "Values of this run: " + ", ".join(f"{k}={v}" for k, v in request.params.items() if len(v) <= PARAM_LIMIT),
        f"Page URL: {request.url}",
        "Accessibility snapshot of the page (YAML):",
        request.page_outline,
    ]
    return "\n".join(lines)
