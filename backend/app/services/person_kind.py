"""Person or service account: rules for people that come from a people source.

Directories like Google Workspace have no flag for shared mailboxes and technical accounts, so
the rules read the address and the name. Each match returns its reason, shown in the panel.
An admin's choice (``kind_source = manual``) always wins: syncs never change it.

Rules, first match wins:

1. a generic address: the local part, or its first part before ``.``/``-``/``_``/``+``, is a
   role word (``kontakt``, ``sales``, ``noreply`` ...),
2. a digit in the local part together with a name that does not look like a person's (a digit
   in the name, or a name all in lower case): ``index.gsc.10`` named "index gsc10",
3. a name with a word for technical accounts ("Konto Techniczne", "Service", "Bot"),
4. never signed in, and created more than ``NEVER_SIGNED_IN_DAYS`` ago.

Not covered: a technical account with a person-like address and name (``kubernetes-dex@`` named
"Kubernetes Dex" that someone signed in with). The admin marks those by hand.
"""

import re
from datetime import UTC, datetime, timedelta

from app.models.enums import PersonKind

NEVER_SIGNED_IN_DAYS = 30

ROLE_WORDS = frozenset(
    {
        # English
        "abuse", "accounting", "accounts", "admin", "administrator", "alerts", "api", "apps", "backup",
        "billing", "bot", "careers", "contact", "contracts", "devops", "dev", "events", "finance", "hello",
        "help", "helpdesk", "hi", "hr", "info", "invoices", "it", "jobs", "legal", "mail", "mailer",
        "marketing", "marketplace", "media", "monitoring", "newsletter", "no-reply", "noreply", "notifications",
        "office", "ops", "orders", "partners", "payments", "postmaster", "press", "privacy", "projects",
        "recruitment", "reports", "root", "sales", "security", "service", "shop", "support", "system", "team",
        "tech", "test", "webmaster",
        # Polish
        "biuro", "faktury", "kadry", "kontakt", "ksiegowosc", "pomoc", "praca", "rekrutacja",
        "sekretariat", "sklep", "sprzedaz", "zamowienia",
        # German, French, Spanish basics
        "anfrage", "bureau", "buero", "contacto", "rechnung", "ventas", "verkauf",
    }
)  # fmt: skip
NAME_WORDS = re.compile(
    r"\b(konto techniczne|technical|service|serwis|bot|system|shared|wspólne|wspolne|no-?reply|mailbox|skrzynka)\b",
    re.IGNORECASE,
)
SEPARATORS = re.compile(r"[._+-]")


def classify(
    email: str,
    first_name: str | None,
    last_name: str | None,
    *,
    last_sign_in_at: datetime | None = None,
    created_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[PersonKind, str | None]:
    """``(kind, reason)``; the reason is set for service accounts only."""
    local = email.split("@", 1)[0].lower()
    name = " ".join(part.strip() for part in (first_name, last_name) if part and part.strip())
    first_part = SEPARATORS.split(local, maxsplit=1)[0]
    if local in ROLE_WORDS or first_part in ROLE_WORDS:
        return PersonKind.SERVICE, f"generic address {local}@"
    if re.search(r"\d", local) and name and (re.search(r"\d", name) or name == name.lower()):
        return PersonKind.SERVICE, f"numbered address {local}@ with the name {name!r}"
    if name and (match := NAME_WORDS.search(name)):
        return PersonKind.SERVICE, f"name {name!r} contains {match.group(0)!r}"
    if last_sign_in_at is None and created_at is not None:
        age = (now or datetime.now(UTC)) - created_at
        if age > timedelta(days=NEVER_SIGNED_IN_DAYS):
            return PersonKind.SERVICE, f"never signed in, created {created_at.date().isoformat()}"
    return PersonKind.HUMAN, None
