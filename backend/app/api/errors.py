"""Map service errors to HTTP responses in the FastAPI format ``{"detail": "..."}``."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorResponse
from app.services.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    UnavailableError,
)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidInputError: status.HTTP_400_BAD_REQUEST,
    UnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    RateLimitedError: status.HTTP_429_TOO_MANY_REQUESTS,
}

ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse, "description": "The request breaks a domain rule"},
    401: {"model": ErrorResponse, "description": "Not signed in, or the session expired"},
    403: {"model": ErrorResponse, "description": "The role does not allow it, or the client header is missing"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict with existing data or state"},
}

UNAVAILABLE_RESPONSE: dict[int | str, dict] = {
    503: {"model": ErrorResponse, "description": "A service the request needs is down (e.g. the browser)"}
}

RATE_LIMITED_RESPONSE: dict[int | str, dict] = {
    429: {"model": ErrorResponse, "description": "Too many attempts; try again later"}
}

NOT_IMPLEMENTED = "Not implemented yet"
NOT_IMPLEMENTED_RESPONSE: dict[int | str, dict] = {
    501: {"model": ErrorResponse, "description": "Comes in a later stage of the MVP"}
}


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    code = next((code for cls, code in STATUS_BY_ERROR.items() if isinstance(exc, cls)), 400)
    return JSONResponse(status_code=code, content={"detail": exc.message})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
