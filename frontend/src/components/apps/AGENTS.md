# open-revoke/frontend/src/components/apps/

Tracked SaaS apps: list, add, and the detail page with four tabs (accounts, connection, sync, settings). Hooks: `use-apps.ts`, `use-accounts.ts`, `use-connection.ts`, `use-connectors.ts`. Pages: `src/app/apps/page.tsx` (`AppsView`), `src/app/apps/[id]/page.tsx` (`AppDetailView`, `?tab=`, `?accounts=`) and the form pages `/apps/new`, `/apps/new/bulk`, `/accounts/import`, `/apps/[id]/accounts/new`, `/apps/[id]/accounts/bulk`, `/apps/[id]/connection/edit` (`?connector=`). Every create and edit form is its own page (`FormPage`), not a side panel.

- `apps-view.tsx`: `AppsView`: search (debounced), integration, status and category filters, list; links "Import accounts" (`/accounts/import`), "Add several apps" (`/apps/new/bulk`), "Add app" (`/apps/new`). Hooks `useApps`, `useDebouncedValue`.
- `apps-table.tsx`: `AppsTable`: rows with cost, integration and sync state, row menu. Hook `useSyncConnection`.
- `new-app-view.tsx`: `NewAppView` (`/apps/new`): catalog search first (`CatalogAppPicker` fills name, website, connector) or "Add your own app" (website, category, logo); free until priced; goes on to `/apps/[id]/connection/edit?connector=`, the app, or "Add and paste e-mails" (`/apps/[id]/accounts/bulk`). Hooks `useCreateApp`, `useAppLogo`, `useConnectors`, `useAuthState`.
- `bulk-apps-view.tsx`: `BulkAppsView` (`/apps/new/bulk`): grid of catalog apps (found by discovery first, added ones last and disabled) with search, ticked cards plus typed names, one save. Hooks `useCatalogSearch`, `useCreateApps`.
- `app-identity-fields.tsx`: `WebsiteCategoryFields`, `LogoPicker` (preview, Upload, Remove), `logoProblem`, `LOGO_ACCEPT`.
- `paste-accounts-view.tsx`: `PasteAccountsView` (`/apps/[id]/accounts/bulk`): pasted e-mails, Preview, Add (manual apps only). Hooks `useApp`, `usePasteAccounts`.
- `import-accounts-view.tsx`: `ImportAccountsView` (`/accounts/import`): CSV for several apps, "Create missing apps", sample file, Preview, Import. Hook `useImportAccounts`.
- `account-import-preview.tsx`: `AccountImportPreview` (result, showApp): counts, new apps and one row per line.
- `app-detail-view.tsx`: `AppDetailView`, types `AppTab`, `AppDetailViewProps`: header, tabs, "Sync now". Hooks `useApp`, `useSyncConnection`, `useSyncInProgress`.
- `app-accounts-tab.tsx`: `AppAccountsTab`, type `AccountsFilter`: filtered account list of one app; manual apps get "Paste e-mails" and "Add account". Hooks `useAppAccounts`, `useDebouncedValue`.
- `accounts-table.tsx`: `AccountsTable`: account rows, links to people, edit status. Hook `useUpdateAccount`.
- `new-account-view.tsx`: `NewAccountView` (`/apps/[id]/accounts/new`): manual account (manual apps only), back to the app. Hooks `useApp`, `useCreateAccount`.
- `connection-tab.tsx`: `ConnectionTab`: picks `ConnectionCard` or the empty state. Hook `useConnectors`.
- `connection-card.tsx`: `ConnectionCard`: saved connection, state, Check, Edit (link to the form page). Hook `useCheckConnection`.
- `connection-form-view.tsx`: `ConnectionFormView` (`/apps/[id]/connection/edit`, `?connector=` preselects): connector choice, `SchemaFields`, the two switches; back to `?tab=connection`. Hooks `useApp`, `useConnectors`, `useSaveConnection`.
- `schema-fields.tsx`: `SchemaFields`: form built from the connector's JSON Schema `config_schema`.
- `sync-runs-tab.tsx`: `SyncRunsTab`: history of sync runs in a `DataTable`. Hook `useSyncRuns`.
- `app-settings-tab.tsx`: `AppSettingsTab`: logo (saved on pick), name, slug, website, category, price, integration, request policy; delete app. Hooks `useUpdateApp`, `useAppLogo`, `useDeleteApp`.
- `billing-notice.tsx`: `BillingNotice` (app, onApplied): the plan and price read from the app's billing in the settings tab; "Use billing price" when a manual price overrides it. Hook `useUpdateApp`.
- `price-fields.tsx`: `PriceFields`, `PriceForm`, `priceFormFrom`, `priceFromForm`, `DEFAULT_CURRENCY`: price form; free apps send no price.
- `integration-picker.tsx`: `IntegrationPicker`: segmented control of integration types.
- `app-options.ts`: `PRICING_OPTIONS`, `BILLING_OPTIONS`, `integrationOfConnector` (integration implied by a connector's auth kind).
