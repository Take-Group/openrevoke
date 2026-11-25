"""OAuth scopes of the Google Workspace connector, shared by the service account and the OAuth sign-in."""

SCOPE_READ = "https://www.googleapis.com/auth/admin.directory.user.readonly"
SCOPE_WRITE = "https://www.googleapis.com/auth/admin.directory.user"
SCOPE_AUDIT = "https://www.googleapis.com/auth/admin.reports.audit.readonly"
SCOPE_TOKENS = "https://www.googleapis.com/auth/admin.directory.user.security"

# A granted scope that covers another one: full directory access includes the read-only scope.
COVERED_BY = {SCOPE_READ: SCOPE_WRITE}


def is_granted(granted: frozenset[str], scope: str) -> bool:
    return scope in granted or COVERED_BY.get(scope) in granted
