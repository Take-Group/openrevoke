# Skill: UI kit (build every screen from shared components)

Read this before you add or change anything that shows on screen in the
panel: a page, a form, a dialog, a list, a message.

## The rule

The panel is built only from shared components. A page composes them; it
does not style controls by hand. Then every select, checkbox, box and alert
looks the same on every page, in both themes.

1. Use the component from the catalogue below. Do not write a raw
   `<select>`, `<input type="checkbox">`, `<input type="radio">`,
   `<datalist>`, `<textarea>` or a `<button>` with hand classes. The browser
   draws native controls in its own style, so they never match the panel.
   Files go through `FileDrop` (field) or `FileButton` (button).
2. If the catalogue has no component for the job, add one to
   `components/common/` (or a primitive to `components/ui/`), then use it.
   Do not build it inline in the page. If two pages need the same markup,
   it becomes a component.
3. Do not override the look of a shared component from a page: no other
   height (`h-7`, `h-9`, `h-10` on an `Input`), radius, border or colour in
   `className`. Layout classes (width, margin, `max-w-*`) are fine. If a
   variant is missing, add it to the component.
4. Colours are tokens only: `foreground`, `muted-foreground`, `subtle`,
   `border`, `destructive`, `success`, `warning` (`text-success`,
   `bg-warning/10`), and the brand violet `brand`, `brand-ink` (small
   text), `brand-soft` (quiet fill), `brand-foreground` (text on `brand`).
   Never `emerald-*`, `amber-*`, `red-*`, `blue-*`, `indigo-*` or hex. A new colour is a new token in `app/globals.css`, in
   both themes.
5. Anything clickable is a kit component, never a `div`, `span` or `li`
   with `onClick`: then it gets the pointer cursor, keyboard focus and a
   focus ring for free. See "Interactive states" for building one.
6. Look at the result in the running stack before you say it is done. Open
   every dropdown you added and hover what you made clickable.

## Enforced by lint

`bun run lint` (`frontend/eslint.config.mjs`, `no-restricted-syntax`) fails
outside `components/ui/` and `components/common/` on: raw `<button>`,
`<input>`, `<select>`, `<textarea>`, `<datalist>`; `<Input type="file">`;
`onClick` on `div`, `span`, `li`, `p`, `td`, `tr`, `img`, `section`,
`label`. Everywhere, the kit included, on Tailwind palette colours
(`bg-blue-500`) and `cursor-default`. The error names the component to use.
Do not silence it with `eslint-disable`: add the missing kit component.

## Interactive states

Every clickable element in the kit has all four states. Check them when
you add or change a component in `ui/` or `common/`:

| State | Look |
|---|---|
| Rest | `cursor-pointer` (a global rule in `app/globals.css` also covers `button`, `a[href]`, `label[for]` and the ARIA roles switch, checkbox, radio, tab, option, menuitem) |
| Hover | a quiet change: `hover:bg-accent` or `hover:bg-subtle` on rows and buttons, `hover:text-foreground` on grey text, underline on links |
| Keyboard focus | `focus-visible:` ring; fields and selects `border-brand ring-4 ring-brand/15`, buttons `ring-link` |
| Disabled | `disabled:` or `data-disabled:` `cursor-not-allowed` and `opacity-50`/`60`; menu items `pointer-events-none` |

Base UI draws some controls on a `<span>` or `<div>` (switch, menu item,
list option): give the element its role through the Base UI part, not by
hand. Never `cursor-default` (shadcn copies have it on menu items: replace
it with `cursor-pointer`).

## Catalogue

Paths are under `frontend/src/components/`.

### Form controls

| Need | Component |
|---|---|
| Label, control, hint, info tooltip | `common/form-field.tsx` `FormField` |
| Text, number, password, e-mail | `ui/input.tsx` `Input` |
| Long text | `ui/textarea.tsx` `Textarea` |
| Pick one of a short list | `common/option-select.tsx` `OptionSelect` (`options`, `placeholder`; without `required` the placeholder item clears the choice) |
| Pick one of a long list, with search | `common/searchable-select.tsx` `SearchableSelect`; `CurrencySelect`, `TimeZoneSelect` |
| Pick a person | `common/person-picker.tsx` `PersonPicker` (`variant="field"` in forms) |
| Free text with suggestions | `common/suggest-input.tsx` `SuggestInput` |
| Yes/no setting in a form | `common/switch-field.tsx` `SwitchField`; a bare `ui/switch.tsx` `Switch` with a `Label` only in a header or a table |
| Tick items in a list | `ui/checkbox.tsx` `Checkbox` |
| Pick one of 2-4 options with an explanation each | `common/choice-cards.tsx` `ChoiceCards` |
| Filter with 2-5 options | `common/segmented.tsx` `Segmented` |
| Search box over a list | `common/search-input.tsx` `SearchInput` |
| File in a form (CSV, JSON) | `common/file-drop.tsx` `FileDrop` (drop or click; `fileName` shows the choice) |
| Button that picks a file ("Upload") | `common/file-button.tsx` `FileButton` (Button props, `accept`, `onFile`) |

All field triggers (`OptionSelect`, `SearchableSelect`, `PersonPicker`)
take their classes from `ui/field-styles.ts`: `fieldTriggerClass` for the
closed field, `listPopupClass` and `listItemClass` for the open list. A new
picker uses the same three constants.

### Actions and links

| Need | Component |
|---|---|
| Any button | `ui/button.tsx` `Button`; `buttonVariants(...)` on a `Link` or `<a>`. Red action: `variant="destructive"`; quiet "Start over": `variant="link-muted"` |
| Link inside a sentence, "See all" | `common/links.tsx` `TextLink` (`external` for other sites; `tone="muted"` for a quiet "Skip") |
| Name of a person or app in a table or list | `common/links.tsx` `RecordLink` (underline on hover) |
| Button that opens another service | `common/links.tsx` `ExternalLinkButton` |
| Button that opens a panel page (Add, Edit, Onboard) | `common/links.tsx` `LinkButton` (`disabled` draws a disabled button) |
| Active filter with an x | `common/links.tsx` `FilterChip` |
| Copy a value | `common/copy-button.tsx` `CopyButton`, `CopyField` |
| Row menu "..." | `data-table/row-actions.tsx` |
| Confirm a risky action | `common/confirm-dialog.tsx` |

### Layout and content

| Need | Component |
|---|---|
| Page title | `common/page-header.tsx` `PageHeader`, `DetailHeader` |
| Block heading outside a frame | `common/page-header.tsx` `SectionHeader` (`meta` for a count) |
| Any framed block | `common/panel.tsx` `Panel` (`title`, `meta`, `actions`, `footer`, `tone="muted"`); `PanelFooter` for the grey bar |
| Settings card | `settings/settings-section.tsx` `SettingsSection` (`footer`), `SettingsFooter` inside a form |
| Brand pattern (decoration) | `common/strings.tsx` `Strings`: animated strings behind content (`shape`: `STRINGS_SWEEP` full page, `STRINGS_BAND` card or banner); used on the sign-in pages, the setup checklist and `EmptyState`. Mask it away from text (`mask-[...]`) |
| Theme switch outside the panel | `layout/theme-toggle.tsx` `ThemeSwitch`; in the user menu `ThemeSubmenu` |
| Table | `data-table/data-table.tsx` `DataTable`; `common/table-shell.tsx` `Pager` |
| Facts across a detail page | `common/stat.tsx` `StatStrip`, `Stat` (`info`) |
| Label and value rows | `common/detail-list.tsx` `DetailList` |
| Numbered setup steps | `common/steps.tsx` `Steps`, `Step` (`state`: todo, active, running, done, failed) |
| Create or edit form (any length) | `common/form-page.tsx` `FormPage`: its own route (`/apps/new`, `/people/<id>/edit`), never a side sheet or a dialog |
| Short yes/no question | `common/confirm-dialog.tsx` `ConfirmDialog` |

### States and messages

| Need | Component |
|---|---|
| Error, warning, success, hint box | `common/notice.tsx` `Notice` (`tone`), `InlineError` |
| Nothing to show | `common/empty-state.tsx` `EmptyState`, `NotAvailable` |
| Loading, query errors | `common/query-state.tsx`; `common/spinner.tsx` `Spinner` |
| Status of a record | `common/status-badge.tsx` `StatusBadge`, `TONE_DOT`, `TONE_TEXT` |
| Explanation behind an icon | `common/info-tip.tsx` `InfoTip`, `Hint` |
| Toast after an action | `sonner` `toast` |

## Forms are pages

Every create and edit form has its own address, so a person can share it and
an AI agent that drives the browser can open it, read it and see where it
landed after saving.

- The route is the record path plus a verb: `/apps/new`,
  `/apps/<id>/accounts/new`, `/apps/<id>/connection/edit`, `/people/new`,
  `/people/import`, `/people/<id>/edit`, `/people/<id>/onboard`.
- The button that opens it is a `LinkButton`, not a state toggle.
- The view renders `FormPage` with `backHref` (Cancel and the back link) and,
  after a successful save, `router.push` to the record or to the place the
  work continues (`/actions?batch=` after onboarding).
- A page under a record loads it itself (`useApp(id)`, `PersonQuery`), so the
  address works when opened directly.
- Dialogs are only for short questions without fields (`ConfirmDialog`,
  revealing a secret once).

## Look in one paragraph

Vercel's dashboard (Geist tokens, copied on 24.11.2026): pure greys, a
light grey page (`bg-page`, #fafafa; dark #000) with white cards and
controls (dark #0a0a0a), 6 px corners (`rounded-lg`), `shadow-card` under
every card. Two line colours, as in Vercel's dark theme: a card's outline is
`border-frame` (#ebebeb / #2e2e2e), dividers inside it and under the page
bar are the default `border` (#ebebeb / #1f1f1f); fields and outline
buttons use `border-input`. Card footers and table heads are `bg-subtle`
(#fafafa / #000), row hover is `bg-subtle` / `dark:bg-muted`. Text #171717, secondary `muted-foreground` #4d4d4d, third level
`faint` #8f8f8f (placeholders), links `text-link` (violet `brand-ink`).
The brand violet #7c5cff is the only colour accent, in small doses: field
focus, checked checkbox, switch and choice card, the active sidebar item
(`brand-soft` fill, violet icon), the active line tab, progress bars, link
underlines, text selection. Primary buttons stay black. Body text 14 px
(`text-sm`), hints 12-13 px. Controls are 36 px high (`h-9`, buttons
`size="sm"` 32 px, `size="lg"` 40 px). A page starts with a full-width bar
(`PageHeader`: title centred, 14 px, actions right; `DetailHeader`).
Settings pages put their cards in the centred `SETTINGS_COLUMN` (914 px);
Settings sits last in the sidebar and opens its sub-pages under it
(`NAV_SETTINGS`, `children`). Settings are cards with a title (20 px), a
description and a grey footer with the action (`SettingsSection`,
`SettingsFooter`). Sign-in pages and the first run: one centred card under
the logo, theme switch top right (`AuthShell`, `AuthCard`). No icon in a
tinted tile, no card inside a card. More in `pages.md`, "Look rules".

## Phones

Check every new screen at 390 px. The page must not scroll sideways.

- Tables keep the identifying column, the status and the row actions; every
  other column gets `max-md:hidden` in its `meta.className` (or on
  `TableHead` and `TableCell`). The main text column takes the free width
  and truncates: `meta: { className: "w-full max-w-0 min-w-28" }`.
- `PageHeader` is a plain title row on phones (the mobile bar above holds the
  menu); filters (`Segmented`) and tabs scroll sideways instead of widening
  the page.
- Secondary button labels may hide on phones (`<span className="max-md:sr-only">`)
  when the icon says enough; keep a `title`.

## Loading and motion

Navigation must feel calm: no grey flash, nothing that pops.

- `layout/page-transition.tsx` (`PageTransition`, in `AdminLayout`) wraps
  the page outlet in a React `ViewTransition` keyed by the pathname: on a
  route change the old page fades out (140 ms, slight blur) and the new one
  settles in from 98 % scale and blur (320 ms). CSS `page-exit`,
  `page-enter` in `globals.css`; reduced motion turns it off. Query string
  changes (tabs, filters) keep the key and do not animate. A `flushSync`
  while the transition prepares makes React skip it (console warning).
  `animate-page-in` (4 px rise) is left for the sign-in card.
- The page frame (header, tabs) renders at once; only the data waits.
  Load data through `QueryState` and give it a skeleton in the shape of
  the content: `loading={<TableSkeleton rows={n} />}` for a table,
  `loading={<DetailPageSkeleton stats tabs />}` for a detail page
  (`common/page-skeletons.tsx`); the default is plain `LoadingRows`. The
  skeleton shows at once with a 160 ms fade (`animate-skeleton-in`).
  Data that had to load fades in (`animate-content-in`); data from the
  cache shows at once.
- Lists with filters, search or pages use `placeholderData: keepPreviousData`
  in their hook, so the old rows stay while the new ones load.
- Render the page header and the toolbar outside `QueryState`, so they
  stay still while the data loads.
- Popups, dialogs and sheets animate through their `ui/` components. Do not
  add other motion; the utilities live at the end of `app/globals.css` and
  turn off under `prefers-reduced-motion`.

## How to add a component

1. Look for it in shadcn first: `bunx shadcn@latest view <name>` shows the
   base-nova (Base UI) source. Do not run `shadcn add` without `--dry-run`:
   it overwrites the customised `button`, `input` and `input-group`. Copy
   the file by hand and replace its icon placeholders with Lucide icons.
2. Restyle it to the look above, with tokens and `ui/field-styles.ts`.
3. Put a one-line doc comment on the export: what it is for and when to use
   another component instead.
4. Add it to the catalogue in this file in the same change.
