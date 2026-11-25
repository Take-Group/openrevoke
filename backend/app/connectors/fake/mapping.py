"""Deterministic fake data. Names are invented; addresses use the configured domain."""

from app.connectors.base import RemoteAccount, RemotePerson

FIRST_NAMES = ("Ada", "Borys", "Celina", "Dawid", "Edyta", "Filip", "Gaja", "Henryk")
LAST_NAMES = ("Testowa", "Przykładowy", "Fikcyjna", "Wzorcowy")


def _name(index: int) -> tuple[str, str]:
    return FIRST_NAMES[index % len(FIRST_NAMES)], LAST_NAMES[index % len(LAST_NAMES)]


def fake_accounts(domain: str, count: int) -> list[RemoteAccount]:
    """``count`` user accounts plus one service account without an e-mail.

    The last user is suspended, the one before it invited, so every status shows up.
    """
    accounts = []
    for index in range(count):
        first, last = _name(index)
        status = "suspended" if index == count - 1 and count > 2 else "invited" if index == count - 2 else "active"
        accounts.append(
            RemoteAccount(
                external_id=f"fake-{index + 1}",
                email=f"user{index + 1}@{domain}",
                display_name=f"{first} {last}",
                username=f"user{index + 1}",
                role="admin" if index == 0 else "member",
                status=status,
                raw={"index": index + 1},
            )
        )
    accounts.append(
        RemoteAccount(
            external_id="fake-bot",
            email=None,
            display_name="Deploy bot",
            username="deploy-bot",
            role="member",
            status="active",
            raw={"bot": True},
        )
    )
    return accounts


def fake_people(domain: str, count: int) -> list[RemotePerson]:
    people = []
    for index in range(count):
        first, last = _name(index)
        people.append(
            RemotePerson(
                external_id=f"fake-person-{index + 1}",
                email=f"user{index + 1}@{domain}",
                aliases=[f"alias{index + 1}@{domain}"],
                first_name=first,
                last_name=last,
                employee_code=f"FAKE-{index + 1:03d}",
                active=index != count - 1,
            )
        )
    return people


def created_account(email: str, first_name: str | None, last_name: str | None, role: str | None) -> RemoteAccount:
    """An account the fake app creates: invited until the person logs in, like most apps."""
    name = " ".join(part for part in (first_name, last_name) if part) or None
    return RemoteAccount(
        external_id=f"fake-new-{email}",
        email=email,
        display_name=name,
        username=email.split("@")[0],
        role=role or "member",
        status="invited",
        raw={"created": True},
    )
