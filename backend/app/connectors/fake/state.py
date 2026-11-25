"""Writes of the fake connector, kept in Redis so a later read (verification, sync) sees them.

Per e-mail domain of the connection: a hash of created accounts and a set of
deleted external ids. Development and tests only.
"""

import json
from dataclasses import asdict

from app.connectors.base import RemoteAccount
from app.redis import redis_client

KEY_PREFIX = "open-revoke:fake-connector"


def _keys(domain: str) -> tuple[str, str]:
    return f"{KEY_PREFIX}:{domain}:created", f"{KEY_PREFIX}:{domain}:deleted"


async def apply_state(domain: str, generated: list[RemoteAccount]) -> list[RemoteAccount]:
    """The generated accounts plus the created ones, minus the deleted ones."""
    created_key, deleted_key = _keys(domain)
    created = [RemoteAccount(**json.loads(value)) for value in (await redis_client.hvals(created_key))]
    deleted = set(await redis_client.smembers(deleted_key))
    accounts = [*generated, *sorted(created, key=lambda account: account.external_id)]
    return [account for account in accounts if account.external_id not in deleted]


async def add_created(domain: str, account: RemoteAccount) -> None:
    created_key, deleted_key = _keys(domain)
    await redis_client.hset(created_key, account.external_id, json.dumps(asdict(account)))
    await redis_client.srem(deleted_key, account.external_id)


async def mark_deleted(domain: str, external_id: str) -> None:
    created_key, deleted_key = _keys(domain)
    await redis_client.hdel(created_key, external_id)
    await redis_client.sadd(deleted_key, external_id)
