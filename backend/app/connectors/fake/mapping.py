"""Deterministic fake data. Names are invented; addresses use the configured domain.

People form a two-level org chart: the first person runs the company, the next ones head a
department each and report to them, everyone else reports to the head of their department.
Two addresses match the development panel users: ``manager@`` heads Engineering and ``member@``
works there, so the manager step of access requests can be tried with their sign-ins.
"""

from app.connectors.base import RemoteAccount, RemotePerson

FIRST_NAMES = ("Ada", "Borys", "Celina", "Dawid", "Edyta", "Filip", "Gaja", "Henryk")
LAST_NAMES = ("Testowa", "Przykładowy", "Fikcyjna", "Wzorcowy")

# Index in the directory -> local part of the address, for people the panel users stand for.
NAMED_LOCAL_PARTS = {1: "manager", 5: "member"}

# (department, title of its head, title of the others)
DEPARTMENTS = (
    ("Engineering", "Head of Engineering", "Software Engineer"),
    ("Sales", "Head of Sales", "Account Executive"),
    ("Design", "Design Lead", "Product Designer"),
    ("Operations", "Head of Operations", "Operations Specialist"),
)
# Department of each person after the heads, in turn: Engineering is the largest team.
TEAM_ROTATION = (0, 1, 0, 2, 0, 3)


def _name(index: int) -> tuple[str, str]:
    # The last name shifts with every round of first names, so the first 32 names are all different.
    last = (index + index // len(FIRST_NAMES)) % len(LAST_NAMES)
    return FIRST_NAMES[index % len(FIRST_NAMES)], LAST_NAMES[last]


def _local_part(index: int) -> str:
    return NAMED_LOCAL_PARTS.get(index, f"user{index + 1}")


def _email(index: int, domain: str) -> str:
    return f"{_local_part(index)}@{domain}"


def _position(index: int) -> tuple[str, str, int | None]:
    """Department, job title and the manager's index of the person at ``index``."""
    if index == 0:
        return "Management", "Chief Executive Officer", None
    if index <= len(DEPARTMENTS):
        department, head_title, _ = DEPARTMENTS[index - 1]
        return department, head_title, 0
    team = TEAM_ROTATION[(index - len(DEPARTMENTS) - 1) % len(TEAM_ROTATION)]
    department, _, title = DEPARTMENTS[team]
    return department, title, team + 1


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
                email=_email(index, domain),
                display_name=f"{first} {last}",
                username=_local_part(index),
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
        department, title, manager = _position(index)
        people.append(
            RemotePerson(
                external_id=f"fake-person-{index + 1}",
                email=_email(index, domain),
                aliases=[f"alias{index + 1}@{domain}"],
                first_name=first,
                last_name=last,
                employee_code=f"FAKE-{index + 1:03d}",
                active=index != count - 1,
                manager_email=_email(manager, domain) if manager is not None and manager < count else None,
                department=department,
                job_title=title,
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
