# Skill: First steps after setup (`/welcome` and the dashboard checklist)

## What it does

The first-run setup (`skills/backend/auth.md`) ends with 2FA. The panel then sends
the new admin to `/welcome`, which asks two questions:

1. Where do your people come from: Google Workspace, Microsoft 365, a CSV file, or by hand.
2. Where does your team talk: Slack, Microsoft Teams, or neither.

Nothing connects on `/welcome`. The answers pick the steps of the checklist on the
dashboard ("Set up Open Revoke"), each with a button to the page that does it:

| Answer | Step | Done when |
|---|---|---|
| Google Workspace | Connect Google Workspace, `/discovery` | a `google_workspace` connection exists |
| Microsoft 365 | Import a CSV export, `/people` (marked unsupported: no Entra connector yet) | at least one person |
| CSV file, by hand | Import or add people, `/people` | at least one person |
| Slack | Add the bot, `/settings/slack` | Slack agent `connected` or `connecting` |
| Teams | shown as unsupported, no button | never |
| Neither | no step | |
| (always) | Add the apps you pay for: `/discovery` after Google, else `/apps` | an app not `free` with a price above 0 |

Step state is never stored: `services/setup_checklist.py` works it out from the data
on every request, so a step done on another page shows as done. Only the answers and
"dismissed" are stored, on the `organization` row. The checklist is for admins; it
hides when every step is done or the admin closes it. Without answers it shows one
step, "Answer", back to `/welcome`, plus the apps step.

## Files

| File | What it does |
|---|---|
| `backend/app/models/organization.py`, `models/enums.py` | `people_import` (`PeopleImport`), `chat_platform` (`ChatPlatform`), `onboarding_dismissed_at` |
| `backend/app/services/setup_checklist.py` | `overview`, `save_choices`, `dismiss`; one function per step |
| `backend/app/api/setup_checklist.py`, `schemas/setup_checklist.py` | `GET /api/onboarding`, `PUT /api/onboarding/choices` (admin), `POST /api/onboarding/dismiss` (admin) |
| `frontend/src/components/onboarding/welcome-view.tsx`, `app/welcome/page.tsx` | the two questions, steps 4-5 of the first run, in the sign-in frame (`FRAMELESS_ROUTES` in `components/auth/routes.ts`) |
| `frontend/src/components/auth/setup-progress.tsx` | `SetupProgress`: five segments along the top edge of the card, no text, in the `eyebrow` of `AuthCard` on every first-run step (setup, 2FA, `/welcome`) |
| `frontend/src/components/auth/auth-gate.tsx` | `/setup` with a signed-in user goes to `/welcome` |
| `frontend/src/components/dashboard/setup-checklist.tsx` | the checklist |
| `frontend/src/hooks/use-onboarding.ts`, `lib/api/onboarding-types.ts` | hooks and types |

`services/onboarding.py` is something else: onboarding a person into apps (actions).

## How to extend

- A new answer (e.g. Microsoft 365 once an Entra connector exists): change the step in
  `_people_item` to point at the connector's setup page and its "done" rule, and set
  `supported=True`. Change the hint in `welcome-view.tsx`.
- A new step: a function that returns a `ChecklistItem` with a new `key` (add it to the
  `Literal` in the schema and to `ChecklistItem` in `onboarding-types.ts`), appended in
  `overview`. Its "done" must come from data, not from a click.
- Check by hand: `dc exec api python -m app.db reset`, sign in, open `/welcome`, answer,
  look at the dashboard; do the step on its page and reload.
