# Skill: panel pages

## What it does

The panel has the pages from the sidebar menu and an app discovery page
(`/discovery`, described in `skills/backend/app-discovery.md`). Each page is a thin
file in `src/app/` (metadata, URL parameters) and a view in
`src/components/<area>/`. The sidebar and the page frame are in the root layout,
so pages do not add them.

## Panel frame (`src/components/layout/`)

The panel has no top bar. All navigation is in the sidebar
(`app-sidebar.tsx`): the mark and name (`brand-mark.tsx`, also on the sign-in
pages and in the mobile bar) with a collapse button, the search (opens
the ⌘K palette from `command-menu.tsx`), the pages from `nav-items.ts` and, at the bottom, the account
menu (`nav-user.tsx`). On mobile the sidebar is a slide-out panel, so
`admin-layout.tsx` shows only a narrow bar with a menu button there.

The account menu shows the signed-in user and the organization from
`GET /api/auth/state` (`useAuthState`). "Account" and "Organization" lead
to `/settings`, "Users" to `/settings/users`, "Sign out" signs the user out.
"Notifications" and "API tokens" show a "not available yet" toast. The theme
is changed by the submenu from `theme-toggle.tsx`. Sign-in pages and the session gate:
`skills/frontend/auth.md`.

Size: `html` is 16 px. Tables, forms and menus are 14 px
(`text-sm`), labels and column headers 12-13 px, the page title 20 px. Write new
sizes in rem (Tailwind classes), not in px.

## Pages

| Path | View file | Hooks | URL parameters |
|---|---|---|---|
| `/` | `components/dashboard/dashboard-view.tsx` | `useDashboard` | - |
| `/people` | `components/people/people-view.tsx` | `usePeople`, `useCreatePerson`, `useImportPeople` | `status` |
| `/people/new` | `components/people/new-person-view.tsx` | `useCreatePerson` | - |
| `/people/import` | `components/people/import-people-view.tsx` | `useImportPeople` | - |
| `/people/[id]` | `components/people/person-detail-view.tsx` | `usePerson`, `useDeletePerson`, `useSetPersonKind`, `useCreateAction`, `useActions`, `useApps` | - |
| `/people/[id]/edit` | `components/people/edit-person-view.tsx` | `usePerson`, `useUpdatePerson` | - |
| `/people/[id]/add-to-app` | `components/people/add-to-app-view.tsx` | `usePerson`, `useApps`, `useCreateAction` | - |
| `/people/[id]/onboard` | `components/people/onboard-view.tsx` | `usePerson`, `useApps`, `useActions`, `useOnboardPerson` | - |
| `/people/[id]/offboard` | `components/people/offboard-view.tsx` | `usePerson`, `useApps`, `useActions`, `useOffboardPerson` | - |
| `/apps` | `components/apps/apps-view.tsx` | `useApps` (category filter from `categories`) | - |
| `/apps/new` | `components/apps/new-app-view.tsx` | `useCatalogSearch` (in `CatalogAppPicker`), `useCreateApp`, `useAppLogo`, `useConnectors`, `useAuthState` | - |
| `/apps/new/bulk` | `components/apps/bulk-apps-view.tsx` | `useCatalogSearch`, `useCreateApps` | - |
| `/accounts/import` | `components/apps/import-accounts-view.tsx` | `useImportAccounts` | - |
| `/apps/[id]` | `components/apps/app-detail-view.tsx` | `useApp`, `useAppAccounts`, `useUpdateAccount`, `useConnectors`, `useCheckConnection`, `useSyncConnection`, `useSyncRuns`, `useSyncInProgress`, `useUpdateApp`, `useDeleteApp` | `tab` (`accounts`, `connection`, `sync`, `settings`), `accounts` (`all`, `unassigned`, `removed`) |
| `/apps/[id]/accounts/new` | `components/apps/new-account-view.tsx` | `useApp`, `useCreateAccount` | - |
| `/apps/[id]/accounts/bulk` | `components/apps/paste-accounts-view.tsx` | `useApp`, `usePasteAccounts` | - |
| `/apps/[id]/connection/edit` | `components/apps/connection-form-view.tsx` | `useApp`, `useConnectors`, `useSaveConnection` | `connector` (preselected after "Add app") |
| `/actions` | `components/actions/actions-view.tsx` | `useActions`, `useActionTransition`, `useApproveBatch`, `useRevealSecret` | `tab` (`pending`, `progress`, `done`, `failed`, `cancelled`), `batch` |
| `/discovery` | `components/discovery/discovery-view.tsx` | `useDiscovery`, `useDiscoveredApps`, `useScanNow`, `useConnectDiscoverySource`, `useTrackDiscoveredApp`, `useUpdateDiscoveredApp` | - |
| `/discovery/[id]` | `components/discovery/discovered-app-view.tsx` | `useDiscoveredApp`, `useTrackDiscoveredApp`, `useUpdateDiscoveredApp` | - |
| `/browser` | `components/browser/browser-view.tsx` | `useBrowserState`, `useOpenInBrowser` | - |
| `/settings/ai` | `components/ai/ai-settings-view.tsx` | `useAiSettings`, `useSaveAiSettings`, `useAiModels`, `useTestAi` | - |
| `/settings/slack` | `components/slack/slack-view.tsx` | `useSlackAgent`, `useCreateSlackApp`, `useSaveSlackTokens`, `useUpdateSlackAgent`, `useSetSlackAvatar`, `useRemoveSlackAgent` | `installed`, `error` (return from Slack OAuth) |
| `/requests` | `components/requests/requests-view.tsx` | `useAccessRequests` | - |
| `/audit` | `components/audit/audit-view.tsx` | `useAudit` | `entity` and `id` (one entity), `app` or `person` (the full history of an app or a person) |

A page with URL parameters reads them in a server component
(in Next.js 16, `searchParams` and `params` are `Promise` objects) and passes them
to the view as initial values. The view gets a `key` from these parameters,
so that a link to the same page with a different filter resets the state.

## Shared components (`src/components/common/`)

- `page-header.tsx`: `PageHeader` (title, count in `meta`, buttons),
  `DetailHeader`, `SectionHeader`. No icon: the `icon` prop is accepted,
  but not drawn.
- `panel.tsx`: a white block with a thin border and an optional title row
  (a list, a summary on the dashboard). Do not nest panels.
- `query-state.tsx`: loading, error, 501 for one query.
- `table-shell.tsx`: `Pager` (limit/offset) below a table.
- `status-badge.tsx`: status colour for every API enum, `TagBadge`.
- `money-list.tsx`: amounts in several currencies side by side, without conversion.
- `converted-money.tsx`: an amount in the organization currency with the original (`skills/frontend/currency.md`).
- `confirm-dialog.tsx`: a confirmation in a plain `Dialog`.
- `person-picker.tsx`: person search (a `?q=` query to the API).
- `empty-state.tsx`: empty state, "not available yet", inline error and
  warning.
- `form-field.tsx`: label, field, hint.

Formatting is in `src/lib/format.ts`: amounts `1 234,50 PLN`, dates
`22.11.2026, 18:24` in the time zone from `timezone.md`, enum labels.

## Write actions in the panel

The backend is described in skills/backend/actions.md. Panel:

- `/actions`: the counts on the tabs come from `counts` in the `GET /api/actions` response.
  `useActions` polls every 2 s while any action on the page is in progress
  (`isMoving`: `running`, `verifying` or an approved connector write).
  The status in the table has the step description and the error text (`actions-table.tsx`).
- "Approve" shows the error in the row, not in a toast. On a 400 from a
  connector write (writes disabled) there is a link to
  `/apps/<id>?tab=connection`. "Approve batch" warns with a toast about actions
  with `not_approved`.
- "Reveal password" (`reveal-secret-dialog.tsx`) with `has_secret_result`:
  first a warning that the password is shown once, then the value and "Copy".
- Removal label: "Suspend" instead of "Remove" when the app has
  `delete_suspends` (Google Workspace); in the action, the `suspends` field
  (`actionOperation` in `lib/format.ts`, `removeVerb` in `lib/write-mode.ts`).
- Person: "Onboard" (`onboard-view.tsx`, `/people/[id]/onboard`) is a list
  of apps with checkboxes; apps with an account or an open creation are disabled, as
  in the backend. The result leads to `/actions?batch=…`. `batch-bar.tsx` shows
  batches of both kinds (`reason`).
- Person: "Add to app", "Remove from app" and the offboarding preview say what
  will happen, from the app's `create_mode` / `delete_mode` (`automatic`,
  `writes_disabled`, `manual`; texts in `lib/write-mode.ts`). "Delete" is
  shown only with `can_delete` (`delete-person-button.tsx`).

## App discovery in the panel

- The dashboard shows the `setup-checklist.tsx` checklist (steps from
  `GET /api/onboarding`, `skills/backend/setup-checklist.md`). Without a source
  (`source = null` in `GET /api/discovery`), `/discovery` shows the
  `discovery-setup.tsx` wizard: service account steps, scopes with a copy
  button (from `connectors[].required_scopes`), a form. A Google error
  comes back as 400 and is shown below the form, not in a toast.
- `useDiscovery` polls every 3 s while `scan_running`, and after the scan ends
  it refreshes the app list, people and the dashboard.
- The list opens the "Left or removed" filter by default when there are such sign-ins.
- Person: the "Google sign-ins" tab (`person-discovered-apps.tsx`) shows
  the apps the person signed in to, and whether they are tracked in Open Revoke.
- The types are in `lib/api/discovery-types.ts`, because `types.ts` is close to the
  600-line limit.

## Connection form from JSON Schema

`components/apps/connection-form-view.tsx` draws fields from the connector's `config_schema`
(`GET /api/connectors`) through `src/lib/json-schema.ts`
and `components/apps/schema-fields.tsx`. Supported: `string`, `integer`,
`number`, `boolean`, `enum`, string arrays, `anyOf` with `null`, `$ref`
to `$defs`, `pattern`, `x-multiline`. A field with `secret: true`, with
`format: password`, with `writeOnly` or from the `secret_fields` list is a password
field. Its value goes to `secrets`, not to `config`. Empty secret fields
with the same connector send `secrets: null`, which means
"keep the saved value". A field whose name is in the connection's `secret_fields_set` has a
"Set" marker and is not required.

## Look rules

- Themes: light and dark, by default from the system (`next-themes`,
  `attribute="class"` in `components/providers.tsx`). Colours are tokens
  from `globals.css`, copied from Geist (Vercel's design system, 24.11.2026):
  pure greys, a grey page background (`page`, #fafafa; #000 in dark),
  white cards and fields (`background`, `card`), borders #ebebeb, `shadow-card`
  under cards. Black (`primary`) is for primary buttons and headings.
  `subtle` (#fafafa) is the background of table headers and card footers. The brand violet
  (`brand` #7c5cff, as on openrevoke.com) is an accent in small doses:
  field focus, checked checkboxes and switches, the active menu item
  (`brand-soft` background, violet icon), the active tab underline,
  progress bars, link underlines and hover (`link` = `brand-ink`, darker
  for contrast), text selection. Never large fills or the primary
  button. Signal
  colours only in statuses: green, amber, red (tokens
  `success`, `warning`, `destructive`). Add new colours as tokens
  in both themes.
- Build screens only from shared components: catalogue and rules
  in `ui-kit.md` (no native `<select>` and checkboxes).
- Fonts Geist Sans and Geist Mono (`geist`). The base size is described in the
  "Panel frame" section.
- Little text: a page has a short title (`PageHeader`) with no icon and no
  description paragraph. An explanation goes into `InfoTip` (an "i" icon with a tooltip).
  A button is an icon and one or two words. Empty state (`EmptyState`): a small
  grey icon, one line, one button.
- No icons in tiles: an icon does not sit in a coloured or grey square next to
  a title, in a card, in an alert or in a form header. Borders are thin
  (`border`, 6 px radius, `rounded-lg`), no cards in cards.
- Statuses are `StatusBadge`: a dot and text in a thin border. The `info` tone
  (in progress, invited) is ink, `neutral` is light grey. The integration type is
  `IntegrationIcon` (API, SCIM, Browser, Manual). The app logo
  (`AppAvatar`) is the logo an admin uploaded, else the `simple-icons` mark
  bundled in the build, else `logo_url` from the API (a catalog PNG); it sits in
  a neutral square with a thin border. Pass `logoUrl={app.logo_url}` wherever the
  API gives it (`AppListItem`, `AppRef`). The panel does not fetch icons
  from outside. Without a brand icon there is an initial (in the brand colour when it is
  readable). People avatars are initials on a neutral background.
- Tables: `components/data-table/data-table.tsx` (TanStack Table): white
  10 px border, 12 px header on the `subtle` background, 44 px rows, no zebra stripes;
  sorting, sticky header, row actions in a "…" menu (`row-actions.tsx`), amounts
  aligned right. One text column gets `meta.className`
  `"w-full max-w-0 min-w-40"`. It then takes the free space and truncates the text,
  so the table does not overflow its border at 1280 px. Hide less important columns
  on narrower screens (`hidden min-[88rem]:table-cell`, from 1408 px).
- Details (person, app): `DetailHeader`, a row of numbers (`stat.tsx`)
  and `TabsList variant="line"` tabs with a `tab` parameter in the URL. The default
  tab variant and `Segmented` are a grey track with a white active pill.
- Dashboard: numbers in one bar with thin dividers (`kpi-cards.tsx`),
  alerts and costs in `Panel`.
- Every add and edit form is a separate subpage with its own URL
  (`form-page.tsx`, `FormPage`; rules in `ui-kit.md`, "Forms are pages").
  No side panels and no forms in modals: an AI agent in the browser
  must reach a form by its address. Short confirmations go in `Dialog`
  (`confirm-dialog.tsx`). Control radius 7-8 px, borders 10 px, modals `rounded-xl`.
- Modals (`components/ui/dialog.tsx`, Base UI) close on a click
  outside and on the Escape key. Do not use `AlertDialog`: Base UI does not close it
  on a click outside.
- Select lists are `components/common/option-select.tsx` (`OptionSelect`) or
  `searchable-select.tsx` for long lists, never a native `<select>`; switches
  between a few options are `components/common/segmented.tsx`.
- A link that looks like a button: `<Link className={buttonVariants()}>`,
  not `Button render={<Link />}` (Base UI warns in the console).
- Checking the look: screenshots from headless Chromium (Playwright through
  `uv run --with playwright`) at 1280 and 1440 px, in both themes.

## How to add a page

1. A file `src/app/<path>/page.tsx` with `metadata` and the view.
2. The view in `src/components/<area>/<name>-view.tsx`, data through hooks.
3. An entry in `NAV_MAIN` or `NAV_TOOLS` in `src/components/layout/nav-items.ts`
   (the sidebar and the ⌘K palette use the same list).
4. A row in the "Pages" table above.
