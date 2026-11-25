# open-revoke/backend/app/

The FastAPI app and the Temporal worker. Layers: `api/` (endpoints) calls `services/` (logic) which uses `models/`, `connectors/`, `browser/`, `ai/`; `schemas/` are request and response types; `temporal/` workflows call services.

- `main.py`: `app` (FastAPI, CORS, `AllowedHostsMiddleware`, error handlers, `api_router`, the MCP endpoint at `/api/mcp`), `lifespan` (prints the setup link while no user exists, runs the MCP session manager), `run()`; operation id = endpoint function name.
- `config.py`: `settings` (pydantic-settings, all env variables; `version` from `OPEN_REVOKE_VERSION`, `update_check`, `update_check_url`, `telemetry`, `telemetry_url`), `trusted_hosts`, `trusted_origins`, `public_origin`, `cookie_secure`, `google_oauth_redirect_uri`.
- `database.py`: async `engine`, `async_session`, `Base` (naming convention), `get_session` dependency.
- `redis.py`: `redis_client`.
- `logging.py`: `setup_logging(debug)` (structlog).
- `cli.py`: `python -m app.cli list-users | reset-2fa | reset-link | set-password | setup-link` for panel users (`reset-link` prints a one-time password link, no e-mail; `setup-link` a new first-run setup link).
- `ops.py`: `python -m app.ops version | preflight | in-flight`: JSON for the host command `open-revoke` (install, update; `deploy/`), run inside the app image.
- `__init__.py`: empty.
- `api/`: own AGENTS.md. HTTP endpoints under `/api`.
- `schemas/`: own AGENTS.md. Pydantic request and response types.
- `models/`: own AGENTS.md. SQLAlchemy models, the only schema.
- `services/`: own AGENTS.md. Business logic.
- `connectors/`: own AGENTS.md. One folder per SaaS app plus the `Connector` interface.
- `temporal/`: own AGENTS.md. Workflows, activities, schedules, worker.
- `slack_agent/`: own AGENTS.md. Slack bot for access requests (runs in the worker).
- `mcp/`: own AGENTS.md. MCP server for AI assistants at `/api/mcp`, tools built from the API routes.
- `ai/`: own AGENTS.md. Language model providers.
- `browser/`: own AGENTS.md. Shared Chromium over CDP.
- `catalog/`, no map: `apps.json` (known SaaS apps: name, website, aliases, Google OAuth client ids, optional `login_url`), `logos/` (own AGENTS.md: `<slug>.png`, 128 px), `lookup.py` (`app_catalog()`, `AppCatalog.match`, `by_name`, `logo_path`, `normalize`, `MatchedBy`). Skill `skills/backend/app-catalog.md`.
- `recipes/`, no map: `model.py` (click recipe format: `Recipe`, `Step`, `Locator`, `load_recipe`, `render_steps`, `render_value`, `unrender_value`, `config_params`, `RecipeError`, `RecipeStepError` with screenshot; an irreversible click needs an earlier `expect` naming the person), `repair.py` (`RecipeSupport` protocol for local fixes and AI repair, `Alternative`, `Probe`, `ProbeResult`, `RepairRequest`, `Repair`). Run by `browser/recipe_runner.py`. Skill `skills/backend/click-recipes.md`.
- `db/`: own AGENTS.md. Schema create, reset, seed.
- `devtools/`, no map: `capture.py` (`python -m app.devtools.capture --host ... --out file.jsonl`: records an admin panel's fetch/XHR traffic to write a connector), `masking.py` (`mask_headers`, `mask_body`, `truncate`).
- `exchange_rates/`, no map: `providers.py` (`RateProvider` protocol, `OpenErApiProvider` then `CurrencyApiProvider` fallback, `RateSnapshot`, `RatesUnavailableError`); stored by `services/exchange_rates.py`.
