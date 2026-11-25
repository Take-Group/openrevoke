"""Click recipe format (docs/browser-recipes.md): JSON steps, no code.

A recipe is data. ``app/browser/recipe_runner.py`` executes it in the shared
browser; nothing in a recipe can run anything but the four step kinds.
"""

import json
import re
from functools import cache
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

from app.connectors.base import ConnectorError

if TYPE_CHECKING:
    from pathlib import Path

PARAM = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")
# An irreversible click must follow an `expect` that names the person, so it never confirms the wrong user.
IDENTITY_PARAMS = frozenset({"email", "external_id"})


class RecipeError(ConnectorError):
    """The recipe file or its parameters are wrong: nothing was clicked."""


class RecipeStepError(ConnectorError):
    """A step could not be done. Steps before it were done; the message says which step and why."""

    def __init__(
        self, message: str, *, step_index: int, step: Step, url: str | None = None, screenshot: bytes | None = None
    ) -> None:
        super().__init__(message)
        self.step_index = step_index
        self.step = step
        self.url = url
        self.screenshot = screenshot  # PNG of the tab where the step stopped, for the admin


class Locator(BaseModel):
    """One way to find an element, by the accessibility tree first, CSS last."""

    model_config = ConfigDict(extra="forbid")

    role: str | None = None
    name: list[str] | None = Field(default=None, description="Exact accessible names, any of them (languages)")
    label: str | None = None
    test_id: str | None = None
    text: str | None = None
    css: str | None = None
    has_text: str | None = Field(default=None, description="Keep only elements that contain this text")

    @model_validator(mode="after")
    def _one_kind(self) -> Self:
        kinds = [kind for kind in (self.role, self.label, self.test_id, self.text, self.css) if kind]
        if len(kinds) != 1:
            raise ValueError("a locator needs exactly one of role, label, test_id, text, css")
        if self.name is not None and self.role is None:
            raise ValueError("name works only with role")
        return self

    def describe(self) -> str:
        parts = [f"{key}={value!r}" for key, value in self.model_dump(exclude_none=True).items()]
        return " ".join(parts)


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$", description="Stable within the action; local fixes pin to it")
    do: Literal["goto", "click", "fill", "press", "expect"]
    goal: str = Field(default="", description="What the step achieves; read by people and by AI repair")
    url: str | None = None
    within: Locator | None = None
    target: list[Locator] = Field(default_factory=list, description="Candidates in order; the first single match wins")
    value: str | None = None
    text: str | None = None
    irreversible: bool = False

    @model_validator(mode="after")
    def _fields_for_kind(self) -> Self:
        if self.do == "goto":
            if not self.url or self.target:
                raise ValueError("goto needs url and no target")
        elif self.do == "press":
            if not self.value:
                raise ValueError("press needs value, the key (e.g. Enter); target is optional")
        elif not self.target:
            raise ValueError(f"{self.do} needs at least one target candidate")
        if self.do == "fill" and self.value is None:
            raise ValueError("fill needs value")
        if self.do == "expect" and not self.text:
            raise ValueError("expect needs text")
        if self.irreversible and self.do != "click":
            raise ValueError("only a click can be irreversible")
        return self

    def describe(self) -> str:
        return f"{self.id}: {self.goal}" if self.goal else self.id


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: str
    version: int = Field(ge=1)
    actions: dict[str, list[Step]]

    @model_validator(mode="after")
    def _irreversible_needs_identity_check(self) -> Self:
        for action, steps in self.actions.items():
            ids = [step.id for step in steps]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{action}: step ids must be unique")
            checked = False
            for index, step in enumerate(steps, start=1):
                if step.do == "expect" and set(PARAM.findall(step.text or "")) & IDENTITY_PARAMS:
                    checked = True
                if step.irreversible and not checked:
                    raise ValueError(
                        f"{action} step {index}: an irreversible click needs an earlier expect step "
                        "whose text contains {{email}} or {{external_id}}"
                    )
        return self

    def steps(self, action: str) -> list[Step]:
        if action not in self.actions:
            raise RecipeError(f"The {self.app} recipe has no {action} steps")
        return self.actions[action]


@cache
def load_recipe(path: Path) -> Recipe:
    """Read and validate a recipe file. Cached: files ship with the code."""
    try:
        return Recipe.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError) as exc:
        raise RecipeError(f"Recipe {path.name} is invalid: {exc}") from exc


def render_steps(steps: list[Step], params: dict[str, str]) -> list[Step]:
    """Steps with ``{{param}}`` replaced. A missing parameter fails before any click."""
    used = {name for step in steps for name in PARAM.findall(step.model_dump_json())}
    missing = sorted(used - params.keys())
    if missing:
        raise RecipeError(f"Recipe parameters missing: {', '.join(missing)}")
    return [Step.model_validate(_render(step.model_dump(), params)) for step in steps]


def render_value(value: Any, params: dict[str, str]) -> Any:
    """``value`` (str, list, dict) with ``{{param}}`` replaced. Raises ``RecipeError`` for a missing one."""
    missing = sorted({name for name in PARAM.findall(json.dumps(value)) if name not in params})
    if missing:
        raise RecipeError(f"Recipe parameters missing: {', '.join(missing)}")
    return _render(value, params)


def unrender_value(value: Any, params: dict[str, str]) -> Any:
    """The reverse of ``render_value`` for identity values (an AI fix names the person's e-mail):
    each occurrence of a parameter value of 3+ characters becomes ``{{param}}``, longest first."""
    pairs = sorted(((v, k) for k, v in params.items() if len(v) >= 3), key=lambda pair: -len(pair[0]))

    def one(text: str) -> str:
        for raw, name in pairs:
            text = text.replace(raw, "{{" + name + "}}")
        return text

    if isinstance(value, str):
        return one(value)
    if isinstance(value, list):
        return [unrender_value(item, params) for item in value]
    if isinstance(value, dict):
        return {key: unrender_value(item, params) for key, item in value.items()}
    return value


def _render(value: Any, params: dict[str, str]) -> Any:
    if isinstance(value, str):
        return PARAM.sub(lambda match: params[match.group(1)], value)
    if isinstance(value, list):
        return [_render(item, params) for item in value]
    if isinstance(value, dict):
        return {key: _render(item, params) for key, item in value.items()}
    return value


def config_params(config: BaseModel) -> dict[str, str]:
    """Plain (non-secret) fields of a connection config as recipe parameters."""
    params: dict[str, str] = {}
    for name in type(config).model_fields:
        value = getattr(config, name)
        if value is None or isinstance(value, SecretStr):
            continue
        params[name] = str(value).rstrip("/") if isinstance(value, str) else str(value)
    return params
