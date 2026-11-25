"""Deterministic app discovery data for the fake connector. Fictional apps and people only.

Directory: the fake people (``user<N>@<domain>``, the last one suspended).
Sign-ins: everybody to "Fake Notes", odd users to "Fake Design" (no live
token), user1 to "Fake Video", and a deleted ``former@<domain>`` to
"Fake Notes" and "Fake Chat".
"""

from datetime import datetime, timedelta

from app.connectors.discovery import AppGrant, DirectoryUser, DiscoveryResult
from app.connectors.fake.mapping import fake_people

DELETED_LOCAL_PART = "former"


def fake_discovery(domain: str, count: int, since: datetime, until: datetime) -> DiscoveryResult:
    people = fake_people(domain, count)
    directory = [
        DirectoryUser(email=person.email, status="active" if person.active else "suspended", aliases=person.aliases)
        for person in people
    ]
    seen = until - timedelta(days=1)
    grants: list[AppGrant] = []

    def grant(client: str, name: str, email: str, *, token: bool = True, days_ago: int = 1) -> None:
        at = max(since, until - timedelta(days=days_ago))
        grants.append(
            AppGrant(
                client_id=f"fake-client-{client}",
                app_name=name,
                email=email,
                scopes=["openid", "email", "profile"],
                first_seen_at=at,
                last_seen_at=max(at, seen) if days_ago <= 1 else at,
                token_active=token,
            )
        )

    for index, person in enumerate(people):
        grant("notes", "Fake Notes", person.email, days_ago=index + 1)
        if index % 2 == 0:
            grant("design", "Fake Design", person.email, token=False, days_ago=10)
    if people:
        grant("video", "Fake Video", people[0].email)
    former = f"{DELETED_LOCAL_PART}@{domain}"
    grant("notes", "Fake Notes", former, token=False, days_ago=40)
    grant("chat", "Fake Chat", former, token=False, days_ago=45)
    return DiscoveryResult(
        grants=grants,
        directory=directory,
        deleted_users={former: until - timedelta(days=30)},
        events_from=since,
        events_until=until,
        token_inventory=True,
        notes=["Fake data from the development connector."],
    )
