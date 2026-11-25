# open-revoke/frontend/src/components/layout/

The frame around every page: sidebar, phone top bar, command palette, theme switch. Navigation is defined once in `nav-items.ts`; the sidebar and the palette both read it.

- `address-warning.tsx`: `AddressWarning`, a `Notice` shown when the browser address differs from the server's `public_url` (or is not local).
- `update-notice.tsx`: `UpdateNotice`, admins only: a `Notice` when a newer stable release exists (`useSystemVersion`), warning tone for a security release, copy button for `open-revoke update`.
- `admin-layout.tsx`: `AdminLayout` (children, defaultOpen) used in the root layout; `MobileBar` on phones, `FULL_WIDTH_PAGES` (only `/browser`) skip the content width limit.
- `app-sidebar.tsx`: `AppSidebar` (onSearch): logo, search button, `NAV_*` groups, alert count badge from `useDashboard`, `NavUser`; a `user` gets only `NAV_USER`, no search. Settings sub-pages open under it.
- `brand-mark.tsx`: the logo (door with a violet line, OpenRevoke wordmark as paths): `BrandMark` (door), `BrandName` (wordmark), `BrandWordmark` (both). Colour `--brand` in `globals.css`.
- `command-menu.tsx`: `CommandMenu` (open, onOpenChange), the Cmd-K palette: pages (`NAV_PAGES`, settings sub-pages too), people (server search), apps, theme. Mounted only while open.
- `nav-items.ts`: `NavItem`, `NAV_MAIN`, `NAV_TOOLS`, `NAV_SETTINGS` (with `children`), `NAV_ALL`, `NAV_PAGES` (items plus sub-pages, for the palette), `NAV_USER` (the whole sidebar of a `user`), `isActive`, `isItemActive`. Add a page to the sidebar here.
- `page-transition.tsx`: `PageTransition`, mounted by `AdminLayout` around the page outlet: a React `ViewTransition` keyed by the pathname fades the old page out and settles the new one in (`page-exit`, `page-enter` in `globals.css`); query-string changes (tabs, filters) do not animate.
- `nav-user.tsx`: `NavUser`, the signed-in user menu (account, organization, users, sign out, Open Revoke version for admins) via `useAuthState`, `useLogout`, `useSystemVersion`.
- `theme-toggle.tsx`: `THEMES`, `ThemeSubmenu` (inside a dropdown), `ThemeSwitch` (standalone, used on auth pages).
