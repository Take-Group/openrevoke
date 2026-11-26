# open-revoke/frontend/src/hooks/

React Query hooks, one file per API resource; components never `fetch`. Reads: `useQuery` with `apiGet`; writes: `useApiMutation` (invalidates by the first key element plus `dashboard` and `audit`, toasts `detail`): [api-communication.md](../../../skills/frontend/api-communication.md). Add a new key to `ResourceKey` first. Endpoints per resource: `backend/app/api/AGENTS.md`.

- `use-api-mutation.ts`: `useApiMutation({mutationFn, invalidate, success, toastErrors})`, `ResourceKey` union of top-level keys.
- `use-accounts.ts`: `useAppAccounts(appId, params)` key `["accounts", appId, params]`; `useCreateAccount(appId)`, `useUpdateAccount()`, `useImportAccounts()` (`dry_run`, `create_apps`), `usePasteAccounts(appId)` (`/apps/{id}/accounts/bulk`).
- `use-actions.ts`: `useActions(params, enabled)` key `["actions", params]`, polls 2 s while `isMoving`; `useCreateAction`, `useActionTransition(approve | cancel | complete | retry | by-hand)`, `useApproveBatch` (warns about apps with writes off), `useRevealSecret` (one-time, does not refresh the list).
- `use-access-requests.ts`: `useAccessRequests(params, enabled)` key `["access-requests", params]`; `useAccessRequest(id)`; `useDecideAccessRequest(id, approve | reject)`; `accessRequestsExportUrl(filters)` (CSV link).
- `use-access-profiles.ts`: all under `["access-profiles", ...]`: `useAccessProfiles`, `useAccessProfile(id)`, `useAccessProfileMembers(id)`, `useAppRoleSuggestions` (Map app id to roles), `usePersonAccessProfiles`, `usePersonAccessDrift`; `useCreateAccessProfile`, `useUpdateAccessProfile`, `useDeleteAccessProfile`, `useAssignPersonProfiles(personId)` and `useAssignProfileMembers(profileId)` (also `dry_run` previews, no toast), `useUnassignPersonProfile`, `useCreateRemovals` (one `delete_account` action per suggested removal).
- `use-ai-settings.ts`: `useAiSettings` key `["ai-settings"]`; `useSaveAiSettings`, `useAiModels` (Connect, no toast), `useSavedAiModels`, `useTestAi`.
- `use-api-tokens.ts`: `useApiTokens` key `["api-tokens"]`; `useCreateApiToken`, `useRevokeApiToken`.
- `use-apps.ts`: `useApps(params)` key `["apps", params]` (`categories`, filter `category`); `useApp(id)` key `["app", id]`; `useCreateApp`, `useCreateApps` (bulk), `useAppLogo()` (PUT/DELETE logo), `useUpdateApp(id)`, `useDeleteApp(id)`.
- `use-audit.ts`: `useAudit(params)` key `["audit", params]`, filters `q`, `entity_type`, `entity_id`, `event`, `app_id`, `person_id`; `auditExportUrl(filters, csv | jsonl)` (download link).
- `use-auth.ts`: `useAuthState` key `["auth"]` (who is signed in, setup needed, organization); `useSetup`, `useLogin`, `useRegister` (enter the panel on `done`), `useVerifyTotp`, `useSkipTotp`, `useEnterPanel`, `useStartTwoFactor`, `useSetTwoFactor`, `useSignup`, `useResetPassword`, `useChangePassword`, `useLogout`, all with `meta.authFlow` (a 401 does not reset the state); `useInviteInfo(token)`, `useSetupTokenCheck(token)`, `useRestartAtLogin()`. Sign-in and logout clear every cache except `auth`.
- `use-browser.ts`: `useBrowserState` key `["browser"]` (polls 15 s, not after a 4xx); `useOpenInBrowser`.
- `use-catalog.ts`: `useAppCatalog()` key `["catalog"]` (public, never stale): lookup by catalog slug or app name (`keys`); `useCatalogSearch(q, limit, enabled)` key `["apps", "catalog-search", ...]` (refreshed with apps).
- `use-connection.ts`: `useSaveConnection(appId)`, `useCheckConnection`, `useSyncConnection`; `useSyncRuns(appId)` key `["sync-runs", appId]` (polls 3 s while `running`); `useSyncInProgress(appId)`: boolean, refetches apps, accounts and people when the sync ends.
- `use-connectors.ts`: `useConnectors` key `["connectors"]` (config schema for the connection form).
- `use-currencies.ts`: `useCurrencies` key `["currencies"]` (public, stale 10 min); `useRefreshRates` refetches every list with costs.
- `use-dashboard.ts`: `useDashboard` key `["dashboard"]`.
- `use-debounced-value.ts`: `useDebouncedValue(value, delay = 300)` for search inputs.
- `use-me.ts`: `useMyAccess` key `["me", "access"]`; `useRequestAccess`; `useMyTeam`; `useMyApprovals(params)` (`pending`, `has_reports` for the sidebar); `useMyApproval(id)`; `useDecideMyApproval(id, approve | reject)`.
- `use-discovery.ts`: `useDiscovery` key `["discovery", "overview"]` (polls 3 s while `scan_running`, then refetches people and apps); `useDiscoveredApps(params)`, `useDiscoveredApp(id)`, `usePersonDiscoveredApps`; `useScanNow`, `useConnectDiscoverySource`, `useStartGoogleOAuth`, `useGoogleCloudSetup` (polls), `useStartGoogleCloudSetup`, `useUpdateDiscoveredApp`, `useTrackDiscoveredApp` (`create_accounts`); `useGoogleOAuthResult()` reads `?google=`/`?google_error=` once after the redirect.
- `use-mobile.ts`: `useIsMobile()` true below 768 px.
- `use-onboarding.ts`: `useOnboarding` key `["onboarding"]` (first-run answers, checklist); `useSaveOnboardingChoices`, `useDismissOnboarding`.
- `use-people.ts`: `usePeople(params, enabled)` key `["people", params]`; `usePerson(id)` key `["person", id]`; `useCreatePerson`, `useUpdatePerson(id)`, `useSetPersonKind(id)`, `useImportPeople` (`dry_run`), `useOffboardPerson(id)`, `useOnboardPerson(id)` (create actions), `useDeletePerson(id)`.
- `use-recipe-fixes.ts`: `useRecipeFixDecision("approve" | "reject")`.
- `use-slack-agent.ts`: `useSlackAgent` key `["slack-agent"]` (polls 3 s while `connecting`), setup mutations.
- `use-system.ts`: `useSystemVersion` (admins).
- `use-url-tab.ts`: `useUrlTab(initial, fallback, param = "tab")`: state mirrored in a query param (`?tab=`, `?step=` on /welcome) with `history.replaceState`, no navigation; the fallback drops the param; the page reads it on the server and passes `initial`.
- `use-users.ts`: `useUsers` key `["users"]`; `useInvites(enabled)` key `["invites"]`; `useCreateInvite`, `useRevokeInvite`, `useApproveUser`, `useCreateResetLink`, `useUpdateUserRole`, `useResetUserTotp`, `useRemoveUser`; `useOrganizationSettings` key `["organization"]`; `useUpdateOrganization(success)` (refreshes cost views).
