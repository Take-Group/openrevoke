# open-revoke/frontend/src/components/settings/

Settings pages: `/settings` (account, and for admins the organization) and `/settings/users` (admins only). `/settings/ai` (AI model) and `/settings/slack` (Slack bot) live in `ai/` and `slack/`. Hooks: `use-auth.ts`, `use-users.ts`, `use-currencies.ts`.

- `settings-view.tsx`: `SettingsView` (`/settings`): account, 2FA state (link to `/settings/two-factor`) and password for everyone; organization (name, currency, time zone), password manager and exchange rates for admins. Hooks `useChangePassword`, `useCurrencies`, `useRefreshRates`, `useUpdateOrganization`.
- `users-view.tsx`: `UsersView` (`/settings/users`): sign-ups waiting for approval (approve, reject), users (role, password reset link, reset 2FA, remove), then sections for sign-up rules, invite and open invites. Hooks `useUsers`, `useApproveUser`, `useUpdateUserRole`, `useRemoveUser`, `useCreateResetLink`, `useResetUserTotp`, `useInvites`, `useRevokeInvite`.
- `two-factor-view.tsx`: `TwoFactorView` (`/settings/two-factor`, form page): turn 2FA on (QR, first code) or off (current code). Hooks `useStartTwoFactor`, `useSetTwoFactor`.
- `signup-settings.tsx`: `SignupSettings`: sign-up on or off, automatic approval and its e-mail domains. Hooks `useOrganizationSettings`, `useUpdateOrganization`.
- `invite-form.tsx`: `InviteForm`: e-mail and role, shows the one-time link. Hook `useCreateInvite`.
- `settings-section.tsx`: `SettingsSection`, `SettingsFooter`: the settings card frame, also used by `apps/app-settings-tab.tsx`.
