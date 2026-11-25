"""Synchronization of one connection: read from the connector, then store in one transaction.

Called by the activities of ``SyncConnectionWorkflow``. Steps:

1. ``start_run``: the ``sync_run`` row (the API creates it for "Sync now",
   a scheduled run creates it here).
2. ``run``: under the connection lock, read accounts (and people when the
   connection is a people source) with no transaction open, then apply
   everything in one transaction. ``NeedsLogin`` ends with ``needs_login``
   and touches no account; any other connector error or the 30% threshold
   ends with ``failed`` and touches no account either. A connector with
   ``READ_BILLING`` also reads the app's plan and price (``services/billing``);
   a billing error is logged and never fails the account sync.
3. ``fail_run``: the workflow's last resort when ``run`` crashed for good.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import structlog

from app.connectors.base import Capability, ConnectorError, NeedsLogin
from app.connectors.http import build_http_client
from app.database import async_session
from app.models import Connection, SyncRun
from app.models.enums import ConnectionStatus, SyncRunStatus
from app.services.billing import apply_billing
from app.services.connection_lock import ConnectionBusyError, connection_lock
from app.services.connections import set_status
from app.services.connector_runtime import HttpFactory, open_context
from app.services.people_sync import apply_people
from app.services.secret_box import SecretsUnreadableError
from app.services.sync_accounts import apply_accounts
from app.services.sync_rules import RemovalThresholdError, clean_accounts

if TYPE_CHECKING:
    import uuid

    from app.connectors.base import BillingInfo, RemoteAccount, RemotePerson

logger = structlog.get_logger()

FETCH_TIMEOUT_SECONDS = 20 * 60
CONNECTOR_ERRORS = (ConnectorError, SecretsUnreadableError, httpx.HTTPError, TimeoutError)


@dataclass
class SyncOutcome:
    sync_run_id: str | None
    status: str
    accounts_seen: int = 0
    accounts_added: int = 0
    accounts_removed: int = 0
    people_created: int = 0
    error: str | None = None


@dataclass
class Fetched:
    accounts: list[RemoteAccount]
    people: list[RemotePerson] | None
    billing: BillingInfo | None = None


async def start_run(connection_id: uuid.UUID, sync_run_id: uuid.UUID | None) -> uuid.UUID | None:
    """Return the run to execute: the given one, or a new one for a scheduled sync. ``None`` when gone."""
    async with async_session() as session:
        if sync_run_id is not None:
            run = await session.get(SyncRun, sync_run_id)
            return run.id if run is not None else None
        if await session.get(Connection, connection_id) is None:
            return None
        run = SyncRun(connection_id=connection_id, status=SyncRunStatus.RUNNING)
        session.add(run)
        await session.commit()
        return run.id


async def run(
    sync_run_id: uuid.UUID, *, force: bool = False, http_factory: HttpFactory = build_http_client
) -> SyncOutcome:
    async with async_session() as session:
        sync_run = await session.get(SyncRun, sync_run_id)
        if sync_run is None:
            return SyncOutcome(sync_run_id=None, status="skipped", error="Sync run not found")
        if sync_run.status != SyncRunStatus.RUNNING:
            return _outcome(sync_run)  # a retried activity: the run already finished
        connection_id = sync_run.connection_id
    try:
        async with connection_lock(connection_id):
            return await _run_locked(sync_run_id, connection_id, force, http_factory)
    except ConnectionBusyError as exc:
        return await _finish_failed(sync_run_id, SyncRunStatus.FAILED, str(exc), touch_connection=False)


async def fail_run(sync_run_id: uuid.UUID, error: str) -> SyncOutcome:
    """Close a run that crashed (infrastructure error after all retries)."""
    return await _finish_failed(sync_run_id, SyncRunStatus.FAILED, error, touch_connection=True)


async def _run_locked(
    sync_run_id: uuid.UUID, connection_id: uuid.UUID, force: bool, http_factory: HttpFactory
) -> SyncOutcome:
    async with async_session() as session:
        connection = await session.get(Connection, connection_id)
    if connection is None:
        return SyncOutcome(sync_run_id=str(sync_run_id), status="skipped", error="Connection deleted")

    try:
        async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
            fetched = await _fetch(connection, http_factory)
    except NeedsLogin as exc:
        return await _finish_failed(sync_run_id, SyncRunStatus.NEEDS_LOGIN, str(exc), touch_connection=True)
    except CONNECTOR_ERRORS as exc:
        message = str(exc) or exc.__class__.__name__
        if isinstance(exc, TimeoutError):
            message = f"The app did not return the full list within {FETCH_TIMEOUT_SECONDS // 60} minutes"
        elif isinstance(exc, httpx.HTTPError):
            message = f"Network error while reading the app: {exc.__class__.__name__}: {exc}"
        return await _finish_failed(sync_run_id, SyncRunStatus.FAILED, message, touch_connection=True)

    async with async_session() as session:
        connection = await session.get(Connection, connection_id)
        sync_run = await session.get(SyncRun, sync_run_id)
        if connection is None or sync_run is None:
            return SyncOutcome(sync_run_id=str(sync_run_id), status="skipped", error="Connection deleted")
        try:
            people_stats = (
                await apply_people(session, connection, fetched.people) if fetched.people is not None else None
            )
            stats = await apply_accounts(session, connection, clean_accounts(fetched.accounts), force=force)
            if fetched.billing is not None:
                await apply_billing(session, connection.app_id, fetched.billing)
        except RemovalThresholdError as exc:
            await session.rollback()
            return await _finish_failed(sync_run_id, SyncRunStatus.FAILED, str(exc), touch_connection=True)
        now = datetime.now(UTC)
        sync_run.status = SyncRunStatus.OK
        sync_run.finished_at = now
        sync_run.accounts_seen = stats.seen
        sync_run.accounts_added = stats.added
        sync_run.accounts_removed = stats.removed
        sync_run.error = None
        connection.last_synced_at = now
        await set_status(session, connection, ConnectionStatus.OK)
        await session.commit()
        outcome = _outcome(sync_run)
        outcome.people_created = people_stats.created if people_stats else 0
    logger.info("sync_finished", connection_id=str(connection_id), **_log_fields(outcome))
    return outcome


async def _fetch(connection: Connection, http_factory: HttpFactory) -> Fetched:
    async with open_context(connection, http_factory) as (connector, ctx):
        people = None
        if connection.is_people_source and connector.supports(Capability.LIST_PEOPLE):
            people = await connector.list_people(ctx)
        accounts = await connector.list_accounts(ctx)
        billing = None
        if connector.supports(Capability.READ_BILLING):
            try:
                billing = await connector.read_billing(ctx)
            except ConnectorError as exc:  # NeedsLogin included: the accounts above were read fine
                logger.warning("billing_read_failed", connection_id=str(connection.id), error=str(exc))
    return Fetched(accounts=accounts, people=people, billing=billing)


async def _finish_failed(
    sync_run_id: uuid.UUID, status: SyncRunStatus, error: str, *, touch_connection: bool
) -> SyncOutcome:
    """Close the run with an error. Accounts stay as they are."""
    async with async_session() as session:
        sync_run = await session.get(SyncRun, sync_run_id)
        if sync_run is None:
            return SyncOutcome(sync_run_id=None, status="skipped", error=error)
        sync_run.status = status
        sync_run.finished_at = datetime.now(UTC)
        sync_run.error = error
        if touch_connection:
            connection = await session.get(Connection, sync_run.connection_id)
            if connection is not None:
                connection_status = (
                    ConnectionStatus.NEEDS_LOGIN if status == SyncRunStatus.NEEDS_LOGIN else ConnectionStatus.ERROR
                )
                await set_status(session, connection, connection_status, error)
        await session.commit()
        outcome = _outcome(sync_run)
    logger.warning("sync_failed", sync_run_id=str(sync_run_id), status=str(status), error=error)
    return outcome


def _outcome(sync_run: SyncRun) -> SyncOutcome:
    return SyncOutcome(
        sync_run_id=str(sync_run.id),
        status=str(sync_run.status),
        accounts_seen=sync_run.accounts_seen,
        accounts_added=sync_run.accounts_added,
        accounts_removed=sync_run.accounts_removed,
        error=sync_run.error,
    )


def _log_fields(outcome: SyncOutcome) -> dict[str, object]:
    return {
        "sync_run_id": outcome.sync_run_id,
        "status": outcome.status,
        "seen": outcome.accounts_seen,
        "added": outcome.accounts_added,
        "removed": outcome.accounts_removed,
        "people_created": outcome.people_created,
    }
