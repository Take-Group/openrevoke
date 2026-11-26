# Open Revoke backend

Product rules are in `../AGENTS.md`. This file covers the backend only.

## Stack

- Python 3.14+, FastAPI (Uvicorn), Pydantic 2 and pydantic-settings
- SQLAlchemy 2 (async) with asyncpg on PostgreSQL 18; Alembic migrations
- Temporal (workflows and activities), Redis 8 (locks, rate limits, sign-in tickets)
- cryptography (Fernet) for connector secrets, structlog, httpx, playwright (CDP only)
- uv for packages; ruff in the `dev` group

## Processes in the local stack

| Service | Command | Notes |
|---|---|---|
| `api` | `python -m app.db migrate --seed`, then `uvicorn --reload` | http://localhost:18411, `/health`, `/health/ready` |
| `worker` | `watchfiles ... worker` | Temporal worker, queue `open-revoke`; restarts on every `.py` change |

Both (`../compose.dev.yaml`) mount `backend/` at `/app/backend` and keep the venv in `/opt/venv`
(Dockerfile target `backend-dev`). They run `uv sync --frozen` at start.
Dependencies: `uv add --no-sync <pkg>` (or `--dev`) on the host in
`backend/`, then `dc restart api worker`.

Infrastructure: `postgres`, `redis`, `temporal` (+ one-off setup jobs),
`browser` (Chromium, CDP 9223 in the compose network, noVNC on
127.0.0.1:18412 in the dev stack only; the panel's live view goes through
the API, `skills/backend/browser.md`), no mail server: the panel sends no e-mail. Inside the
compose network use the aliases `open-revoke-postgres`, `open-revoke-redis`,
`open-revoke-temporal`, `open-revoke-browser`,
`open-revoke-app` (the API): plain service names may collide with other
projects when the stack joins a shared network (a local reverse proxy).

## Database

- Schema = models in `app/models/` plus Alembic revisions in `migrations/versions/`
  (`alembic.ini`). A model change needs a revision: skill `skills/backend/new-model.md`.
- `python -m app.db migrate [--seed]`: upgrade head under an advisory lock; refuses a
  database from a newer version or from before migrations (exit 2).
- `python -m app.db reset`: development only: drop the `public` schema, migrate from
  zero, flush Redis, seed, reconcile Temporal schedules.
- `app/db/seed.py`: fictional organization, panel users
  (`admin@example.com` admin, `member@example.com` member, password
  `open-revoke-dev-password`, no 2FA) and sample apps; people come from the
  Google Workspace connection (`seed_google.py`, `SEED_GOOGLE_*`). Extend it
  when a feature needs data in the panel.
- Queries by hand: `dc exec postgres psql -U postgres -d open_revoke`.

The self-hosting image (`docker/entrypoint.sh`) runs `python -m app.db migrate`
at start; `open-revoke update` backs the database up before.

## Configuration

`app/config.py` (env variables; list with descriptions in `.env.example`).
The dev stack sets them in `../compose.dev.yaml`.

- `OPEN_REVOKE_SECRET_KEY`: Fernet key for connector secrets, required, from
  `../.env` or `_FILE`; `_PREVIOUS` only during `open-revoke rotate-key`.
- `OPEN_REVOKE_ENABLE_FAKE_CONNECTOR`, `OPEN_REVOKE_DEV_PREFILL`: test
  connector and one-click sign-in form fill; on in the local stack.
- `SYNC_INTERVAL_HOURS` (6), `ACTION_VERIFY_*`, `ACTION_LOCK_WAIT_SECONDS`:
  sync and write actions (`skills/backend/actions.md`).
- `PUBLIC_URL`, `SESSION_TTL_HOURS`: sign-in and
  e-mail (`skills/backend/auth.md`).
- `GOOGLE_OAUTH_REDIRECT_BASE`: base of the Connect with Google redirect URI
  (default `PUBLIC_URL`); the local stack sets `http://localhost:18410`,
  because Google refuses `*.localhost`.
- `ALLOWED_HOSTS`, `CORS_ORIGINS`: JSON lists. Requests with another `Host`
  or `X-Forwarded-Host` get 400 (DNS rebinding protection). The host and
  origin of `PUBLIC_URL` are always added (`settings.trusted_hosts`,
  `settings.trusted_origins`).
- `BROWSER_LIVE_VIEW_URL` (default `/api/browser/live/live.html?...`, the
  API proxy), `BROWSER_LIVE_PORT` (6080): live view of the shared browser.

Admin CLI for panel users: `dc exec api python -m app.cli list-users`
(also `reset-2fa <email>`, `set-password <email>`).

## Checks

```bash
dc exec api ruff check .
dc exec api ruff format --check .
```

Then check by hand: `curl` the endpoint on http://localhost:18411
(mutating requests need the header `X-Open-Revoke-Client: 1` and a session
cookie from `POST /api/auth/login`), or run the workflow and read
`dc logs --tail 100 worker`. After an endpoint or schema change refresh
`../docs/openapi.json` (command in `../AGENTS.md`).

## Code rules

- Business logic in `app/services/`, not in endpoints. Endpoints validate,
  call a service, return a schema.
- Temporal: workflows and activities in separate files. A workflow only
  calls activities; activities call services.
- Domain model, account matching, costs and API conventions:
  [skills/backend/domain-model.md](../skills/backend/domain-model.md).
- SOLID and max 600 lines per file (`../../AGENTS.md`).

## Files

- `app/`: own AGENTS.md. The FastAPI app, services, connectors, Temporal worker.
- `pyproject.toml`: dependencies (uv), `ruff` config, scripts `serve` (`app.main:run`) and `worker` (`app.temporal.worker:run`).
- `alembic.ini`: Alembic config (URL from the settings, ruff on new revisions).
- `migrations/`, no map: `env.py` (async engine; uses the connection `app.db migrate` passes), `script.py.mako`, `versions/` (one revision per schema change, first the baseline).
- `uv.lock`: locked dependencies; change it with `uv add --no-sync`, never by hand.
- `.env.example`: every env variable with a description (read by `app/config.py`).
- `.dockerignore`, `.gitignore`: ignore `.venv/`, caches and `.env`.
- `scripts/`, no map: `export_openapi.py` (prints the OpenAPI schema; command in its docstring writes `../docs/openapi.json`), `fetch_catalog_logos.py` (downloads app logos into `app/catalog/logos/`), `probe_google_sign_in.py` (reads Google OAuth client ids from apps' sign-in pages); both run on the host.
- `temporal/`, no map: `dynamicconfig/development-sql.yaml` (Temporal dev server config), `scripts/create-namespace.sh` (creates the namespace), `scripts/setup-postgres.sh` (prepares the Temporal databases); used by the compose setup jobs.
