# open-revoke/frontend/src/app/settings/

Settings routes; the sidebar lists them under Settings (`NAV_SETTINGS` in `components/layout/nav-items.ts`).

- `page.tsx`: `/settings` renders `SettingsView` (account, and for admins the organization).
- `users/`: `/settings/users` renders `UsersView` (admins only).
- `two-factor/`: `/settings/two-factor` renders `TwoFactorView` (form page, not in the sidebar).
- `ai/`: `/settings/ai` renders `AiSettingsView`: the one language model for every AI feature.
- `slack/`: `/settings/slack` renders `SlackView`; `?installed=` and `?error=` come back from Slack's OAuth.
