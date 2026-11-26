# open-revoke/frontend/src/app/

App Router of the panel. Every `page.tsx` is a thin server component: it reads `params` or `searchParams` and renders one `*View` from `src/components/<feature>/`; logic and data fetching live in the view and its hooks. Sign-in pages and the panel shell are decided by `AuthGate` (mounted in `layout.tsx`).

- `layout.tsx`: root layout; Geist fonts, metadata title template, reads cookie `sidebar_state`, wraps children in `Providers` and `AuthGate`.
- `globals.css`: Tailwind 4 import, theme tokens (`@theme inline`), light and dark CSS variables, animations.
- `shadcn.css`: vendored `shadcn/tailwind.css` (data-state variants, `no-scrollbar`, `scroll-fade`, `shimmer`): the shadcn package is not a dependency; its CLI runs with `bunx shadcn@latest`.
- `icon.svg`, `apple-icon.png`: the logo's door as the browser and home screen icon (same files as openrevoke.com).
- `not-found.tsx`: 404 page (`EmptyState` with a button back).
- `page.tsx`: `/` renders `DashboardView`.
- `actions/`: `/actions` renders `ActionsView`; `?tab=` picks the tab, `?batch=<uuid>` filters one batch.
- `access-profiles/`: `/access-profiles` renders `AccessProfilesView`; `new/` (`NewAccessProfileView`); `[id]/` is `/access-profiles/<id>` (`AccessProfileDetailView`) with form pages `[id]/edit/` (`EditAccessProfileView`) and `[id]/members/add/` (`AddMembersView`, `?missing=1`).
- `apps/`: `/apps` renders `AppsView`; `new/` is `/apps/new` (`NewAppView`), `new/bulk/` is `/apps/new/bulk` (`BulkAppsView`); `[id]/` is `/apps/<id>` and renders `AppDetailView` (`?tab=`, accounts filter), with form pages `[id]/accounts/new/` (`NewAccountView`), `[id]/accounts/bulk/` (`PasteAccountsView`) and `[id]/connection/edit/` (`ConnectionFormView`, `?connector=`).
- `accounts/`: `import/` is `/accounts/import` (`ImportAccountsView` from `components/apps/`).
- `audit/`: `/audit` renders `AuditView`; `?entity=&id=&app=&person=` prefilter the log.
- `browser/`: `/browser` renders `BrowserView` (live view of the shared browser).
- `discovery/`: `/discovery` renders `DiscoveryView`; `[id]/` is `/discovery/<id>` and renders `DiscoveredAppView`.
- `forgot-password/`: `/forgot-password` renders `ForgotPasswordView`.
- `login/`: `/login` renders `LoginView`.
- `me/`: `/me` renders `MyAccessView` (home of a `user`); `request/` is `/me/request?app=` (`RequestAccessView`); `approvals/` is `/me/approvals` (`ApprovalsView`), `approvals/[id]/` `/me/approvals/<id>` (`ApprovalDetailView`).
- `people/`: `/people` renders `PeopleView` (`?status=`); `new/` (`NewPersonView`) and `import/` (`ImportPeopleView`); `[id]/` is `/people/<id>` and renders `PersonDetailView` (`?tab=`), with form pages `[id]/edit/`, `[id]/add-to-app/`, `[id]/onboard/`, `[id]/offboard/`, `[id]/access-profiles/add/` (`AssignProfilesView`).
- `register/`: `/register?token=` renders `RegisterView` (accepting an invite).
- `signup/`: `/signup` renders `SignupView` (self sign-up).
- `requests/`: `/requests` renders `RequestsView` (access requests with filters and CSV export); `[id]/` is `/requests/<id>` (`RequestDetailView`).
- `reset-password/`: `/reset-password?token=` renders `ResetPasswordView`.
- `settings/`: own AGENTS.md. `/settings` and its sub-pages (users, two-factor, AI model, Slack).
- `setup/`: `/setup?token=` renders `SetupView` (first admin of a new installation, from the setup link printed on the server).
- `welcome/`: `/welcome` renders `WelcomeView` (first-run questions).
