# open-revoke/frontend/src/components/discovery/

Google Workspace discovery: connect Google (three ways), scan, review the SaaS apps people signed in to. Hooks: `use-discovery.ts`, `use-browser.ts`. Pages: `src/app/discovery/page.tsx` (`DiscoveryView`) and `src/app/discovery/[id]/page.tsx` (`DiscoveredAppView`).

- `discovery-view.tsx`: `DiscoveryView`: no source shows `DiscoverySetup`, else scan status and the apps table; handles the Google OAuth result in the URL. Hooks `useDiscovery`, `useDiscoveredApps`, `useScanNow`, `useGoogleOAuthResult`, `useDebouncedValue`.
- `discovery-setup.tsx`: `DiscoverySetup`: first run, what a scan reads, then a choice of the three setups.
- `google-auto-setup.tsx`: `GoogleAutoSetup`: Open Revoke clicks through Google Cloud in the shared browser, shows `LiveView`. Hooks `useStartGoogleCloudSetup`, `useGoogleCloudSetup`, `useBrowserState`.
- `google-oauth-setup.tsx`: `GoogleOAuthSetup`: guided steps with console links, then client ID and secret. Hook `useStartGoogleOAuth`.
- `service-account-setup.tsx`: `ServiceAccountSetup`: service account key with domain-wide delegation. Hook `useConnectDiscoverySource`.
- `scan-status.tsx`: `ScanStatus`: one line on the last scan and what to fix.
- `discovered-apps-table.tsx`: `DiscoveredAppsTable`: found apps with review actions.
- `discovered-app-view.tsx`: `DiscoveredAppView`: one found app and its grants. Hook `useDiscoveredApp`.
- `grants-table.tsx`: `GrantsTable`: who granted the app access, links to `/people/[id]`.
- `review-actions.tsx`: `ReviewActions`: track as app (with `activeSignIns`, on the detail page, a switch also adds accounts for those people), ignore, undo. Hooks `useTrackDiscoveredApp`, `useUpdateDiscoveredApp`.
