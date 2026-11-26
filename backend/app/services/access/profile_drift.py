"""Access a person has against what their access profiles give: pure rules on plain data, no database.

- A profile grants an app with an optional role. Two profiles granting the same app: the role comes
  from the first profile by name that sets one; different roles give a warning (``Grants.conflicts``).
- ``missing``: an app of the person's profiles where they have no account other than ``removed``
  and no open creation. A person who has left misses nothing.
- ``extra``: an account of the person (kind ``person``, not ``removed``) in an app outside all their
  profiles. Counted only when the person has at least one profile.
- ``role_mismatch``: an account whose role differs from the profile's (case-insensitive). A profile
  without a role, or an account without a known role, is not compared.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.models.enums import AccountKind, AccountStatus

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable


@dataclass(frozen=True)
class Grant:
    """One app of one profile."""

    profile_id: uuid.UUID
    profile_name: str
    app_id: uuid.UUID
    role: str | None


@dataclass(frozen=True)
class EffectiveGrant:
    """What all profiles of a person give in one app."""

    app_id: uuid.UUID
    role: str | None
    profiles: tuple[str, ...]  # names, first by name


@dataclass(frozen=True)
class RoleConflict:
    app_id: uuid.UUID
    chosen_role: str
    chosen_profile: str
    other_role: str
    other_profile: str


@dataclass(frozen=True)
class Grants:
    by_app: dict[uuid.UUID, EffectiveGrant]
    conflicts: list[RoleConflict]


@dataclass(frozen=True)
class HeldAccount:
    account_id: uuid.UUID
    app_id: uuid.UUID
    role: str | None
    status: AccountStatus
    kind: AccountKind


@dataclass(frozen=True)
class Mismatch:
    account_id: uuid.UUID
    app_id: uuid.UUID
    role: str
    expected_role: str
    profiles: tuple[str, ...]


@dataclass(frozen=True)
class Drift:
    missing: list[EffectiveGrant] = field(default_factory=list)
    extra: list[HeldAccount] = field(default_factory=list)
    role_mismatch: list[Mismatch] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.missing or self.extra or self.role_mismatch)


def same_role(a: str | None, b: str | None) -> bool:
    return (a or "").strip().casefold() == (b or "").strip().casefold()


def resolve(grants: Iterable[Grant]) -> Grants:
    """Merge the grants of several profiles per app (first profile by name decides the role)."""
    ordered = sorted(grants, key=lambda grant: (grant.profile_name.casefold(), grant.profile_name))
    per_app: dict[uuid.UUID, list[Grant]] = {}
    for grant in ordered:
        per_app.setdefault(grant.app_id, []).append(grant)
    by_app: dict[uuid.UUID, EffectiveGrant] = {}
    conflicts: list[RoleConflict] = []
    for app_id, items in per_app.items():
        with_role = [grant for grant in items if grant.role]
        chosen = with_role[0] if with_role else None
        for other in with_role[1:]:
            if chosen is not None and not same_role(other.role, chosen.role):
                conflicts.append(
                    RoleConflict(
                        app_id=app_id,
                        chosen_role=chosen.role or "",
                        chosen_profile=chosen.profile_name,
                        other_role=other.role or "",
                        other_profile=other.profile_name,
                    )
                )
        by_app[app_id] = EffectiveGrant(
            app_id=app_id,
            role=chosen.role if chosen else None,
            profiles=tuple(dict.fromkeys(grant.profile_name for grant in items)),
        )
    return Grants(by_app=by_app, conflicts=conflicts)


def compute(
    *,
    has_left: bool,
    grants: Grants,
    accounts: Iterable[HeldAccount],
    creating: set[uuid.UUID],
) -> Drift:
    """Drift of one person. ``creating``: apps with an open creation (action or manual task)."""
    live = [account for account in accounts if account.status != AccountStatus.REMOVED]
    held_apps = {account.app_id for account in live}
    missing = []
    if not has_left:
        missing = [
            grant for app_id, grant in grants.by_app.items() if app_id not in held_apps and app_id not in creating
        ]
    extra = []
    if grants.by_app:
        extra = [
            account for account in live if account.kind == AccountKind.PERSON and account.app_id not in grants.by_app
        ]
    mismatches = []
    for account in live:
        grant = grants.by_app.get(account.app_id)
        if grant is None or not grant.role or not account.role or same_role(grant.role, account.role):
            continue
        mismatches.append(
            Mismatch(
                account_id=account.account_id,
                app_id=account.app_id,
                role=account.role,
                expected_role=grant.role,
                profiles=grant.profiles,
            )
        )
    return Drift(missing=missing, extra=extra, role_mismatch=mismatches)
