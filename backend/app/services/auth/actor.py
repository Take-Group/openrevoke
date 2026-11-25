"""Who makes the current change, for the audit log.

The API sets it from the signed-in user (``app.api.auth_deps``). Workflows and
the CLI keep the default.
"""

from contextvars import ContextVar

SYSTEM_ACTOR = "local"

current_actor: ContextVar[str] = ContextVar("current_actor", default=SYSTEM_ACTOR)
