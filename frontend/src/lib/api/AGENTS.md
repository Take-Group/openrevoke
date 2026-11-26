# open-revoke/frontend/src/lib/api/

The only place that talks HTTP to the API, plus the response types, written by hand from `docs/openapi.json` (update them in the same change as a contract change). Hooks in `src/hooks/` call `apiGet` and `apiSend`.

- `client.ts`: `apiFetch` (same-origin `/api/...`, sets header `CLIENT_HEADER` `X-Open-Revoke-Client`, which the API requires on POST, PATCH and DELETE; 204 gives `undefined`), `apiGet(path, params)`, `apiSend(method, path, body)`, `buildQuery`, `ApiError` (`status`, `detail`, `unauthorized`, `notImplemented`), `errorMessage`, `isNotImplemented`.
- `types.ts`: main contract types (`Page<T>`, `MoneyAmount`, people, apps, accounts, connections, actions, audit, dashboard, currencies). Near the 600-line limit: put new groups in a separate `*-types.ts`.
- `auth-types.ts`: sign-in, sign-up, users, invites and the organization (`UserRole`, `UserStatus`, `UserOut`, `AuthState`, `OrganizationSettingsOut`, `SignupRequest`, `SignupResult`, `ResetLinkOut`, ...).
- `api-token-types.ts`: API tokens and the MCP URL (`ApiTokenScope`, `ApiTokenOut`, `ApiTokenList`, `ApiTokenCreate`, `ApiTokenCreated`).
- `me-types.ts`: `/api/me` (`MyAccess`, `MyAccount`, `MyRequest`, `RequestableApp`, `RequestOutcome`).
- `ai-types.ts`: AI model settings (`AiProvider`, `AiReasoningEffort`, `AiSettingsOut`, `AiSettingsUpdate`, `AiModelOut`, `AiModelList`, `AiTestResult`).
- `slack-types.ts`: Slack bot setup (`SlackAgentStatus`, `SlackAgentOut`, `SlackAppCreate`, `SlackTokensUpdate`).
- `access-request-types.ts`: access requests (`AccessRequestStatus`, `AccessRequestOut`, `AccessRequestPage`).
- `discovery-types.ts`: app discovery (`DiscoveryOverview`, `DiscoveredAppOut`, `DiscoveredAppDetail`, Google Cloud setup, scan runs).
- `billing-types.ts`: `AppBillingOut` (`AppDetail.billing`: plan and price read from the app's billing).
- `recipe-fix-types.ts`: click recipe fixes (`RecipeFixStatus`, `RecipeFixOut`, `RecipeFixList`; `ActionOut.recipe_fixes`).
- `catalog-types.ts`: app catalog (`CatalogAppOut`, `CatalogAppList`, `CatalogMatchOut`, `CatalogMatchedBy`).
- `system-types.ts`: `SystemVersion` (GET `/api/system/version`).
- `access-profile-types.ts`: access profiles (`AccessProfileOut`, `AccessProfileCreate`/`Update`, drift `AccessDrift`, `PersonAccessDrift`, `AccessProfileMember`, assignment `ProfileAssign`, `MembersAssign`, `ProfileAssignResult`, `PlannedAction`, `ProfileUnassignResult`).
- `onboarding-types.ts`: `/welcome` questions and dashboard checklist (`OnboardingOut`, `PeopleImport`, `ChatPlatform`, `PasswordManager`).
