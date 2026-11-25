# open-revoke/frontend/src/components/auth/

Sign-in, first-run setup, registration by invite, password reset and 2FA, in a frame without the sidebar. Hooks: `use-auth.ts`. `AuthGate` wraps every page in `src/app/layout.tsx`; the views are rendered by `src/app/{login,setup,register,signup,forgot-password,reset-password}/page.tsx`.

- `auth-gate.tsx`: `AuthGate`, `useHoldSignInPage`: redirects by auth state and route lists; held while a TOTP step shows, or a refetch would drop the QR code of a new account.
- `routes.ts`: `GUEST_ONLY_ROUTES`, `PUBLIC_ROUTES`, `FRAMELESS_ROUTES`, `USER_HOME`, `isRoute`, `safeNext` (`?next=` only to a panel path), `userRedirect` (a `user` opens only `/me` and `/settings`).
- `auth-shell.tsx`: `AuthShell`, `AuthCard`: centred card, wordmark, theme switch.
- `login-view.tsx`: `LoginView` (`/login`), then `TotpStep`. Hook `useLogin`.
- `setup-view.tsx`: `SetupView` (`/setup?token=`): checks the setup link's token first (`useSetupTokenCheck`); without a valid one shows how to get a link on the server (`SetupLinkNeeded`); then organization, admin, 2FA. Hooks `useSetup`, `useRestartAtLogin`.
- `setup-progress.tsx`: `SetupProgress`: first-run bar (setup, then `/welcome`).
- `register-view.tsx`: `RegisterView` (`/register?token=`): invite, then 2FA. Hooks `useInviteInfo`, `useRegister`, `useRestartAtLogin`.
- `signup-view.tsx`: `SignupView` (`/signup`): self sign-up, then "ready, sign in" or "waiting for approval". Hook `useSignup`.
- `password-reset-views.tsx`: `ForgotPasswordView` (no form: a reset link comes from an admin, or the CLI for an admin), `ResetPasswordView`. Hook `useResetPassword`.
- `totp-step.tsx`: `TotpStep`, `TotpFrame`: the code step of a sign-in with 2FA; QR and "Skip for now" only for `totp_setup` (first-run setup). Also `TotpEnrollmentPanel` (QR and key) and `TotpCodeField`, used by `settings/two-factor-view.tsx`. Hooks `useVerifyTotp`, `useSkipTotp`.
- `form-parts.tsx`: `TextField`, `NewPasswordFields`, `FormError`, `passwordProblem`, `MIN_PASSWORD`; also used by `settings/` and `onboarding/`.
- `dev-fill.tsx`: `DevFillButton`, `useDevPrefill`, `uniqueEmail`: a "Dev fill" pill in the bottom left corner (portal to `<body>`) fills the form it is placed in from `dev_prefill` and submits it; only when the API runs with OPEN_REVOKE_DEV_PREFILL.
