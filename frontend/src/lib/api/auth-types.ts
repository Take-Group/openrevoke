// Sign-in, sign-up, users and the organization (skills/frontend/auth.md), from docs/openapi.json.

import type { PasswordManager } from "@/lib/api/onboarding-types";
import type { DateTimeString, Uuid } from "@/lib/api/types";

/** admin: the whole panel. user: only their own access (My access). */
export type UserRole = "admin" | "user";
/** pending: signed up on /signup, cannot sign in until an admin approves. */
export type UserStatus = "pending" | "active";
/** ISO 4217 code, one of `GET /api/currencies`. */
export type OrganizationCurrency = string;
/** done: signed in (no 2FA on the account); totp: enter a code; totp_setup: first-run setup only, optional. */
export type AuthStepKind = "done" | "totp" | "totp_setup";

export interface OrganizationOut {
  name: string;
  currency: OrganizationCurrency;
  /** IANA time zone; the panel shows dates and times in it. */
  timezone: string;
}

/** The organization with its sign-up rules (GET/PATCH /api/organization, admins only). */
export interface OrganizationSettingsOut extends OrganizationOut {
  /** Force-installed in the shared browser; null until the admin picks on /welcome. */
  password_manager: PasswordManager | null;
  /** Anyone with the panel's address can sign up on /signup. */
  registration_enabled: boolean;
  /** A sign-up with an e-mail in registration_domains gets in without an admin; others still wait. */
  registration_auto_approve: boolean;
  registration_domains: string[];
}

export interface OrganizationUpdate {
  name?: string;
  currency?: OrganizationCurrency;
  timezone?: string;
  password_manager?: PasswordManager | null;
  registration_enabled?: boolean;
  registration_auto_approve?: boolean;
  /** E-mail domains without @, e.g. example.com. */
  registration_domains?: string[];
}

export interface UserOut {
  user_id: Uuid;
  email: string;
  name: string;
  role: UserRole;
  status: UserStatus;
  totp_enabled: boolean;
  created_at: DateTimeString;
  last_login_at: DateTimeString | null;
  /** Self sign-up: when the account was let in. */
  approved_at: DateTimeString | null;
}

export interface AuthState {
  setup_required: boolean;
  user: UserOut | null;
  organization: OrganizationOut | null;
  /** The sign-in page offers self sign-up (/signup). */
  registration_enabled: boolean;
  /** PUBLIC_URL: the address the panel expects to be opened at. */
  public_url: string;
  /** Development only (OPEN_REVOKE_DEV_PREFILL): values for one-click form fill. */
  dev_prefill: DevPrefill | null;
}

export interface DevPrefill {
  /** E-mail for /signup; the panel adds +<random> so each fill is a new account. */
  signup_email: string;
  organization_name: string;
  currency: string;
  name: string;
  email: string;
  password: string;
  invitee_name: string;
}

export interface SetupRequest {
  organization_name: string;
  currency: OrganizationCurrency;
  timezone: string;
  name: string;
  email: string;
  password: string;
  /** Token of the setup link printed on the server (`open-revoke setup-link`). */
  token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  token: string;
  name: string;
  password: string;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
}

export interface SignupResult {
  /** active: sign in now (approved domain); pending: an admin approves first. */
  status: UserStatus;
}

export interface TotpEnrollment {
  secret: string;
  otpauth_uri: string;
  /** data: URI of an SVG QR code. */
  qr_svg: string;
}

export interface AuthStep {
  step: AuthStepKind;
  /** totp and totp_setup: pass it to POST /api/auth/totp. */
  ticket: string | null;
  totp_setup: TotpEnrollment | null;
  /** done: the signed-in user. */
  user: UserOut | null;
}

/** Settings: a new secret to scan; saved only after POST /api/auth/2fa/enable. */
export interface TotpSetupOut {
  ticket: string;
  totp_setup: TotpEnrollment;
}

export interface TotpRequest {
  ticket: string;
  code: string;
}

export interface InviteInfo {
  email: string;
  organization_name: string | null;
  expires_at: DateTimeString;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface InviteCreate {
  email: string;
  role?: UserRole;
}

export interface InviteOut {
  invite_id: Uuid;
  email: string;
  role: UserRole;
  created_at: DateTimeString;
  expires_at: DateTimeString;
}

export interface InviteCreated extends InviteOut {
  link: string;
}

/** POST /api/users/{id}/reset-link: a one-time link the admin passes on; shown only once. */
export interface ResetLinkOut {
  link: string;
  expires_at: DateTimeString;
}

export interface InviteList {
  items: InviteOut[];
}
