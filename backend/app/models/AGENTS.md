# open-revoke/backend/app/models/

SQLAlchemy models. A change needs an Alembic revision in `../../migrations/versions/` (skill `skills/backend/new-model.md`). One class per file. Ids are UUIDs, except singleton rows with `id = 1`. Enums are stored as strings.

- `__init__.py`: re-exports every model (`__all__`); import a new model here so the tables get created.
- `columns.py`: shared column helpers (UUID key, timestamps, enum column, `MONEY` = Numeric(12,2)).
- `enums.py`: all `StrEnum`s (`PersonStatus`, `Integration`, `ConnectionStatus`, `AccountStatus`, `ActionKind`, `ActionStatus`, `ActionReason`, `UserRole`, `UserStatus`, `UserTokenKind`, `AccessRequestChannel`, `SelfServicePolicy`, `AiProvider`, `AiReasoningEffort`, ...), also used by schemas and services.
- `person.py`: `Person` (`person`): employee or service account (`kind`); parent of `PersonEmail`, `PersonLink`, `Account`.
- `person_email.py`: `PersonEmail` (`person_email`): alias e-mail, FK `person`.
- `person_link.py`: `PersonLink` (`person_link`): where a person is known from; `source_id` points to `people_source` or `connection` (no FK); unique per source and external id.
- `people_source.py`: `PeopleSource` (`people_source`): manual and CSV sources without a connector.
- `app.py`: `App` (`app`): a SaaS tool with its price; has one `Connection`, many `Account`.
- `app_billing.py`: `AppBilling` (`app_billing`): plan and price the app's own billing reports (one row per app, PK `app_id`); `applies_to_price` makes each read set the app's price.
- `connection.py`: `Connection` (`connection`): connector, config, encrypted secrets; FK `app` (unique, CASCADE); `is_people_source` flag.
- `account.py`: `Account` (`account`): a user seat in an app; FK `app` (RESTRICT), `connection`, `person` (both SET NULL); unique (`app_id`, `external_id`).
- `action.py`: `Action` (`action`): create/delete account or manual task; FK `person`, `app`, `account`.
- `action_screenshot.py`: `ActionScreenshot` (`action_screenshot`): PNG where a click recipe stopped, PK and FK `action` (CASCADE); a retry deletes it.
- `recipe_fix.py`: `RecipeFix` (`recipe_fix`): local fix of one click recipe step (`recipe_app`, `recipe_action`, `step_id`, `within`/`target` locators with `{{param}}`), `status` proposed/active/rejected (`RecipeFixStatus`), author `ai:<model>`; FK `action` (SET NULL).
- `access_request.py`: `AccessRequest` (`access_request`): a request for an app account from Slack or the panel (`channel`); FK `person`, `app`, `action`.
- `sync_run.py`: `SyncRun` (`sync_run`): one account sync of a connection; FK `connection`.
- `scan_run.py`: `ScanRun` (`scan_run`): one discovery scan of an identity provider; FK `connection`.
- `discovered_app.py`: `DiscoveredApp` (`discovered_app`): third-party app found by a scan; FK `connection`, optional `app`; unique (`connection_id`, `key`).
- `discovered_grant.py`: `DiscoveredGrant` (`discovered_grant`): a user who signed in to a discovered app, matched to people by e-mail at read time; FK `discovered_app`.
- `user.py`: `User` (`panel_user`): panel sign-in user, separate from `Person`; `role` admin or user, `status` (pending after self sign-up, else active).
- `user_session.py`: `UserSession` (`user_session`): cookie session (stores token SHA-256); FK `panel_user`, joined-loaded `user`.
- `user_token.py`: `UserToken` (`user_token`): invite or password-reset link (SHA-256 only); FK `panel_user`.
- `audit_event.py`: `AuditEvent` (`audit_event`): append-only change log; never update or delete rows.
- `organization.py`, `ai_settings.py`, `slack_agent.py`: singleton rows (`id = 1`): `Organization` (`organization`, first-run setup and sign-up rules), `AiSettings` (`ai_settings`, provider, key, model, reasoning effort), `SlackAgent` (`slack_agent`, Fernet-encrypted tokens).
- `exchange_rate.py`: `ExchangeRate` (`exchange_rate`): daily rate per currency, units per 1 EUR.
