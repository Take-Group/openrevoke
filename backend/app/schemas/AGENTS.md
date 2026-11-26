# open-revoke/backend/app/schemas/

Pydantic request/response models of the panel API, one file per router in `app/api/` (same name unless noted). They define `docs/openapi.json`, which is the panel's contract. All inherit `ApiModel`.

- `__init__.py`: empty.
- `common.py`: `ApiModel` (base), `MoneyAmount`, refs `AppRef`, `PersonRef`, `AccountRef`, `ErrorResponse` (used by `api/errors.py`).
- `auth.py`: `api/auth.py` and `api/users.py` organization: `UserOut`, `OrganizationOut`/`OrganizationSettingsOut`/`OrganizationUpdate` (`EmailDomains`), `AuthState`, `SetupRequest` (with `token`), `SetupTokenCheck`, `LoginRequest`, `RegisterRequest`, `SignupRequest`/`SignupResult`, `AuthStep` (+ `AuthStepKind`, `TotpEnrollment`), `TotpRequest`, `TotpSkipRequest`, `InviteInfo`, `ResetPasswordRequest`, `ChangePasswordRequest`, `DevPrefill`.
- `users.py`: `api/users.py`: `InviteCreate`, `InviteOut`, `InviteCreated`, `InviteList`, `UserUpdate`, `ResetLinkOut`.
- `api_tokens.py`: `api/api_tokens.py`: `ApiTokenOut`, `ApiTokenList` (with `mcp_url`), `ApiTokenCreate`, `ApiTokenCreated` (the token once).
- `me.py`: `api/me.py`: `MyAccess` (`MyAccount`, `MyRequest`, `RequestableApp`), `MyAccessRequestCreate`, `MyAccessRequestResult`, `MyTeam` (`TeamMember`).
- `access_requests.py`: `api/access_requests.py`, `api/me.py` approvals: `AccessRequestOut`, `AccessRequestDetail` (decisions, action, seat cost), `AccessRequestDecisionOut`, `AccessRequestActionOut`, `AccessRequestPage`, `AccessRequestDecisionCreate`, `MyApprovals`, `WaitingFor`.
- `people.py`: `api/people.py`: `PersonCreate`, `PersonUpdate`, `PersonListItem`, `PersonPage`, `PersonDetail` (with `AliasOut`, `PersonSourceOut`, `PersonAccountOut`).
- `people_import.py`: POST `/people/import`: `ImportResult`, `ImportRowResult`, `ImportRowAction`, `FieldChange`.
- `apps.py`: `api/apps.py`: `AppCreate`, `AppUpdate`, `AppListItem`, `AppPage`, `AppDetail`, `PriceIn`/`PriceOut`.
- `accounts.py`: `api/accounts.py` and `/apps/{id}/accounts`: `AccountOut`, `AccountPage`, `AccountCreate`, `AccountUpdate`.
- `connections.py`: `api/connections.py`: `ConnectionOut`, `ConnectionUpsert`, `ConnectionCheckResult`, `SyncRunOut`, `SyncRunPage`, `ConnectorOut`, `ConnectorPage`.
- `actions.py`: `api/actions.py` plus on/offboarding in `api/people.py`: `ActionCreate`, `ActionOut`, `ActionPage`, `ActionList`, `ActionPayload`, `BatchApproveResult`, `NotApproved`, `ActionSecret`; `OffboardResult`/`OffboardSkipped`, `OnboardRequest`/`OnboardApp`/`OnboardResult`/`OnboardSkipped`; enums `WriteKind`, `WriteMode`.
- `recipe_fixes.py`: `api/recipe_fixes.py` and `ActionOut.recipe_fixes`: `RecipeFixOut`, `RecipeFixList`.
- `discovery.py`: `api/discovery.py`, `api/google_oauth.py`: `DiscoveryOverview` (`DiscoverySource`, `DiscoveryConnector`, `DiscoveryCounts`), `DiscoverySourceCreate`, `ScanRunOut`/`ScanRunPage`, `DiscoveredAppOut`/`Page`/`Detail`/`Update`/`Track`, `DiscoveredGrantOut`, `GoogleOAuthStart`/`StartOut`, `PersonDiscoveredAppPage`; `GrantRisk`.
- `google_cloud_setup.py`: `api/google_cloud_setup.py`: `GoogleCloudSetupOut`, `GoogleCloudSetupStart`, `SetupStepOut`, enums `SetupStatus`, `SetupStep`, `StepState`.
- `dashboard.py`: GET `/dashboard`: `Dashboard`, `DashboardCounts`, `Alert` (`AlertKind`, `AlertSeverity`, `AlertEntityType`).
- `setup_checklist.py`: `api/setup_checklist.py`: `OnboardingOut`, `OnboardingChoices`, `ChecklistItem`.
- `browser.py`: `api/browser.py`: `BrowserState`, `BrowserTab`, `BrowserApp`, `BrowserPolicyOut`, `BrowserOpenRequest`.
- `audit.py`: `api/audit.py`: `AuditEventOut`, `AuditEventPage`.
- `ai.py`: `api/ai.py`: `AiSettingsOut`, `AiSettingsUpdate`, `AiProviderOut`, `AiModelsRequest`, `AiModelOut` (id, name, efforts), `AiModelList`, `AiTestResult`.
- `slack_agent.py`: `api/slack_agent.py`: `SlackAgentOut`, `SlackAgentUpdate`, `SlackAppCreate`, `SlackTokensUpdate`, `SlackOAuthStart`.
- `catalog.py`: `api/catalog.py`: `CatalogAppOut`, `CatalogAppList`, `CatalogMatchOut` (also in discovered apps).
- `currencies.py`: `api/currencies.py`: `CurrencyList`, `ExchangeRatesInfo`.
- `system.py`: `api/system.py`: `SystemVersion`.
