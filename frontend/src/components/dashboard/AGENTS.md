# open-revoke/frontend/src/components/dashboard/

The home page (`/`). `DashboardView` loads one `useDashboard` query and lays out the blocks below it; all are specific to this page.

- `alerts-list.tsx`: `AlertsList` (alerts sorted critical first) and `alertHref` which maps an `Alert.kind` to the page that fixes it. Add a new alert kind there (the switch is exhaustive).
- `apps-by-cost.tsx`: `AppsByCost` (totals, total): monthly cost per app with a share bar, in organization currency when converted, else in the app's own.
- `dashboard-view.tsx`: `DashboardView`: `PageHeader`, `SetupChecklist`, then `QueryState` with `KpiCards`, `AlertsList`, `AppsByCost`.
- `kpi-cards.tsx`: `KpiCards` (data) top strip of figures (label, value, caption).
- `row-hover.ts`: `ROW_HOVER` hover and focus tint for clickable rows, same as `DataTable`.
- `setup-checklist.tsx`: `SetupChecklist` first-steps card for admins from the welcome answers (`useOnboarding`, `useDismissOnboarding`); state comes from data and hides when done or dismissed.
