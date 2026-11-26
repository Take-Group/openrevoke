# Skill: Domain model, account matching and costs

## What it does

People, apps, accounts in apps, write actions and the audit log. The API contract is stored in `docs/openapi.json`,
and the frontend takes its types from it.

## Files

| File | What it does |
|---|---|
| `backend/app/models/enums.py` | all enums |
| `backend/app/models/columns.py` | UUID PK, `timestamptz`, `numeric(12,2)`, enum as varchar with CHECK |
| `backend/app/models/<table>.py` | one model per file: `person`, `person_email`, `app`, `connection`, `people_source`, `person_link`, `account`, `sync_run`, `action`, `audit_event` |
| `backend/app/db/`, `backend/migrations/` | Alembic migrations: `python -m app.db migrate` / `reset`, development data in `seed.py` (`skills/backend/new-model.md`) |
| `backend/app/services/matching.py` | e-mail normalization, `EmailIndex`, `resolve_match`, `match_email` |
| `backend/app/services/billing.py` | price from the app's billing (`app_billing`): sets the app price until an admin enters a different one by hand |
| `backend/app/services/costs.py` | pure cost functions: seat, app, sum per currency; conversion to the organization currency: `skills/backend/exchange-rates.md` |
| `backend/app/services/accounts.py` | accounts: list, manual account, assignment, `rematch_accounts`, `unassigned_clause` |
| `backend/app/services/people.py`, `people_import.py`, `people_sources.py` | people, aliases, CSV import, sources and `person_link` |
| `backend/app/services/people_managers.py`, `people_import_managers.py` | reporting lines: `set_manager`, `creates_cycle`, reports, `needs_manager_clause`; manager column of the CSV import |
| `backend/app/services/apps.py` | apps, `seat_stats` (accounts, seats, without an owner) |
| `backend/app/services/actions.py`, `offboarding.py`, `onboarding.py`, `capabilities.py` | actions, status transitions, offboarding, onboarding; execution and verification: `skills/backend/actions.md` |
| `backend/app/services/access/profiles.py` and `profile_*.py` | access profiles: apps with roles, assignment, drift (`skills/backend/access-profiles.md`) |
| `backend/app/services/dashboard.py` | counts, monthly cost, alerts (also `profile_access_missing` per access profile) |
| `backend/app/services/audit.py` | `record()`: every write appends an `audit_event` (actor `local`, `app_id`, `person_id`) |
| `backend/app/services/presenters.py` | builds response schemas from models |
| `backend/app/services/errors.py`, `backend/app/api/errors.py` | domain errors and their mapping to 404, 409, 400 |
| `backend/app/schemas/*.py`, `backend/app/api/*.py` | Pydantic schemas and routers under `/api` |
| `backend/scripts/export_openapi.py` | dump of the OpenAPI schema |

## Rules in the code

- **A router only calls a service.** The service raises `NotFoundError`,
  `ConflictError` or `InvalidInputError`. The handler in `api/errors.py` returns
  `{"detail": "..."}` with code 404, 409 or 400. Schema validation errors
  stay in the FastAPI format (422).
- **The session** commits in `get_session` after a successful request. Services
  only call `flush()`.
- **Person or technical account** (`person.kind`): people from a source (Google)
  get a type from the rules in `services/person_kind.py` (a generic address such as
  `kontakt@`, an address with a digit and a name that does not look like a person, words in the name,
  never signed in during the last 30 days), with the reason in `kind_reason`. Sync checks
  the rule on every run while `kind_source = auto`. `PATCH
  /api/people/{id}` with `kind` sets `manual`, and sync no longer changes it.
  A person added by hand is `manual`. `GET /api/people?kind=` filters,
  `kind_counts` gives the counts for the tabs. The dashboard counts only `human`.
- **Manager, department, job title** (`person.manager_id`, `manager_source`,
  `department`, `job_title`). Sources: a people source (`RemotePerson.manager_email`,
  `department`, `job_title`; Google `relations` and `organizations`), the CSV
  import (`manager_email`, `department`, `job_title`) and `PATCH
  /api/people/{id}` (`manager_id`, `department`, `job_title`).
  - `manager_source = auto`: the sync's second pass (after every person of the
    list is stored) sets the manager from the source's e-mail (primary or
    alias); no manager or an unknown e-mail clears it. `manual` (PATCH, also
    `null`, and every manager set by the CSV import) is never changed by a sync.
  - Nobody is their own manager and the chain above a person never leads back
    to them (`creates_cycle`): PATCH and CSV give 400 or a row error, the sync
    ignores such a manager. PATCH also refuses a manager who left or is a
    service account.
  - Department and job title from a source replace the stored values on every
    sync; an empty value in the source keeps them (no source flag column).
  - `GET /api/people?no_manager=true` lists people with no manager; `q` also
    matches department and job title. `PersonListItem` has `manager`
    (`PersonRef`), `manager_source`, `department`, `job_title`; `PersonDetail`
    adds `reports`.
  - Dashboard alert `people_without_manager` (count, link
    `/people?no_manager=true`): only while an app has `request_policy`
    `manager` or `manager_then_admin`; counts active `human` people with no
    manager who manage nobody (the top of a reporting line is not missing data).
- **E-mails** in the database have `strip()` and `lower()` applied (CHECK in `person`
  and `person_email`). An e-mail, primary or alias, belongs to one person.
  The service enforces this, because these are two tables.
- **Matching:** `resolve_match(index, email, current_person_id,
  current_method)`. With `match_method = manual` it returns the current owner,
  also "nobody" (manual unassignment). Otherwise: the primary e-mail, then an alias,
  then `none`. Sync loads `load_email_index()` once per run.
- **After a change to a person's e-mails** (new person, e-mail change, aliases, import)
  the service calls `rematch_accounts(session, emails)`. Accounts with these addresses
  change owner; manual assignments stay.
- **An account with an owner** and `kind = unknown` gets `kind = person`
  (`set_owner`).
- **An account without an owner:** `person_id IS NULL`, `kind != service`,
  `status != removed` (`unassigned_clause`). It counts in alerts,
  in `unassigned_count` and in the `?unassigned=true` filter.
- **Costs** are computed at full precision. Rounding to cents happens only
  on output (`Money` in `schemas/common.py`). A seat is an `active` or
  `invited` account with `kind` `person` or `unknown`. `flat` does not go into a
  person's cost. Amounts in JSON are strings, e.g. `"123.40"`.
- **Audit:** every event has `app_id` and `person_id` (without foreign keys,
  so the log survives deletions). `audit.record` takes them from the arguments, from the entity
  (`app`, `person`), from `data` (`app_id`, `person_id`, `previous_person_id`)
  or from the account, action or connection row. `GET /api/audit?app_id=…`
  and `?person_id=…` give the history of an app or a person.
- **Deleting a person** (`DELETE /api/people/{id}`): only without accounts and actions
  (409), e.g. a person added by mistake. `PersonDetail.can_delete` says
  whether it is allowed. Leaving the company is offboarding, not deletion.
- **Actions:** status transitions are in `TRANSITIONS` in `services/actions.py`.
  A person closes a `manual_task` (`complete`), and it does not go through
  `running`. A connector action ends as `done` only through `running` or
  `verifying`. Closing a manual account removal without a connection marks
  the account as `removed`.
- **`connector_supports()`** in `services/capabilities.py` checks the connector
  of the app's connection in the registry: with a write `Capability` the action is
  `create_account` / `delete_account`, without it `manual_task`. Execution,
  `writes_enabled` and verification: `skills/backend/actions.md`.

## API conventions

- Lists: `{"items": [...], "total": N}`, parameters `q`, `status`, `limit`
  (default 100, max. 500), `offset`. `GET /api/actions` accepts
  `status` several times and also returns `counts` (the number of actions in each status
  with the same filters without `status`).
- `ImportRowResult` of `create` rows has the fields of the new person: `first_name`,
  `last_name`, `employee_code`, `aliases`, `manager_email`, `department`, `job_title`.
- `AppListItem` has `create_mode` and `delete_mode` (`automatic`,
  `writes_disabled`, `manual`) and `delete_suspends`: the panel says what will happen
  before it creates an action.
- PATCH changes only the fields present in the request (`model_fields_set`).
  `null` in an account's `person_id` is a manual unassignment.
- Endpoints that are not built yet return 501 `{"detail": "Not implemented
  yet"}` with the final response schema in OpenAPI.
- `operationId` is the name of the endpoint function, e.g. `list_people`.

## How to extend

1. New field or table: model in `app/models/`, Alembic migration
   (`skills/backend/new-model.md`), schema, service.
2. Endpoint or schema change: after the change, refresh the contract from the
   repo root (the local dev stack must be running):
   ```bash
   dc exec -T api python scripts/export_openapi.py > docs/openapi.json
   ```
   The frontend writes its types from this file.
3. New cost or matching rule: change `costs.py` or `matching.py`
   and check the result by hand on the seeder data (`backend/app/db/seed.py`):
   costs on the dashboard and in `GET /api/apps`, account assignment in the panel.
4. New write in a service: always `audit.record(...)`.
