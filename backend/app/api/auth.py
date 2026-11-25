"""Sign-in endpoints. Public (no session needed), except password change and sign-out."""

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.auth_deps import CurrentSessionDep, OptionalSessionDep, require_client_header
from app.api.deps import SessionDep
from app.api.errors import ERROR_RESPONSES, RATE_LIMITED_RESPONSE
from app.config import settings
from app.schemas.auth import (
    AuthState,
    AuthStep,
    AuthStepKind,
    ChangePasswordRequest,
    DevPrefill,
    InviteInfo,
    LoginRequest,
    OrganizationOut,
    RegisterRequest,
    ResetPasswordRequest,
    SetupRequest,
    SetupTokenCheck,
    SignupRequest,
    SignupResult,
    TotpDisableRequest,
    TotpEnableRequest,
    TotpEnrollment,
    TotpRequest,
    TotpSetupOut,
    TotpSkipRequest,
    UserOut,
)
from app.services.auth import passwords_flow, sessions, setup_link, sign_in, signup, totp, two_factor

router = APIRouter(
    prefix="/api/auth", tags=["auth"], responses=ERROR_RESPONSES, dependencies=[Depends(require_client_header)]
)


def _answer(result: sign_in.SignInResult, response: Response) -> AuthStep:
    """A session now (cookie set, step ``done``) or the TOTP step."""
    if isinstance(result, sign_in.SignedIn):
        _set_cookie(response, result.session_token)
        return AuthStep(step=AuthStepKind.DONE, user=UserOut.model_validate(result.user))
    return _step(result)


def _enrollment(enrollment: totp.Enrollment) -> TotpEnrollment:
    return TotpEnrollment(secret=enrollment.secret, otpauth_uri=enrollment.otpauth_uri, qr_svg=enrollment.qr_svg)


def _step(pending: sign_in.PendingStep) -> AuthStep:
    if pending.enrollment is None:
        return AuthStep(step=AuthStepKind.TOTP, ticket=pending.ticket)
    return AuthStep(step=AuthStepKind.TOTP_SETUP, ticket=pending.ticket, totp_setup=_enrollment(pending.enrollment))


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        sessions.COOKIE_NAME,
        token,
        max_age=int(sessions.lifetime().total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.get("/state", response_model=AuthState)
async def get_auth_state(session: SessionDep, current: OptionalSessionDep) -> AuthState:
    organization = await sign_in.get_organization(session)
    return AuthState(
        setup_required=await sign_in.setup_required(session),
        user=UserOut.model_validate(current.user) if current else None,
        organization=OrganizationOut.model_validate(organization) if organization else None,
        registration_enabled=bool(organization and organization.registration_enabled),
        public_url=settings.public_url,
        dev_prefill=_dev_prefill(),
    )


def _dev_prefill() -> DevPrefill | None:
    if not settings.dev_prefill:
        return None
    return DevPrefill(
        organization_name=settings.dev_prefill_organization,
        currency=settings.dev_prefill_currency,
        name=settings.dev_prefill_name,
        email=settings.dev_prefill_email,
        password=settings.dev_prefill_password,
        invitee_name=settings.dev_prefill_invitee_name,
        signup_email=settings.dev_prefill_signup_email,
    )


@router.post("/setup/check", status_code=status.HTTP_204_NO_CONTENT)
async def check_setup_token(data: SetupTokenCheck) -> None:
    """204 when the token of a setup link is valid, 403 otherwise. The setup page checks it before the form."""
    await setup_link.require_valid(data.token)


@router.post("/setup", response_model=AuthStep, status_code=status.HTTP_201_CREATED)
async def setup(data: SetupRequest, session: SessionDep) -> AuthStep:
    """First run only: create the organization and the first user (admin). Next step: optional TOTP setup."""
    return _step(await sign_in.setup(session, **data.model_dump()))


@router.post("/login", response_model=AuthStep, responses=RATE_LIMITED_RESPONSE)
async def login(data: LoginRequest, request: Request, response: Response, session: SessionDep) -> AuthStep:
    """``done`` with the session cookie, or ``totp`` when the account has 2FA on."""
    result = await sign_in.login(
        session, email=data.email, password=data.password, user_agent=request.headers.get("user-agent")
    )
    return _answer(result, response)


@router.post("/totp", response_model=UserOut)
async def verify_totp(data: TotpRequest, request: Request, response: Response, session: SessionDep) -> UserOut:
    """Second step of a sign-in with 2FA (or of the first-run setup): a TOTP code for the ticket. Sets the cookie."""
    signed_in = await sign_in.complete(
        session, ticket=data.ticket, code=data.code, user_agent=request.headers.get("user-agent")
    )
    _set_cookie(response, signed_in.session_token)
    return UserOut.model_validate(signed_in.user)


@router.post("/totp/skip", response_model=UserOut)
async def skip_totp(data: TotpSkipRequest, request: Request, response: Response, session: SessionDep) -> UserOut:
    """First-run setup only: continue without 2FA from the ``totp_setup`` step. Settings can turn it on later.

    401 for a ticket of an account that has 2FA on.
    """
    signed_in = await sign_in.skip_enrollment(session, ticket=data.ticket, user_agent=request.headers.get("user-agent"))
    _set_cookie(response, signed_in.session_token)
    return UserOut.model_validate(signed_in.user)


@router.get("/invites/{token}", response_model=InviteInfo)
async def get_invite(token: str, session: SessionDep) -> InviteInfo:
    email, organization, expires_at = await sign_in.invite_info(session, token)
    return InviteInfo(email=email, organization_name=organization.name if organization else None, expires_at=expires_at)


@router.post("/register", response_model=AuthStep, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, request: Request, response: Response, session: SessionDep) -> AuthStep:
    """Create an account from an invite link and sign in (step ``done``)."""
    result = await sign_in.register(
        session,
        token=data.token,
        name=data.name,
        password=data.password,
        user_agent=request.headers.get("user-agent"),
    )
    return _answer(result, response)


@router.post(
    "/signup", response_model=SignupResult, status_code=status.HTTP_201_CREATED, responses=RATE_LIMITED_RESPONSE
)
async def sign_up(data: SignupRequest, session: SessionDep) -> SignupResult:
    """Self sign-up (role user): active at once for an auto-approved domain, otherwise pending for an admin.

    403 when the organization turned sign-up off, 409 when the e-mail has an account.
    """
    user = await signup.sign_up(session, name=data.name, email=data.email, password=data.password)
    return SignupResult(status=user.status)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: ResetPasswordRequest, session: SessionDep) -> None:
    """Set a new password with a reset link from an admin or the CLI. Signs out every session."""
    await passwords_flow.reset(session, token=data.token, password=data.password)


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: ChangePasswordRequest, current: CurrentSessionDep, session: SessionDep) -> None:
    """Signed in: change the password. Other sessions of the user are signed out."""
    await passwords_flow.change(
        session,
        current.user,
        current_password=data.current_password,
        new_password=data.new_password,
        session_id=current.id,
    )


@router.post("/2fa/setup", response_model=TotpSetupOut)
async def start_two_factor(current: CurrentSessionDep) -> TotpSetupOut:
    """Settings: a new secret and QR code. Nothing changes until POST /2fa/enable with a code."""
    ticket, enrollment = await two_factor.start(current.user)
    return TotpSetupOut(ticket=ticket, totp_setup=_enrollment(enrollment))


@router.post("/2fa/enable", response_model=UserOut)
async def enable_two_factor(data: TotpEnableRequest, current: CurrentSessionDep, session: SessionDep) -> UserOut:
    """Turn 2FA on with the first code from the new secret. Every next sign-in asks for a code."""
    return UserOut.model_validate(await two_factor.enable(session, current.user, ticket=data.ticket, code=data.code))


@router.post("/2fa/disable", response_model=UserOut, responses=RATE_LIMITED_RESPONSE)
async def disable_two_factor(data: TotpDisableRequest, current: CurrentSessionDep, session: SessionDep) -> UserOut:
    """Turn 2FA off; needs a current code. A lost phone: an admin resets 2FA instead."""
    return UserOut.model_validate(await two_factor.disable(session, current.user, code=data.code))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, session: SessionDep, current: OptionalSessionDep) -> None:
    if current is not None:
        await sign_in.logout(session, current.id, current.user)
    response.delete_cookie(sessions.COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure)
