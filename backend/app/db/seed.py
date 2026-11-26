"""Development data: the organization, panel users and sample apps.

People and their accounts come from a people source: a real Google Workspace with
SEED_GOOGLE_* in `.env` (``seed_google``), otherwise a fictional directory at example.com
(``seed_demo``). The panel sign-in uses
the DEV_PREFILL_* settings (default admin@example.com / open-revoke-dev-password); the admin has
no 2FA yet, so the first sign-in offers to set it up or skip it.

With OPEN_REVOKE_DEV_PREFILL on, the users also get fixed API tokens (``DEV_API_TOKENS``) for the
MCP server, so a local AI assistant keeps working after a reset.

Add what a new feature needs to see in the panel here, so that
``python -m app.db reset`` brings it back after every schema change.
"""

from decimal import Decimal

from app.config import settings
from app.database import async_session
from app.db.seed_demo import seed_demo_directory
from app.db.seed_google import seed_google_workspace
from app.models import AccessProfile, AccessProfileApp, Organization, User
from app.models.enums import (
    ApiTokenScope,
    BillingPeriod,
    Integration,
    PasswordManager,
    PricingModel,
    RequestPolicy,
    UserRole,
)
from app.schemas.apps import AppCreate, PriceIn
from app.services import apps
from app.services.auth import api_tokens, passwords
from app.services.auth.actor import current_actor

# Local development only (fictional data on 127.0.0.1): (user, token name, scope, token).
DEV_API_TOKENS = [
    (settings.dev_prefill_email, "Local AI assistant", ApiTokenScope.WRITE, "orv_dev_admin_local_only"),
    ("member@example.com", "Local AI assistant", ApiTokenScope.WRITE, "orv_dev_member_local_only"),
]

# (name, pricing model, price per seat or plan, currency, who approves access requests)
APPS = [
    ("Slack", PricingModel.PER_SEAT, "8.75", "USD", RequestPolicy.MANAGER),
    ("Notion", PricingModel.PER_SEAT, "10", "USD", RequestPolicy.MANAGER_THEN_ADMIN),
    ("Figma", PricingModel.PER_SEAT, "15", "EUR", RequestPolicy.ADMIN),
    ("1Password", PricingModel.FLAT, "399", "PLN", RequestPolicy.OFF),
    ("Miro", PricingModel.FREE, None, None, RequestPolicy.AUTOMATIC),
]

# (name, description, requests skip the manager, [(app, role)])
PROFILES = [
    ("Every employee", "What everyone gets on the first day", True, [("Slack", "member"), ("Miro", None)]),
    ("Designer", "Design team", False, [("Figma", "editor"), ("Notion", "member")]),
]


async def seed() -> None:
    current_actor.set("seed")
    async with async_session() as session, session.begin():
        session.add(
            Organization(
                id=1,
                name=settings.dev_prefill_organization,
                currency=settings.dev_prefill_currency,
                timezone=settings.timezone,
                password_manager=PasswordManager.ONE_PASSWORD,
            )
        )
        users = [
            _user(settings.dev_prefill_email, settings.dev_prefill_name, UserRole.ADMIN),
            _user("member@example.com", "Dev Member", UserRole.USER),
            # A manager who approves requests of their people (manager step of access requests).
            _user("manager@example.com", "Dev Manager", UserRole.USER),
        ]
        session.add_all(users)
        await session.flush()
        if settings.dev_prefill:
            by_email = {user.email: user for user in users}
            for email, name, scope, token in DEV_API_TOKENS:
                await api_tokens.create(session, by_email[email], name=name, scope=scope, token=token)

        created = {}
        for name, model, amount, currency, request_policy in APPS:
            price = None
            if amount is not None:
                price = PriceIn(amount=Decimal(amount), currency=currency, billing_period=BillingPeriod.MONTHLY)
            created[name] = await apps.create_app(
                session,
                AppCreate(
                    name=name,
                    integration=Integration.MANUAL,
                    pricing_model=model,
                    price=price,
                    request_policy=request_policy,
                ),
            )

        for profile_name, description, auto_approve, members in PROFILES:
            profile = AccessProfile(name=profile_name, description=description, auto_approve_requests=auto_approve)
            session.add(profile)
            await session.flush()
            session.add_all(
                AccessProfileApp(profile_id=profile.id, app_id=created[app].id, role=role) for app, role in members
            )

        await seed_google_workspace(session)  # only with SEED_GOOGLE_* in .env
        await seed_demo_directory(session)  # only without it


def _user(email: str, name: str, role: UserRole) -> User:
    return User(
        email=email,
        name=name,
        role=role,
        password_hash=passwords.hash_password(settings.dev_prefill_password),
    )
