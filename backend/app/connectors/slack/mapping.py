"""Pure parsing of the Slack web client's data: local config, Web API answers, members.

Field names follow the Slack Web API user object (``users.list``). The web
client token (``xoxc-...``) comes from ``localStorage.localConfig_v2`` of
app.slack.com. Members and billing checked on a real workspace
(docs/connectors/slack.md).
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from app.connectors.base import BillingInfo, RemoteAccount
from app.connectors.errors import ConnectorError, NeedsLogin

NAME = "Slack"
# Web API errors that mean the browser session is gone or not allowed.
AUTH_ERRORS = frozenset({"invalid_auth", "not_authed", "token_revoked", "token_expired", "account_inactive"})
SLACKBOT_ID = "USLACKBOT"
RAW_FIELDS = (
    "id",
    "team_id",
    "name",
    "deleted",
    "is_admin",
    "is_owner",
    "is_primary_owner",
    "is_restricted",
    "is_ultra_restricted",
    "is_invited_user",
)


def token_from_local_config(raw: str | None, workspace: str) -> str | None:
    """Web client token of ``workspace`` from ``localConfig_v2``; ``None`` when not logged in to it."""
    if not raw:
        return None
    try:
        config = json.loads(raw)
    except ValueError:
        return None
    teams = config.get("teams") if isinstance(config, dict) else None
    if not isinstance(teams, dict):
        return None
    for team in teams.values():
        if not isinstance(team, dict):
            continue
        host = urlsplit(str(team.get("url") or "")).hostname or ""
        if team.get("domain") == workspace or host == f"{workspace}.slack.com":
            token = team.get("token")
            return token if isinstance(token, str) and token else None
    return None


def check_api_response(body: Any, method: str) -> dict[str, Any]:
    """Slack answers HTTP 200 with ``ok: false``. Session problems raise ``NeedsLogin``."""
    if not isinstance(body, dict):
        raise ConnectorError(f"{NAME} returned an unexpected {method} response")
    if body.get("ok") is True:
        return body
    error = str(body.get("error") or "unknown_error")
    if error in AUTH_ERRORS:
        raise NeedsLogin(f"{NAME} rejected the browser session ({method}: {error}). Log in again on the Browser page.")
    raise ConnectorError(f"{NAME} {method} failed: {error}")


def next_cursor(body: dict[str, Any]) -> str | None:
    metadata = body.get("response_metadata")
    cursor = metadata.get("next_cursor") if isinstance(metadata, dict) else None
    return cursor if isinstance(cursor, str) and cursor else None


def parse_members(body: dict[str, Any]) -> list[dict[str, Any]]:
    members = body.get("members")
    if not isinstance(members, list) or not all(isinstance(member, dict) for member in members):
        raise ConnectorError(f"{NAME} users.list returned no members list")
    return members


def is_bot(member: dict[str, Any]) -> bool:
    return member.get("id") == SLACKBOT_ID or bool(member.get("is_bot")) or bool(member.get("is_app_user"))


def is_erased(member: dict[str, Any]) -> bool:
    """A deactivated member whose data Slack erased: name ``deactivateduserNNN``, e-mail on slack-corp.com.

    The admin page does not count them (checked 25.11.2026: 40 from users.list, 29 in the admin page,
    11 erased). No person is behind them any more, so they are not accounts.
    """
    profile = member.get("profile") if isinstance(member.get("profile"), dict) else {}
    email = str(profile.get("email") or "").lower()
    return bool(member.get("deleted")) and (
        str(member.get("name") or "").startswith("deactivateduser") or email.endswith("@slack-corp.com")
    )


def role_of(member: dict[str, Any]) -> str | None:
    if member.get("is_primary_owner"):
        return "primary_owner"
    if member.get("is_owner"):
        return "owner"
    if member.get("is_admin"):
        return "admin"
    if member.get("is_ultra_restricted"):
        return "single_channel_guest"
    if member.get("is_restricted"):
        return "guest"
    # users.list drops the role flags of deactivated members, so their role is unknown.
    return None if member.get("deleted") else "member"


def member_to_account(member: dict[str, Any]) -> RemoteAccount | None:
    """Account of a person; ``None`` for bots, apps, Slackbot and erased members. Deactivated ones are ``suspended``."""
    if is_bot(member) or is_erased(member):
        return None
    member_id = member.get("id")
    if not member_id:
        raise ConnectorError(f"{NAME} returned a member without id")
    profile = member.get("profile") if isinstance(member.get("profile"), dict) else {}
    email = profile.get("email")
    display = profile.get("real_name") or member.get("real_name") or profile.get("display_name") or None
    if member.get("deleted"):
        status = "suspended"
    elif member.get("is_invited_user"):
        status = "invited"
    else:
        status = "active"
    return RemoteAccount(
        external_id=str(member_id),
        email=email.strip().lower() if isinstance(email, str) and email.strip() else None,
        display_name=display,
        username=member.get("name") or None,
        role=role_of(member),
        status=status,  # type: ignore[arg-type]
        raw={key: member[key] for key in RAW_FIELDS if key in member},
    )


def team_summary(body: dict[str, Any]) -> str:
    """``auth.test`` answer in words, without ids that would mean nothing to the admin."""
    team = body.get("team") or "the workspace"
    user = body.get("user") or "an unknown user"
    return f"Logged in to Slack workspace {team} as {user}."


# Plan levels in retail.getAvailablePlans and their names in Slack's pricing page.
PLAN_NAMES = {"free": "Free", "std": "Pro", "plus": "Business+", "enterprise": "Enterprise Grid"}
TERM_PERIODS = {"1m": "monthly", "12m": "yearly"}


def billing_from_plans(body: dict[str, Any]) -> BillingInfo:
    """Current plan and price from ``retail.getAvailablePlans`` (what the admin billing page reads).

    Amounts there are in cents of ``currency``; ``cost.unit_price`` is per billed seat per term.
    Checked 25.11.2026 on a Pro workspace billed monthly.
    """
    current = body.get("team_current_product")
    currency = str(body.get("currency") or "").upper()
    status = body.get("payments_status") if isinstance(body.get("payments_status"), dict) else {}
    provisions = status.get("provisions_status") if isinstance(status.get("provisions_status"), dict) else {}
    level = str(provisions.get("level") or "")
    if not current:
        if level in ("", "free") and currency:
            return BillingInfo(plan="Free", pricing_model="flat", unit_amount=Decimal(0), currency=currency,
                               billing_period="monthly", raw={"level": level or "free"})  # fmt: skip
        raise ConnectorError(f"{NAME} billing has no current product")
    entry = _plan_entry(body.get("plans"), str(current))
    if entry is None:
        raise ConnectorError(f"{NAME} billing does not list the current product {current}")
    product, cost = entry
    term = str(product.get("term") or "")
    period = TERM_PERIODS.get(term)
    if period is None or not isinstance(cost.get("unit_price"), int) or not currency:
        raise ConnectorError(f"{NAME} billing returned an unexpected price for {current}")
    term_info = provisions.get("term_info") if isinstance(provisions.get("term_info"), dict) else {}
    seats = cost.get("billable_active_users")
    total = cost.get("total_recurring")
    level = str(product.get("level") or level)
    return BillingInfo(
        plan=PLAN_NAMES.get(level, level or None),
        pricing_model="per_seat",
        unit_amount=_cents(cost["unit_price"]),
        currency=currency,
        billing_period=period,  # type: ignore[arg-type]
        billed_seats=seats if isinstance(seats, int) else None,
        total_amount=_cents(total) if isinstance(total, int) else None,
        renews_on=_date(term_info.get("end_dt")),
        raw={"product_id": str(current), "level": level, "term": term},
    )


def _plan_entry(plans: Any, product_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not isinstance(plans, dict):
        return None
    for terms in plans.values():
        if not isinstance(terms, dict):
            continue
        for option in terms.values():
            if not isinstance(option, dict):
                continue
            product, cost = option.get("product"), option.get("cost")
            if isinstance(product, dict) and isinstance(cost, dict) and product.get("product_id") == product_id:
                return product, cost
    return None


def _cents(value: int) -> Decimal:
    return (Decimal(value) / 100).quantize(Decimal("0.01"))


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
