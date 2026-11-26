# open-revoke/frontend/src/components/access-profiles/

Access profiles: named sets of apps with a role each, assigned to people (`/access-profiles`, `/people/[id]/access-profiles/add`). Hooks in `use-access-profiles.ts`, types in `lib/api/access-profile-types.ts`, backend `skills/backend/access-profiles.md`. `profile-parts.tsx` and `profile-choice-list.tsx` are also used by `people/` (Onboard page, person section).

- `access-profiles-view.tsx`: `AccessProfilesView` (`/access-profiles`): table with app logos, members, missing-access dot, cost per person, "New profile".
- `access-profile-detail-view.tsx`: `AccessProfileDetailView` (`/access-profiles/[id]`): stats, "Create actions for N people" notice, apps with roles and seat price, members, Edit, Delete (confirmation).
- `profile-members-table.tsx`: `ProfileMembersTable`: members with missing, extra, other role, assigned date.
- `access-profile-form.tsx`: `AccessProfileForm`, `ProfileDraft`, `EMPTY_PROFILE`, `toPayload`: name, description, apps with role suggestions from existing accounts, skip-manager switch.
- `new-access-profile-view.tsx`: `NewAccessProfileView` (`/access-profiles/new`).
- `edit-access-profile-view.tsx`: `EditAccessProfileView` (`/access-profiles/[id]/edit`); toasts how many members now miss access.
- `add-members-view.tsx`: `AddMembersView` (`/access-profiles/[id]/members/add`, `?missing=1` preselects members who miss access): people picker, Preview (`dry_run`), Assign.
- `assign-profiles-view.tsx`: `AssignProfilesView` (`/people/[id]/access-profiles/add`): profile checkboxes, Preview, Assign, then `/actions?batch=`.
- `assignment-preview.tsx`: `AssignmentPreview`: accounts to create with role, write mode and seat cost, skipped apps, role warnings, monthly total.
- `profile-choice-list.tsx`: `ProfileChoiceList`: profiles with checkboxes and app logos (assign page, Onboard page).
- `profile-parts.tsx`: `AppLogos`, `RoleTag`, `AppNames`.
