# Skill: panel sign-in (frontend)

## What it does

Sign-in pages without the panel frame, a gate that guards the session, and
account, organization and user settings. Backend: `skills/backend/auth.md`.

## Files

| File | Role |
|---|---|
| `frontend/src/components/auth/auth-gate.tsx` | in `app/layout.tsx` instead of `AdminLayout`: setup, sign-in or the panel |
| `frontend/src/components/auth/routes.ts` | public pages, `safeNext` (panel paths only) |
| `frontend/src/components/auth/auth-shell.tsx` | frame of the sign-in and first-run pages, like the Vercel sign-up (`AuthShell`: theme switch in the top right corner, logo centred above the card; `AuthCard`: 550 px card, centred 24 px title, no description in the first-run step) |
| `frontend/src/components/auth/setup-progress.tsx` | `SetupProgress`: five segments along the top edge of the card, no label, in the `eyebrow` of each setup step and of `/welcome`. The 2FA step gets it through the `Frame` prop in `TotpStep` (a stable module-level component) |
| `frontend/src/components/auth/totp-step.tsx` | code step at sign-in with 2FA; with `totp_setup` (setup only) a QR code, the key and "Skip for now"; exports `TotpEnrollmentPanel` and `TotpCodeField` for the settings |
| `frontend/src/components/settings/two-factor-view.tsx`, `frontend/src/app/settings/two-factor/` | `/settings/two-factor`: turning 2FA on (QR code, first code) or off (current code); a section in `/settings` shows the state |
| `frontend/src/components/auth/setup-view.tsx` | `/setup?token=`: first checks the setup link token (`useSetupTokenCheck`); without a valid one it shows the `open-revoke setup-link` command; then the setup wizard: step 1 organization (name, currency, time zone suggested from the computer), step 2 admin account, step 3 2FA; nothing goes to the API before step 2 |
| `frontend/src/components/auth/login-view.tsx`, `register-view.tsx`, `password-reset-views.tsx` | page views; sign-in shows "No account? Create one" when `registration_enabled` |
| `frontend/src/components/auth/signup-view.tsx` | `/signup` (self sign-up): after submit, "Your account is ready" (domain from auto-approval) or "Waiting for approval" |
| `frontend/src/components/me/*`, `frontend/src/app/me/*` | `user` role: `/me` (My access: accounts, requests) and `/me/request` (request form) |
| `frontend/src/components/settings/signup-settings.tsx` | "Sign-up" section in Settings → Users: sign-up, auto-approval, domains |
| `frontend/src/components/auth/form-parts.tsx` | form fields, new password twice, error |
| `frontend/src/components/auth/dev-fill.tsx` | development only: a small "Dev fill" pill in the bottom left corner of the screen (a portal to `<body>`, outside the card, so it does not change the look of the form) fills the form with the `dev_prefill` values from `GET /api/auth/state` and submits it at once; sign-up gets `signup_email` with a `+<random>` suffix (`uniqueEmail`); without the flag it renders nothing |
| `frontend/src/app/{login,setup,register,signup,forgot-password,reset-password}/page.tsx` | public pages |
| `frontend/src/app/settings/page.tsx`, `settings/users/page.tsx` | settings: account and organization, users and invites |
| `frontend/src/components/settings/*` | settings views |
| `frontend/src/hooks/use-auth.ts`, `use-users.ts` | API hooks |
| `frontend/src/components/layout/nav-user.tsx` | account menu in the sidebar: signed-in user, sign-out |

## Flow

1. `AuthGate` reads `GET /api/auth/state` (key `["auth"]`).
2. `setup_required` → `/setup`. No user → `/login?next=<path>`.
   A signed-in user on a guest page → `next` or `/`. The `user` role can
   open only `/me…` and `/settings` (`userRedirect` in `routes.ts`); other
   paths end on `/me`. The `user` sidebar has only `NAV_USER`, with no
   search and no admin queries (`useDashboard`).
3. Sign-in and sign-up from an invite: `step: done` → `useEnterPanel`
   clears the cache and refreshes `["auth"]`, and the gate moves to the panel. An account
   with 2FA (`step: totp`) and setup (`totp_setup`) show `TotpStep`; a successful
   code does the same.
4. `AuthGate` sets the organization time zone (`setAppTimeZone`
   in `lib/date-time.ts`) before the panel renders and remounts the panel after it
   changes, so all dates are in the organization time zone.
5. A 401 from any query (`providers.tsx`) refreshes `["auth"]`, so
   an expired session ends on `/login`.
6. `apiFetch` sends `X-Open-Revoke-Client: panel` (CSRF; without it the API
   rejects writes).
7. When the API runs with `OPEN_REVOKE_DEV_PREFILL=true`, `AuthState.dev_prefill`
   carries test values, and setup (both steps), sign-in, sign-up
   and password reset show `DevFillButton`. The values are in the backend
   (`DEV_PREFILL_*` in `backend/app/config.py`), not in the frontend code.

## How to extend

- New public page: add the path to `routes.ts`.
- New sign-in form: add `DevFillButton` inside `<form>` (it submits the nearest form) with an `onFill` that sets its fields.
- Account menu item: `ACCOUNT_ITEMS` in `nav-user.tsx`, with `href`.
