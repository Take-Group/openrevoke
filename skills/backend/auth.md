# Skill: panel sign-in (backend)

## What it does

The panel has user accounts with a password and optional 2FA (TOTP, Google
Authenticator and any other TOTP app).

- First run: when the `panel_user` table is empty,
  `POST /api/auth/setup` creates the organization (name, ISO 4217 currency
  from `skills/backend/exchange-rates.md`, IANA time zone from the
  `tzdata` package, `app/services/timezones.py`)
  and the first user with the `admin` role. After that, setup answers 409.
- Setup needs a token from a link printed on the server:
  on every start without users the API creates a new token and prints
  `Open Revoke setup link: <PUBLIC_URL>/setup?token=...` in the log;
  `python -m app.cli setup-link` (`open-revoke setup-link`) gives a new one, and the old one
  stops working. A SHA-256 hash is kept in Redis
  (`app/services/auth/setup_link.py`); without the token `POST /api/auth/setup`
  and `/setup/check` answer 403. The local stack's seeder creates the admin,
  so there is no setup there. Description: `skills/backend/releases.md`.
- The panel sends no e-mails: there is no SMTP and no
  Mailpit. The admin passes on every link (invite, password reset) personally.
- Later sign-up is by invite or self sign-up:
  - Invite: the admin creates a link (`POST /api/invites`, 7 days), the link comes back
    in the response and the panel shows it for copying.
  - Self sign-up (`services/auth/signup.py`): `POST /api/auth/signup`
    (name, e-mail, password) creates a `user` account: `active` at once when the e-mail's
    domain is on the auto-approve list, otherwise `pending`. An e-mail already in use
    gives 409. The admin approves (`POST /api/users/{id}/approve`) or rejects
    (`DELETE /api/users/{id}`) in Settings → Users and tells the person personally.
    Sign-in to a `pending` account ends with 403 and a reason, only after
    a correct password.
  - Rules in `organization`: `registration_enabled` (default yes),
    `registration_auto_approve` (default no), `registration_domains`; without
    auto-approve domains it cannot be turned on (`services/organization.py`).
    Nothing checks that the person owns the e-mail they entered: the panel runs in the company network,
    and the admin knows their people. Settings: Settings → Users → "Sign-up",
    `GET/PATCH /api/organization` (admin only).
- 2FA (TOTP) is optional and free (MIT); hardware keys, passkeys
  and enforcing 2FA across the whole company will go to `ee/`.
  Sign-in and sign-up never offer 2FA:
  - Account without 2FA: `POST /api/auth/login` gives a session at once
    (`step: done`, cookie). Sign-up from an invite does too.
  - Account with 2FA: the password gives a ticket (Redis, 10 min, 5 attempts), the ticket with a TOTP
    code (`POST /api/auth/totp`) gives a session.
  - Only the first run (setup) offers 2FA to the admin
    (`totp_setup`), with "Skip for now" (`POST /api/auth/totp/skip`).
  - Turning it on and off in Settings (`services/auth/two_factor.py`):
    `POST /api/auth/2fa/setup` (secret in a ticket), `/2fa/enable` (first
    code), `/2fa/disable` (current code, limit 5 attempts / 15 min). Lost
    phone: the admin uses "Reset 2FA".
- Password reset with a one-time link (`/reset-password?token=`), in two
  ways (`passwords_flow.py`); the "Forgot password" page describes them:
  - the admin creates a link for any account: Settings → Users → "Password
    reset link" (`POST /api/users/{id}/reset-link`, 24 h, sends nothing,
    older links stop working, event
    `user.password_reset_link_created`),
  - an admin who forgot their password: `python -m app.cli reset-link <email>`
    on the server prints a link (access to the server replaces e-mail).
  A reset does not turn off 2FA and signs out all sessions. Password change after
  sign-in is in Settings.
- Roles: `admin` (the whole panel: invites, approval, roles, 2FA reset,
  deletion, organization) and `user` (only `/api/me`: their own accounts and access
  requests, `services/access/my_access.py`). `domain_router` in `api/router.py`
  requires `require_admin`; for `self_router` (`/api/me`) a session is enough.
  A user is linked to a `Person` by e-mail (primary or alias). A `user` who is
  someone's manager (`person.manager_id`) also sees, under `/api/me/team` and
  `/api/me/approvals`, their reports and the requests waiting for them, and
  decides the manager step; any other request is 403, their own request too
  (`skills/backend/access-requests.md`). No new role: managers are plain users.

## Files

| File | Role |
|---|---|
| `backend/app/models/user.py`, `user_session.py`, `user_token.py`, `organization.py` | tables `panel_user`, `user_session`, `user_token`, `organization` (one row, `id = 1`) |
| `backend/app/services/auth/passwords.py` | Argon2id, password policy (min. 12 characters) |
| `backend/app/services/auth/totp.py` | secret, `otpauth://` URI, QR (segno, SVG), code with replay protection (`totp_last_step`) |
| `backend/app/services/auth/tickets.py` | second-step ticket in Redis |
| `backend/app/services/auth/sessions.py` | sessions: random token in the `open_revoke_session` cookie, only SHA-256 in the database |
| `backend/app/services/auth/tokens.py` | one-time links (invite, reset), SHA-256 in the database |
| `backend/app/services/auth/rate_limit.py` | counters in Redis: 10 sign-ins / 15 min per e-mail, 5 sign-ups / h, 5 attempts to turn off 2FA / 15 min |
| `backend/app/services/auth/sign_in.py` | setup, sign-in, TOTP step, sign-up from an invite |
| `backend/app/services/auth/two_factor.py` | 2FA in settings: `start`, `enable`, `disable` |
| `backend/app/services/auth/signup.py` | self sign-up, confirmation link, auto-approve by domain, `sign_in_blocker` |
| `backend/app/services/organization.py` | reading and changing the organization with sign-up rules |
| `backend/app/services/access/my_access.py`, `my_approvals.py`, `backend/app/api/me.py` | `/api/me/access`, `/api/me/access-requests`, `/api/me/team`, `/api/me/approvals`: own accounts and requests, reports, manager decisions |
| `backend/app/services/auth/passwords_flow.py` | forgotten password, reset, change |
| `backend/app/services/auth/invites.py`, `users.py` | invites, account approval, roles, 2FA reset, deletion |
| `backend/app/services/auth/actor.py` | `current_actor`, `current_user_id`, `current_via` (ContextVars, `set_actor`, `actor_ref`): the signed-in user's e-mail goes to `audit_event.actor`; user and channel go to request decisions and `action.approved_by` |
| `backend/app/api/auth_deps.py` | `get_current_session` (cookie only), `get_current_user` (API token or cookie), `require_admin`, header `X-Open-Revoke-Client` (cookie requests) |
| `backend/app/services/auth/api_tokens.py` | personal API tokens (Bearer) for the REST API and MCP: skill `mcp.md` |
| `backend/app/api/auth.py` | `/api/auth/*`, public |
| `backend/app/api/users.py` | `/api/users`, `/api/invites`, `/api/organization` |
| `backend/app/cli.py` | `list-users`, `reset-2fa`, `reset-link`, `set-password` |

## Flow

1. `GET /api/auth/state`: `setup_required`, `user`, `organization`,
   `registration_enabled`. The frontend decides from it what to show.
2. `POST /api/auth/setup` | `login` | `register` → `AuthStep`
   (`step: done | totp | totp_setup`; `done` sets the cookie and carries
   `user`; `totp` and `totp_setup` carry `ticket`, `totp_setup` (setup only)
   also the secret and the QR).
3. `POST /api/auth/totp` with `ticket` and `code` → session cookie
   (HttpOnly, SameSite=Lax, Secure when `PUBLIC_URL` is https). With
   `totp_setup` you can send `POST /api/auth/totp/skip`
   with only the `ticket` instead of a code.
4. `domain_router` in `api/router.py` has `Depends(get_current_session)`:
   every panel endpoint returns 401 without a session. Exceptions: `/health`,
   `/api/auth/*` and the `browser_fake` fake panel (the shared
   browser opens it without a session).
5. CSRF: POST, PATCH and DELETE without the `X-Open-Revoke-Client` header get
   403. `SameSite=Lax` is not enough, because other `localhost` ports are the same
   "site".

## Panel address

- We build links from `PUBLIC_URL`, never from the `Host` header.
- `PUBLIC_URL` also controls the rest of the address: the host goes to `trusted_hosts`
  (middleware `api/host_check.py`, next to `ALLOWED_HOSTS`), the origin to
  `trusted_origins` (CORS), the https scheme turns on `Secure` cookies. A wrong
  host gets 400 with a JSON `detail` that says at which address to open
  the panel. `GET /api/auth/state` returns `public_url`; the panel
  (`components/layout/address-warning.tsx`) shows a warning when
  it was opened under another origin or over http on a host other than a local one.

## Form prefill in development

- `OPEN_REVOKE_DEV_PREFILL=true` (default `false`): `GET /api/auth/state`
  returns `dev_prefill` with the `DEV_PREFILL_*` values from `app/config.py`
  (organization, currency, admin `admin@example.com`, password
  `open-revoke-dev-password`, invited user's name, e-mail for `/signup`). The sign-in pages then show
  a button that fills the form (`skills/frontend/auth.md`).
- The endpoint is public, so anyone who opens the panel sees the password.
  Local only, never with real data.
- The button does not fill the TOTP code; an account without 2FA signs in without a code.

## Recovering access

Local dev stack:

```bash
dc exec api python -m app.cli list-users
dc exec api python -m app.cli reset-2fa admin@example.com
dc exec api python -m app.cli reset-link admin@example.com   # one-time link to a new password
```

`set-password` prompts for the password, and `dc exec` gives no terminal: enter
the container (`dc exec api sh`) and run `python -m app.cli set-password admin@example.com` there.
In the self-hosting stack (`compose.yaml`) all three commands go through
`docker compose exec -it app /app/backend/.venv/bin/python -m app.cli …`.

In the local stack `dc exec api python -m app.db reset` also restores the account
from the seeder (`backend/app/db/seed.py`): `admin@example.com` /
`open-revoke-dev-password` without 2FA and `member@example.com` (role `user`).

## How to check by hand

There are no automated tests in the dev phase. Sign in to the panel
(http://localhost:18410) with the seeder account; the panel shows the invite
and password reset link to the admin for copying.
An API call with `curl` needs the `open_revoke_session` cookie and, for POST,
PATCH and DELETE, the `X-Open-Revoke-Client` header.

## How to extend

- The panel sends no e-mail: a new link for a person (invite, reset) is shown once to the
  admin, who passes it on.
- New admin-only endpoint: the `AdminDep` parameter.
- 2FA backup codes, SSO (Google, OIDC) and a per-IP attempt limit do not
  exist yet.
