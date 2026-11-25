"""Development data: the organization, panel users and sample apps.

People and their accounts come from a people source: a real Google Workspace with
SEED_GOOGLE_* in `.env` (``seed_google``), otherwise a fictional directory at example.com
(``seed_demo``). The panel sign-in uses
the DEV_PREFILL_* settings (default admin@example.com / open-revoke-dev-password); the admin has
no 2FA yet, so the first sign-in offers to set it up or skip it.

Add what a new feature needs to see in the panel here, so that
``python -m app.db reset`` brings it back after every schema change.
"""

from decimal import Decimal

from app.config import settings
from app.database import async_session
from app.db.seed_demo import seed_demo_directory
from app.db.seed_google import seed_google_workspace
from app.models import Organization, User
from app.models.enums import (
    BillingPeriod,
    Integration,
    PasswordManager,
    PricingModel,
    SelfServicePolicy,
    UserRole,
)
from app.schemas.apps import AppCreate, PriceIn
from app.services import apps
from app.services.auth import passwords
from app.services.auth.actor import current_actor

A = SelfServicePolicy.AUTOMATIC
R = SelfServicePolicy.APPROVAL
# (name, pricing model, price per seat or plan, currency, Slack agent requests)
APPS = [
    ("Slack", PricingModel.PER_SEAT, "8.75", "USD", R),
    ("Notion", PricingModel.PER_SEAT, "10", "USD", R),
    ("Figma", PricingModel.PER_SEAT, "15", "EUR", R),
    ("1Password", PricingModel.FLAT, "399", "PLN", SelfServicePolicy.OFF),
    ("Miro", PricingModel.FREE, None, None, A),
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
        session.add_all(
            [
                _user(settings.dev_prefill_email, settings.dev_prefill_name, UserRole.ADMIN),
                _user("member@example.com", "Dev Member", UserRole.USER),
            ]
        )
        await session.flush()

        for name, model, amount, currency, self_service in APPS:
            price = None
            if amount is not None:
                price = PriceIn(amount=Decimal(amount), currency=currency, billing_period=BillingPeriod.MONTHLY)
            await apps.create_app(
                session,
                AppCreate(
                    name=name,
                    integration=Integration.MANUAL,
                    pricing_model=model,
                    price=price,
                    self_service=self_service,
                ),
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
