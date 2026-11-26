# open-revoke/frontend/src/components/people/

People (employees and service accounts): list, detail page, onboarding and offboarding, CSV import. Hooks: `use-people.ts` (plus `use-actions`, `use-apps`, `use-audit`, `use-discovery`). Pages: `src/app/people/page.tsx` (`PeopleView`), `src/app/people/[id]/page.tsx` (`PersonDetailView`) and the form pages `/people/new`, `/people/import`, `/people/[id]/edit`, `/people/[id]/add-to-app`, `/people/[id]/onboard`, `/people/[id]/offboard`. Every form is its own page (`FormPage`), not a side panel or dialog.

- `people-view.tsx`: `PeopleView`: search, kind, status and "No manager" filters (`?no_manager=true`), list, links "Import" and "Add person". Hooks `usePeople`, `useDebouncedValue`.
- `people-table.tsx`: `PeopleTable`: rows (department and job title column), links to detail and `/audit?person=`.
- `new-person-view.tsx`: `NewPersonView` (`/people/new`): create, then goes to `/people/[id]`. Hook `useCreatePerson`.
- `edit-person-view.tsx`: `EditPersonView` (`/people/[id]/edit`): edit, back to the person. Hook `useUpdatePerson`.
- `person-query.tsx`: `PersonQuery` (id, render-prop children): loads the person for the pages under `/people/[id]/`. Hook `usePerson`.
- `person-fields.tsx`: `PersonFields`, `PersonForm`, `ManagerChoice`, `EMPTY_PERSON`: fields shared by add and edit (manager with `PersonPicker`, department, job title).
- `import-people-view.tsx`: `ImportPeopleView` (`/people/import`): Preview (dry run) first, then the real import (columns include `manager_email`, `department`, `job_title`). Hook `useImportPeople`.
- `import-preview.tsx`: `ImportPreview`: rows the dry run would create or change.
- `person-detail-view.tsx`: `PersonDetailView`: header and panels, links Add to app, Onboard, Offboard to their pages. Hook `usePerson`.
- `person-manager-section.tsx`: `PersonManagerSection`: "Reporting line" panel: manager (auto or manual), department, job title, reports.
- `person-accounts-table.tsx`: `PersonAccountsTable`: accounts of the person, per-row action requests. Hooks `useApps`, `useCreateAction`.
- `person-sources-table.tsx`: `PersonSourcesTable`: where the person was found (discovery or import).
- `person-discovered-apps.tsx`: `PersonDiscoveredApps`: apps the person signed in to with Google (untracked ones need a manual check). Hook `usePersonDiscoveredApps`.
- `person-activity.tsx`: `PersonActivity`: open actions and audit history. Hooks `useActions`, `useAudit`.
- `person-more-menu.tsx`: `PersonMoreMenu`: edit (`/people/[id]/edit`), history, copy e-mail, delete (only without accounts and actions), service-account switch. Hooks `useDeletePerson`, `useSetPersonKind`.
- `person-kind-badge.tsx`: `PersonKindBadge`: "Service account" with the reason; nothing for people.
- `onboard-view.tsx`: `OnboardView` (`/people/[id]/onboard`): accounts in several apps as one batch awaiting approval, then goes to `/actions?batch=`; mirrors backend `services/onboarding.py`. Hooks `useActions`, `useApps`, `useChoices`, `useOnboardPerson`.
- `offboard-view.tsx`: `OffboardView` (`/people/[id]/offboard`): previews the plan, then offboards and goes to `/actions?batch=`. Hooks `useActions`, `useApps`, `usePlan`, `useOffboardPerson`.
- `app-choice-list.tsx`: `AppChoiceList`, `AppChoiceRow`: app list on the two pages above.
- `add-to-app-view.tsx`: `AddToAppView` (`/people/[id]/add-to-app`): one create_account action (or manual task), back to the person. Hooks `useApps`, `useCreateAction`.
