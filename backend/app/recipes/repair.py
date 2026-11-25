"""What the recipe runner needs for local fixes and AI repair (docs/browser-recipes.md, "When a recipe breaks").

The runner stays deterministic and knows no database or language model: it
gets a ``RecipeSupport`` (``app/services/recipe_repair.py``) that returns the
active fixes and, when a step finds no element, asks the AI for a new one.
The runner gives it a ``Probe`` that counts matches on the live page, so
every proposal is checked against the page before it is used.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.recipes.model import Locator, Step


class Alternative(BaseModel):
    """One more way to find a step's element: an optional container plus one locator."""

    model_config = ConfigDict(extra="forbid")

    within: Locator | None = None
    target: Locator

    def describe(self) -> str:
        inside = f" within {self.within.describe()}" if self.within else ""
        return f"{self.target.describe()}{inside}"


@dataclass(frozen=True)
class ProbeResult:
    count: int  # visible elements the alternative matches (0 when its container is not exactly one)
    text: str  # inner text of the single match (cut at 5000 characters); empty otherwise


# Counts what an alternative matches on the page right now. Raises ValueError for a locator the page refuses.
type Probe = Callable[[Alternative], Awaitable[ProbeResult]]


@dataclass(frozen=True)
class RepairRequest:
    recipe_app: str
    recipe_action: str
    step_index: int
    step: Step  # rendered: parameters filled in
    params: dict[str, str]
    url: str
    problem: str  # what the step's own candidates found
    page_outline: str  # accessibility snapshot of the page (YAML), cut to a limit


@dataclass(frozen=True)
class Repair:
    """The outcome. ``alternative`` is set when the AI found exactly one fitting element.

    ``usable`` is false for an irreversible step: the fix waits for an admin and the run stops.
    ``note`` is one sentence for the action's error either way.
    """

    alternative: Alternative | None
    usable: bool
    note: str


class RecipeSupport(Protocol):
    async def fixes(self, recipe_app: str, recipe_action: str) -> dict[str, list[Alternative]]:
        """Active fixes per step id, with ``{{param}}`` placeholders."""
        ...

    async def repair(self, request: RepairRequest, probe: Probe) -> Repair:
        """Ask the AI for the step's element; stores the fix. Never raises for an AI failure."""
        ...
