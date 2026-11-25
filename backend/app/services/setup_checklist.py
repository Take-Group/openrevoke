"""First steps after the first-run setup: two questions on /welcome and a checklist on the dashboard.

The answers live on the organization row. The checklist is not stored: every item is
worked out from the data (a Google Workspace connection, people, priced apps, the Slack
agent), so it stays right when the admin does a step from another page.
Skill: skills/backend/setup-checklist.md.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from app.models import App, Connection, Organization, Person
from app.models.enums import ChatPlatform, PeopleImport, PricingModel, SlackAgentStatus
from app.models.slack_agent import SlackAgent
from app.schemas.setup_checklist import ChecklistItem, OnboardingChoices, OnboardingOut
from app.services import audit
from app.services.errors import NotFoundError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

GOOGLE_CONNECTOR = "google_workspace"


async def _organization(session: AsyncSession) -> Organization:
    organization = await session.get(Organization, 1)
    if organization is None:
        raise NotFoundError("The organization is not set up yet.")
    return organization


async def _has(session: AsyncSession, query) -> bool:
    return bool(await session.scalar(select(exists(query))))


async def _people_item(session: AsyncSession, choice: PeopleImport | None) -> ChecklistItem:
    if choice == PeopleImport.GOOGLE_WORKSPACE:
        return ChecklistItem(
            key="people",
            title="Connect Google Workspace",
            description="Imports your people and scans which apps they sign in to with the work account.",
            href="/discovery",
            action="Connect Google",
            done=await _has(session, select(Connection.id).where(Connection.connector_key == GOOGLE_CONNECTOR)),
            supported=True,
        )
    has_people = await _has(session, select(Person.id))
    if choice == PeopleImport.MICROSOFT_365:
        return ChecklistItem(
            key="people",
            title="Import your people from Microsoft 365",
            description=(
                "Open Revoke cannot sync Microsoft 365 yet. Export active users in the Microsoft 365 admin "
                "center (Users, Active users, Export users) and import the CSV file."
            ),
            href="/people",
            action="Import CSV",
            done=has_people,
            supported=False,
        )
    if choice == PeopleImport.CSV:
        return ChecklistItem(
            key="people",
            title="Import your people from a CSV file",
            description="Columns: email, first_name, last_name, employee_code, aliases. Only email is required.",
            href="/people",
            action="Import CSV",
            done=has_people,
            supported=True,
        )
    return ChecklistItem(
        key="people",
        title="Add your people",
        description="Add the people of the company one by one. You can import a CSV file later.",
        href="/people",
        action="Add people",
        done=has_people,
        supported=True,
    )


async def _chat_item(session: AsyncSession, choice: ChatPlatform | None) -> ChecklistItem | None:
    if choice == ChatPlatform.SLACK:
        connected = await _has(
            session,
            select(SlackAgent.id).where(
                SlackAgent.status.in_([SlackAgentStatus.CONNECTED, SlackAgentStatus.CONNECTING])
            ),
        )
        return ChecklistItem(
            key="chat",
            title="Add the Open Revoke bot to Slack",
            description="People ask for access in a direct message; admins approve requests in Slack.",
            href="/settings/slack",
            action="Set up Slack",
            done=connected,
            supported=True,
        )
    if choice == ChatPlatform.TEAMS:
        return ChecklistItem(
            key="chat",
            title="Microsoft Teams",
            description="Open Revoke has no Teams bot yet. Access requests go through the panel.",
            href=None,
            action=None,
            done=False,
            supported=False,
        )
    return None


async def _apps_item(session: AsyncSession, choice: PeopleImport | None) -> ChecklistItem:
    priced = select(App.id).where(
        App.pricing_model != PricingModel.FREE, App.price_amount.is_not(None), App.price_amount > 0
    )
    google = choice == PeopleImport.GOOGLE_WORKSPACE
    return ChecklistItem(
        key="apps",
        title="Add the apps you pay for",
        description=(
            "Track the apps the scan found and enter what each costs, per seat or per plan."
            if google
            else "Add each paid app with its price per seat or per plan, then connect it to read its accounts."
        ),
        href="/discovery" if google else "/apps",
        action="Review apps" if google else "Add apps",
        done=await _has(session, priced),
        supported=True,
    )


async def overview(session: AsyncSession) -> OnboardingOut:
    organization = await _organization(session)
    items = [await _people_item(session, organization.people_import)]
    chat = await _chat_item(session, organization.chat_platform)
    if chat is not None:
        items.append(chat)
    items.append(await _apps_item(session, organization.people_import))
    return OnboardingOut(
        people_import=organization.people_import,
        chat_platform=organization.chat_platform,
        password_manager=organization.password_manager,
        answered=(
            organization.people_import is not None
            and organization.chat_platform is not None
            and organization.password_manager is not None
        ),
        dismissed_at=organization.onboarding_dismissed_at,
        items=items,
        completed=sum(item.done for item in items),
    )


async def save_choices(session: AsyncSession, data: OnboardingChoices) -> OnboardingOut:
    organization = await _organization(session)
    changes = data.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(organization, field, value)
    if changes:
        await audit.record(session, "organization.onboarding_answered", "organization", None, changes)
    await session.flush()
    return await overview(session)


async def dismiss(session: AsyncSession) -> OnboardingOut:
    organization = await _organization(session)
    organization.onboarding_dismissed_at = datetime.now(UTC)
    await session.flush()
    return await overview(session)
