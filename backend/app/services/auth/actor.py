"""Who makes the current change, for the audit log and for decisions on access requests.

The API sets it from the signed-in user (``app.api.auth_deps``): the label (e-mail, or the token
name), the panel user and the channel (``panel`` for the cookie, ``api`` for a token). The Slack
agent sets it for a click on its buttons. Workflows and the CLI keep the defaults.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.models.enums import DecisionVia

if TYPE_CHECKING:
    import uuid

SYSTEM_ACTOR = "local"

current_actor: ContextVar[str] = ContextVar("current_actor", default=SYSTEM_ACTOR)
current_user_id: ContextVar[uuid.UUID | None] = ContextVar("current_user_id", default=None)
current_via: ContextVar[DecisionVia] = ContextVar("current_via", default=DecisionVia.AUTOMATIC)


@dataclass(frozen=True)
class ActorRef:
    """Who approved or decided: a label to show, the panel user when there is one, and the channel."""

    label: str
    user_id: uuid.UUID | None = None
    via: DecisionVia = DecisionVia.AUTOMATIC


def set_actor(label: str, user_id: uuid.UUID | None, via: DecisionVia) -> None:
    current_actor.set(label)
    current_user_id.set(user_id)
    current_via.set(via)


def actor_ref() -> ActorRef:
    """The actor of the current request, task or click."""
    return ActorRef(current_actor.get(), current_user_id.get(), current_via.get())


def created_by_label() -> str | None:
    """The actor's label for ``created_by``; None in workflows and the CLI."""
    label = current_actor.get()
    return None if label == SYSTEM_ACTOR else label
