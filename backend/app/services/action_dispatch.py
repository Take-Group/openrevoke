"""Abstraction over the workflow engine for write actions (like ``sync_dispatch.SyncDispatcher``).

``app.temporal.action_dispatcher.TemporalActionDispatcher`` implements it.
API tests override it with a fake that records the calls or runs the steps inline.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid


class ActionDispatcher(Protocol):
    async def start_action(self, action_id: uuid.UUID, *, retry: int = 0) -> None:
        """Start ``ExecuteActionWorkflow`` for an approved action. ``retry`` > 0: the n-th retry, which reads
        before it writes (its own workflow id, so the failed run's history stays)."""
