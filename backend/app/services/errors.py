"""Domain errors raised by services. ``app.api.errors`` maps them to HTTP."""


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """The entity does not exist (HTTP 404)."""


class ConflictError(DomainError):
    """The change clashes with existing data or state (HTTP 409)."""


class InvalidInputError(DomainError):
    """The request is well-formed but breaks a domain rule (HTTP 400)."""


class UnavailableError(DomainError):
    """A service the request needs is down, e.g. the browser container (HTTP 503)."""


class AuthenticationError(DomainError):
    """Wrong credentials, an expired sign-in step or no session (HTTP 401)."""


class PermissionDeniedError(DomainError):
    """Signed in, but the role does not allow it (HTTP 403)."""


class RateLimitedError(DomainError):
    """Too many attempts in a short time (HTTP 429)."""
