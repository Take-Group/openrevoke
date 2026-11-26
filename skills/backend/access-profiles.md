# Skill: Access profiles

## What it does

An access profile ("Developer", "Sales", "Every employee") is a named set of
apps with a role in each. An admin assigns profiles to people by hand:

- **Assigning** creates the assignment and one onboarding batch for the apps
  of the profiles the person lacks, with the profile's role in each action.
  `dry_run` previews the actions and what the new seats cost per month, in the
  app currency and the organization currency.
- **Unassigning** deletes nothing in apps. It returns `suggested_removals`:
  accounts in apps that no other profile of the person gives. The panel offers
  "Create removal actions" (one `delete_account` action each).
- **Changing a profile** (adding an app) creates no actions. The response says
  how many members now miss access (`members_missing_access`); the panel offers
  "Create actions for N people", which assigns the profile to them again.
- **Drift** per person: what they miss from their profiles, what they have
  outside them, and accounts with another role. Shown on the profile page (per
  member), on the person page and as a dashboard alert per profile.
- `auto_approve_requests`: access requests for an app of the profile, from a
  person with the profile, skip the manager step (`auto_approving_profile`,
  used by access requests, `skills/backend/slack-agent.md` and
  `services/access/requests.py`).

No rules assign profiles by department or group yet.

## Files

| File | What it does |
|---|---|
| `backend/app/models/access_profile.py`, `access_profile_app.py`, `person_access_profile.py` | profile, app with role (PK profile + app), assignment (PK person + profile, `assigned_by`) |
| `backend/app/services/access/profiles.py` | CRUD, `app_role_suggestions`, `auto_approving_profile` |
| `backend/app/services/access/profile_assignment.py` | `assign_to_person`, `assign_members` (one batch per person), `create_actions=false` assigns only |
| `backend/app/services/access/profile_members.py` | person's profiles, person's drift, members with drift, `unassign` with `suggested_removals` |
| `backend/app/services/access/profile_data.py` | bulk loaders, `drift_of`, `members_missing_by_profile` (also the dashboard), `seat_price` |
| `backend/app/services/access/profile_drift.py` | pure rules: `resolve`, `compute` |
| `backend/app/services/onboarding.py` | `plan` (shared by onboarding and the assignment preview), `onboard_person` (role per app) |
| `backend/app/api/access_profiles.py`, `backend/app/schemas/access_profiles.py` | routes and schemas |
| `frontend/src/components/access-profiles/`, `frontend/src/hooks/use-access-profiles.ts` | panel pages (`skills/frontend/pages.md`) |

## Rules

- **Role per app from several profiles**: the first profile by name that sets
  a role wins; a different role in another profile is a warning in the
  assignment response. A profile app without a role means "any role".
- **missing**: an app of the person's profiles with no account other than
  `removed` and no open creation (action or manual task). A person who has
  left misses nothing.
- **extra**: an account of the person (`kind = person`, not `removed`) in an
  app outside all their profiles; only when the person has a profile.
- **role_mismatch**: account role differs from the profile role,
  case-insensitive; no comparison when either is empty.
- A person who has left cannot get a profile (400; skipped in bulk).
- Deleting a profile removes its assignments (CASCADE), never accounts.
- Audit: `access_profile.created`, `.updated` (changes, apps before and
  after), `.deleted`, `.assigned`, `.unassigned` (with `person_id`), plus
  `person.onboarded` with `access_profiles`.

## API

`GET/POST /api/access-profiles`, `GET /api/access-profiles/app-roles`,
`GET/PATCH/DELETE /api/access-profiles/{id}`,
`GET/POST /api/access-profiles/{id}/members`,
`GET/POST /api/people/{id}/access-profiles`,
`DELETE /api/people/{id}/access-profiles/{profile_id}`,
`GET /api/people/{id}/access-drift`.

## How to check by hand

```bash
# preview, then assign (admin token of the dev stack)
curl -s -H 'Authorization: Bearer orv_dev_admin_local_only' -H 'Content-Type: application/json' \
  -d '{"profile_ids":["<id>"],"dry_run":true}' http://localhost:18411/api/people/<person>/access-profiles
```

Then approve the batch in `/actions?batch=` and read the account's role.

## How to extend

- Automatic assignment (department, Google group): a new module that calls
  `profile_assignment.assign_to_person`; keep the drift rules in
  `profile_drift.py` pure.
- A new drift kind: add it to `Drift` and `compute`, then to `AccessDrift`.
