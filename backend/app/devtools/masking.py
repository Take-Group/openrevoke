"""Masking of secrets in recorded traffic (``app.devtools.capture``).

Header values of auth headers are replaced whole. Bodies keep their shape;
values that look like tokens (Slack ``xox?-``, JWTs, ``Bearer ...``, long
``token``/``secret``/``password`` fields) are replaced. This lowers the risk,
it does not remove it: recordings still hold real people's names and e-mails
and stay out of git (``captures/`` is in ``.gitignore``).
"""

import re

MASK = "<masked>"
SENSITIVE_HEADER = re.compile(r"authorization|cookie|csrf|xsrf|token|secret|session|api-key|apikey|^x-slack-", re.I)
BODY_PATTERNS = (
    re.compile(r"xox[a-z]-[A-Za-z0-9-]+"),  # Slack tokens
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),  # JWT
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{10,}"),
    # "token": "...", token=..., access_token=... in JSON or forms
    re.compile(
        r"""(?ix)
        (["']?[a-z_]*(?:token|secret|password|passwd|session|csrf|xsrf)[a-z_]*["']?\s*[:=]\s*["']?)
        ([^"'&\s,}]{6,})
        """
    ),
)


def mask_headers(headers: dict[str, str]) -> dict[str, str]:
    return {name: MASK if SENSITIVE_HEADER.search(name) else value for name, value in headers.items()}


def mask_body(text: str | None) -> str | None:
    if text is None:
        return None
    for pattern in BODY_PATTERNS:
        # Patterns with a group keep the key part (group 1) and mask what follows.
        text = pattern.sub(lambda match: match.group(1) + MASK, text) if pattern.groups else pattern.sub(MASK, text)
    return text


def truncate(text: str | None, limit: int) -> tuple[str | None, bool]:
    if text is None or len(text) <= limit:
        return text, False
    return text[:limit], True
