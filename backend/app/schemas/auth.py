"""Sign-in, first-run setup, registration by invite or self sign-up, and password reset."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.models.enums import PasswordManager, UserRole, UserStatus
from app.schemas.common import ApiModel
from app.services.currencies import is_known
from app.services.timezones import is_known_timezone


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    local, _, domain = value.partition("@")
    if not local or "." not in domain or "@" in domain or " " in value:
        raise ValueError("Enter a valid e-mail address")
    return value


def _known_currency(value: str) -> str:
    value = value.strip().upper()
    if not is_known(value):
        raise ValueError("Unknown currency; use an ISO 4217 code from GET /api/currencies")
    return value


OrganizationCurrency = Annotated[
    str,
    Field(min_length=3, max_length=3, description="ISO 4217 code, one of GET /api/currencies", examples=["EUR"]),
    AfterValidator(_known_currency),
]


def _known_timezone(value: str) -> str:
    value = value.strip()
    if not is_known_timezone(value):
        raise ValueError("Unknown time zone; use an IANA name such as Europe/Warsaw")
    return value


TimeZoneName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        description="IANA time zone; the panel shows times in it",
        examples=["Europe/Warsaw"],
    ),
    AfterValidator(_known_timezone),
]

Email = Annotated[str, Field(min_length=3, max_length=320), AfterValidator(_normalize_email)]
Password = Annotated[str, Field(min_length=1, max_length=128, description="At least 12 characters")]
DisplayName = Annotated[str, Field(min_length=1, max_length=200)]
TotpCode = Annotated[str, Field(min_length=6, max_length=8, description="6 digits from the authenticator app")]
Token = Annotated[str, Field(min_length=20, max_length=200)]


def _clean_domains(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        domain = value.strip().lower().removeprefix("@")
        if not domain:
            continue
        if "." not in domain or " " in domain or "@" in domain or len(domain) > 253:
            raise ValueError(f"Not a domain: {value}. Write it like example.com")
        if domain not in cleaned:
            cleaned.append(domain)
    return cleaned


EmailDomains = Annotated[
    list[str],
    Field(max_length=50, description="E-mail domains without @, e.g. example.com", examples=[["example.com"]]),
    AfterValidator(_clean_domains),
]


class OrganizationOut(ApiModel):
    name: str
    currency: str
    timezone: str


class OrganizationSettingsOut(OrganizationOut):
    """The organization with its sign-up rules; only admins read these."""

    password_manager: PasswordManager | None = Field(
        description="Force-installed in the shared browser; null until the admin picks on /welcome"
    )
    registration_enabled: bool = Field(description="Anyone with the panel's address can sign up on /signup")
    registration_auto_approve: bool = Field(
        description="A confirmed e-mail in registration_domains gets in without an admin; others still wait"
    )
    registration_domains: list[str]


class OrganizationUpdate(BaseModel):
    name: DisplayName | None = None
    currency: OrganizationCurrency | None = None
    timezone: TimeZoneName | None = None
    password_manager: PasswordManager | None = None
    registration_enabled: bool | None = None
    registration_auto_approve: bool | None = None
    registration_domains: EmailDomains | None = None


class UserOut(ApiModel):
    user_id: uuid.UUID = Field(validation_alias="id")
    email: str
    name: str
    role: UserRole
    status: UserStatus = Field(description="pending accounts (self sign-up) cannot sign in until an admin approves")
    totp_enabled: bool
    created_at: datetime
    last_login_at: datetime | None
    approved_at: datetime | None = Field(description="Self sign-up: when the account was let in")


class DevPrefill(BaseModel):
    """Development only (OPEN_REVOKE_DEV_PREFILL): values the sign-in forms fill with one click."""

    organization_name: str
    currency: str
    name: str = Field(description="Name of the first admin")
    email: str = Field(description="E-mail of the first admin, also filled on the sign-in page")
    password: str = Field(description="Password of every form: setup, sign-in, registration, reset")
    invitee_name: str = Field(description="Name filled on the registration and sign-up pages")
    signup_email: str = Field(description="E-mail for /signup; the panel adds +<random> so each fill is a new account")


class AuthState(BaseModel):
    setup_required: bool = Field(description="No user exists yet: the panel shows the first-run setup")
    user: UserOut | None = Field(description="The signed-in user, null without a valid session")
    organization: OrganizationOut | None
    registration_enabled: bool = Field(description="The sign-in page offers self sign-up (/signup)")
    public_url: str = Field(
        description="PUBLIC_URL: the address the panel expects to be opened at. The panel warns when it differs"
    )
    dev_prefill: DevPrefill | None = Field(
        default=None, description="Development only: one-click form fill values; null without OPEN_REVOKE_DEV_PREFILL"
    )


class SetupRequest(BaseModel):
    """Both setup screens at once: the organization (step 1) and the first admin (step 2)."""

    organization_name: DisplayName
    currency: OrganizationCurrency
    timezone: TimeZoneName
    name: DisplayName
    email: Email
    password: Password
    token: Token = Field(description="Token of the setup link printed on the server (`open-revoke setup-link`)")


class SetupTokenCheck(BaseModel):
    token: Token


class LoginRequest(BaseModel):
    email: Email
    password: Password


class RegisterRequest(BaseModel):
    token: Token
    name: DisplayName
    password: Password


class SignupRequest(BaseModel):
    name: DisplayName
    email: Email
    password: Password


class SignupResult(BaseModel):
    status: UserStatus = Field(description="active: sign in now (approved domain); pending: an admin approves first")


class AuthStepKind(StrEnum):
    DONE = "done"  # signed in: the session cookie is set (no 2FA on the account)
    TOTP = "totp"  # enter a code from the authenticator app
    TOTP_SETUP = "totp_setup"  # first-run setup only: scan the QR code and enter the first code, or skip


class TotpEnrollment(BaseModel):
    secret: str = Field(description="Base32 secret for manual entry")
    otpauth_uri: str
    qr_svg: str = Field(description="data: URI of an SVG QR code")


class AuthStep(BaseModel):
    """The password is right. ``done``: signed in now; otherwise the session comes after the TOTP step."""

    step: AuthStepKind
    ticket: str | None = Field(
        default=None, description="totp and totp_setup: pass it to POST /api/auth/totp; valid 10 minutes, 5 codes"
    )
    totp_setup: TotpEnrollment | None = None
    user: UserOut | None = Field(default=None, description="done: the signed-in user")


class TotpSetupOut(BaseModel):
    """Settings: a new secret to scan. Saved on the account only after POST /api/auth/2fa/enable."""

    ticket: str = Field(description="Pass it to POST /api/auth/2fa/enable; valid 10 minutes, 5 codes")
    totp_setup: TotpEnrollment


class TotpEnableRequest(BaseModel):
    ticket: Token
    code: TotpCode


class TotpDisableRequest(BaseModel):
    code: TotpCode


class TotpRequest(BaseModel):
    ticket: Token
    code: TotpCode


class TotpSkipRequest(BaseModel):
    ticket: Token


class InviteInfo(BaseModel):
    email: str
    organization_name: str | None
    expires_at: datetime


class ResetPasswordRequest(BaseModel):
    token: Token
    password: Password


class ChangePasswordRequest(BaseModel):
    current_password: Password
    new_password: Password
