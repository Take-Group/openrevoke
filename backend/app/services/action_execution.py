"""Steps of ``ExecuteActionWorkflow``: start, precheck (retries), write, verify by reading, fail.

Each step opens its own session and returns the action's status after it
(``"retry"`` when a verification read should be repeated). The connector is
called with no transaction open, under the connection lock (the same lock as
sync), waiting at most ``ACTION_LOCK_WAIT_SECONDS``. Rules:

- connector errors end the action as ``failed`` with the app's message;
  ``NeedsLogin`` also sets the connection to ``needs_login``,
- a write is ``done`` only when a fresh ``list_accounts`` confirms it: the
  created account is listed (active or invited), the deleted one is gone or
  suspended. Otherwise ``failed`` after the last read, even if the write
  returned 200,
- a temporary password from ``create_account`` is stored encrypted and never
  logged or put into ``result``,
- a retried action reads first (``precheck``): when the app already shows the
  change, it is ``done`` without a second write,
- a click recipe runs with local fixes and AI repair (``RecipeRepairService``);
  where it stops, a screenshot is kept for the admin (``ActionScreenshot``).
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from sqlalchemy import delete, select

from app.browser.session import open_browser_session
from app.config import settings
from app.connectors.base import CreateAccountRequest, NeedsLogin, RemoteAccount
from app.connectors.http import build_http_client
from app.database import async_session
from app.models import Account, Action, ActionScreenshot, App, Connection, Person
from app.models.enums import AccountStatus, ActionKind, ActionStatus, ConnectionStatus
from app.recipes.model import RecipeStepError
from app.services.action_accounts import apply_created, apply_deleted
from app.services.action_approval import ensure_can_run
from app.services.actions import FINISHED_STATUSES, advance
from app.services.audit import record
from app.services.connection_lock import ConnectionBusyError, connection_lock
from app.services.connections import set_status
from app.services.connector_runtime import HttpFactory, open_context
from app.services.errors import InvalidInputError
from app.services.matching import normalize_email
from app.services.recipe_repair import RecipeRepairService
from app.services.secret_box import encrypt_value
from app.services.sync import CONNECTOR_ERRORS, FETCH_TIMEOUT_SECONDS

if TYPE_CHECKING:
    import uuid
    from collections.abc import AsyncIterator

    from app.connectors.base import Connector, ConnectorContext

logger = structlog.get_logger()

S = ActionStatus
RETRY = "retry"
SKIPPED = "skipped"
WRITE_TIMEOUT_SECONDS = 5 * 60
VERIFIED_CREATE_STATUSES = ("active", "invited")


@dataclass
class Loaded:
    action: Action
    app: App
    connection: Connection | None
    account: Account | None
    person: Person | None

    @property
    def target(self) -> str:
        email = self.action.payload.get("email")
        if self.account is not None:
            return self.account.email or self.account.username or self.account.external_id
        return email or "the account"


async def start(action_id: uuid.UUID) -> str:
    """``approved`` to ``running``. Writes switched off since approval end the action as failed."""
    async with async_session() as session:
        # Row lock: a cancel sent at the same moment either wins (no write) or gets 409.
        action = await session.get(Action, action_id, with_for_update=True)
        if action is None:
            return SKIPPED
        if action.status != S.APPROVED:
            return str(action.status)  # a retried activity, or cancelled in the meantime
        try:
            await ensure_can_run(session, action)
        except InvalidInputError as exc:
            await advance(session, action.id, S.FAILED, error=exc.message)
            await session.commit()
            return str(S.FAILED)
        await advance(session, action.id, S.RUNNING)
        await session.commit()
        return str(S.RUNNING)


async def write(action_id: uuid.UUID, http_factory: HttpFactory = build_http_client) -> str:
    """Call ``create_account`` or ``delete_account``; ``running`` to ``verifying`` or ``failed``."""
    loaded = await _load(action_id)
    if loaded is None:
        return SKIPPED
    if loaded.action.status != S.RUNNING:
        return str(loaded.action.status)
    if loaded.connection is None:
        return await fail(action_id, "The app has no connection anymore")
    if loaded.action.kind == ActionKind.DELETE_ACCOUNT and loaded.account is None:
        return await fail(action_id, "The account to delete no longer exists in Open Revoke")
    created = None
    try:
        async with connection_lock(loaded.connection.id, wait_seconds=settings.action_lock_wait_seconds):
            # The wait for the lock can take minutes (a batch on one connection). Check again under the
            # lock: "Allow writes" switched off or the connector changed in the meantime stops the write.
            refusal = await _write_refusal(action_id)
            if refusal is not None:
                return await fail(action_id, refusal)
            loaded = await _load(action_id)
            assert loaded is not None and loaded.connection is not None
            browser_factory = partial(open_browser_session, recipe_support=RecipeRepairService(action_id))
            async with (
                asyncio.timeout(WRITE_TIMEOUT_SECONDS),
                open_context(loaded.connection, http_factory, browser_factory) as (connector, ctx),
            ):
                if loaded.action.kind == ActionKind.CREATE_ACCOUNT:
                    created = await connector.create_account(ctx, _create_request(loaded))
                else:
                    await connector.delete_account(ctx, _remote_of(loaded))
    except ConnectionBusyError:
        return await fail(action_id, _busy_message())
    except NeedsLogin as exc:
        return await fail(action_id, f"Needs login: {exc}", needs_login=True)
    except RecipeStepError as exc:
        return await fail(action_id, f"The click recipe stopped at {exc}", screenshot=exc.screenshot, url=exc.url)
    except CONNECTOR_ERRORS as exc:
        return await fail(action_id, f"The app refused the write: {_describe(exc, WRITE_TIMEOUT_SECONDS)}")

    result: dict[str, Any] = {"written_at": datetime.now(UTC).isoformat()}
    async with async_session() as session:
        action = await session.get(Action, action_id)
        assert action is not None
        if (action.result or {}).get("retries"):
            result["retries"] = action.result["retries"]  # numbers the next retry's workflow id
        if created is not None:
            result["remote"] = _remote_dict(created.account)
            if created.temporary_password:
                action.secret_result_encrypted = encrypt_value(created.temporary_password)
                result["secret_kind"] = "temporary_password"
        await advance(session, action_id, S.VERIFYING, result=result, data={"written": True})
        await session.commit()
    logger.info("action_written", action_id=str(action_id), kind=str(loaded.action.kind))
    return str(S.VERIFYING)


async def verify(action_id: uuid.UUID, attempt: int, final: bool, http_factory: HttpFactory = build_http_client) -> str:
    """Read the account list and confirm the write: ``done``, ``failed`` (last read) or ``retry``."""
    loaded = await _load(action_id)
    if loaded is None:
        return SKIPPED
    if loaded.action.status != S.VERIFYING:
        return str(loaded.action.status)
    if loaded.connection is None:
        return await fail(action_id, "The app has no connection anymore, the write cannot be verified")
    try:
        async with _connector(loaded.connection, FETCH_TIMEOUT_SECONDS, http_factory) as (connector, ctx):
            accounts = await connector.list_accounts(ctx)
    except NeedsLogin as exc:
        return await fail(action_id, f"Needs login: {exc}", needs_login=True)
    except (ConnectionBusyError, *CONNECTOR_ERRORS) as exc:
        problem = _busy_message() if isinstance(exc, ConnectionBusyError) else _describe(exc, FETCH_TIMEOUT_SECONDS)
        return await _not_verified(action_id, attempt, final, f"could not read the accounts: {problem}")

    remote = _find_remote(loaded, accounts)
    problem = _verification_problem(loaded, remote)
    if problem is not None:
        return await _not_verified(action_id, attempt, final, problem)
    await _confirm(loaded, remote, {"attempts": attempt}, {"verified": True, "attempt": attempt})
    logger.info("action_verified", action_id=str(action_id), attempt=attempt)
    return str(S.DONE)


async def precheck(action_id: uuid.UUID, http_factory: HttpFactory = build_http_client) -> str:
    """Before a retried write: read the accounts. ``done`` when the app already shows the change, else ``running``.

    The failed run may have written before it stopped (a recipe past its last click, a read that timed out).
    A failed read ends the action: writing blind could create or remove the account twice.
    """
    loaded = await _load(action_id)
    if loaded is None:
        return SKIPPED
    if loaded.action.status != S.RUNNING:
        return str(loaded.action.status)
    if loaded.connection is None:
        return await fail(action_id, "The app has no connection anymore")
    if loaded.action.kind == ActionKind.DELETE_ACCOUNT and loaded.account is None:
        return str(S.RUNNING)  # the write step fails it with the reason
    try:
        async with _connector(loaded.connection, FETCH_TIMEOUT_SECONDS, http_factory) as (connector, ctx):
            accounts = await connector.list_accounts(ctx)
    except NeedsLogin as exc:
        return await fail(action_id, f"Needs login: {exc}", needs_login=True)
    except (ConnectionBusyError, *CONNECTOR_ERRORS) as exc:
        problem = _busy_message() if isinstance(exc, ConnectionBusyError) else _describe(exc, FETCH_TIMEOUT_SECONDS)
        return await fail(action_id, f"Not retried: the accounts could not be read first: {problem}")
    remote = _find_remote(loaded, accounts)
    if _verification_problem(loaded, remote) is not None:
        return str(S.RUNNING)
    await _confirm(loaded, remote, {"already_done": True}, {"verified": True, "already_done": True})
    logger.info("action_already_done", action_id=str(action_id))
    return str(S.DONE)


async def _confirm(loaded: Loaded, remote: RemoteAccount | None, extra: dict[str, Any], data: dict[str, Any]) -> None:
    """The read confirms the change: update the accounts and end the action as ``done``."""
    assert loaded.connection is not None
    async with async_session() as session:
        action = await session.get(Action, loaded.action.id)
        connection = await session.get(Connection, loaded.connection.id)
        assert action is not None and connection is not None
        if action.kind == ActionKind.CREATE_ACCOUNT:
            assert remote is not None
            await apply_created(session, action, connection, remote)
        else:
            await apply_deleted(session, action, remote)
        result = {**(action.result or {}), "verified_at": datetime.now(UTC).isoformat(), **extra}
        await advance(session, action.id, S.DONE, result=result, data=data)
        await session.commit()


async def fail(
    action_id: uuid.UUID,
    error: str,
    *,
    needs_login: bool = False,
    screenshot: bytes | None = None,
    url: str | None = None,
) -> str:
    """End the action as ``failed``. ``needs_login`` also marks the connection; ``screenshot`` is kept for
    the admin. Finished actions stay."""
    async with async_session() as session:
        action = await session.get(Action, action_id)
        if action is None:
            return SKIPPED
        if action.status in FINISHED_STATUSES:
            return str(action.status)
        await advance(session, action_id, S.FAILED, error=error)
        if screenshot:
            await session.execute(delete(ActionScreenshot).where(ActionScreenshot.action_id == action_id))
            session.add(ActionScreenshot(action_id=action_id, png=screenshot, url=url))
        if needs_login:
            connection = await session.scalar(select(Connection).where(Connection.app_id == action.app_id))
            if connection is not None:
                await set_status(session, connection, ConnectionStatus.NEEDS_LOGIN, error)
        await session.commit()
    logger.warning("action_failed", action_id=str(action_id), error=error)
    return str(S.FAILED)


@asynccontextmanager
async def _connector(
    connection: Connection, timeout_seconds: int, http_factory: HttpFactory
) -> AsyncIterator[tuple[Connector, ConnectorContext]]:
    """The connector under the connection lock; the time limit starts once the lock is held."""
    async with (
        connection_lock(connection.id, wait_seconds=settings.action_lock_wait_seconds),
        asyncio.timeout(timeout_seconds),
        open_context(connection, http_factory) as pair,
    ):
        yield pair


async def _write_refusal(action_id: uuid.UUID) -> str | None:
    """Why the write must not run now (checked under the connection lock), or ``None``."""
    async with async_session() as session:
        action = await session.get(Action, action_id)
        if action is None or action.status != S.RUNNING:
            return f"Not written: the action is {action.status if action else 'gone'}"
        try:
            await ensure_can_run(session, action)
        except InvalidInputError as exc:
            return f"Not written: {exc.message}"
    return None


async def _not_verified(action_id: uuid.UUID, attempt: int, final: bool, problem: str) -> str:
    if final:
        return await fail(action_id, f"Not confirmed by reading the app after {attempt} reads: {problem}")
    async with async_session() as session:
        await record(session, "action.verify_attempt", "action", action_id, {"attempt": attempt, "problem": problem})
        await session.commit()
    return RETRY


def _find_remote(loaded: Loaded, accounts: list[RemoteAccount]) -> RemoteAccount | None:
    if loaded.action.kind == ActionKind.DELETE_ACCOUNT:
        external_id = loaded.account.external_id if loaded.account else None
        return next((item for item in accounts if item.external_id == external_id), None)
    created = (loaded.action.result or {}).get("remote") or {}
    if created.get("external_id"):
        found = next((item for item in accounts if item.external_id == created["external_id"]), None)
        if found is not None:
            return found
    email = normalize_email(loaded.action.payload.get("email"))
    return next((item for item in accounts if email and normalize_email(item.email) == email), None)


def _verification_problem(loaded: Loaded, remote: RemoteAccount | None) -> str | None:
    """``None`` when the read confirms the write, otherwise what is wrong."""
    if loaded.action.kind == ActionKind.CREATE_ACCOUNT:
        if remote is None:
            return f"{loaded.target} is not in the account list of {loaded.app.name}"
        if remote.status not in VERIFIED_CREATE_STATUSES:
            return f"{loaded.target} is listed in {loaded.app.name} as {remote.status}"
        return None
    if remote is not None and remote.status != "suspended":
        return f"{loaded.target} is still {remote.status} in {loaded.app.name}"
    return None


async def _load(action_id: uuid.UUID) -> Loaded | None:
    async with async_session() as session:
        action = await session.get(Action, action_id)
        if action is None:
            return None
        app = await session.get(App, action.app_id)
        assert app is not None
        connection = await session.scalar(select(Connection).where(Connection.app_id == action.app_id))
        account = await session.get(Account, action.account_id) if action.account_id else None
        person = await session.get(Person, action.person_id) if action.person_id else None
        return Loaded(action=action, app=app, connection=connection, account=account, person=person)


def _create_request(loaded: Loaded) -> CreateAccountRequest:
    person = loaded.person
    return CreateAccountRequest(
        email=loaded.action.payload["email"],
        first_name=person.first_name if person else None,
        last_name=person.last_name if person else None,
        role=loaded.action.payload.get("role"),
    )


def _remote_of(loaded: Loaded) -> RemoteAccount:
    account = loaded.account
    assert account is not None
    status = account.status if account.status in (AccountStatus.ACTIVE, AccountStatus.INVITED) else "suspended"
    return RemoteAccount(
        external_id=account.external_id,
        email=account.email,
        display_name=account.display_name,
        username=account.username,
        role=account.role,
        status=str(status),  # type: ignore[arg-type]
        raw=dict(account.raw or {}),
    )


def _remote_dict(account: RemoteAccount) -> dict[str, Any]:
    return {
        "external_id": account.external_id,
        "email": account.email,
        "username": account.username,
        "display_name": account.display_name,
        "role": account.role,
        "status": account.status,
    }


def _busy_message() -> str:
    minutes = max(1, settings.action_lock_wait_seconds // 60)
    return f"Another sync or action kept the connection busy for {minutes} min. Create the action again later"


def _describe(exc: BaseException, timeout_seconds: int) -> str:
    if isinstance(exc, TimeoutError):
        return f"the app did not answer within {timeout_seconds // 60} minutes"
    if isinstance(exc, httpx.HTTPError):
        return f"network error: {exc.__class__.__name__}: {exc}"
    return str(exc) or exc.__class__.__name__
