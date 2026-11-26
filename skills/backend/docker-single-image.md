# Skill: One Docker image for the whole project

## What it does

The whole product, backend (API, Temporal worker, table creation) and frontend
(Next.js), builds from one `Dockerfile` in the `open-revoke/` folder
(build context), and for self-hosting runs from one `compose.yaml`
next to it. There, backend and frontend run in **one container** (`app`), as
three processes under supervisor.

Local development does not use `compose.yaml`. It uses the
`compose.dev.yaml` stack (described below), which takes
the `backend-dev` and `browser` targets from the same `Dockerfile`, and PostgreSQL
and Redis from the official images.

## Files

- `Dockerfile`: the only file that builds images. Targets used by compose:
  - `app`: the self-hosting image: backend + frontend + supervisor
  - `backend-dev`: backend with dev dependencies (ruff), venv in `/opt/venv`,
    code mounted from the host (local dev stack)
  - `browser`: Chromium on Xvnc (TigerVNC) with noVNC and CDP (a separate container, not
    in `app`; described in `skills/backend/browser.md`)

  PostgreSQL (`postgres:18.7`, has `tzdata`) and Redis (`redis:8.10.3-alpine`)
  are official images. The time zone is not set
  in the images: `TZ` from `.env` (default UTC), the panel without `NEXT_PUBLIC_TIME_ZONE`.
  Version: `ARG OPEN_REVOKE_VERSION` at the end of the `app` target (the layer cache
  stays), OCI labels. Releases: `skills/backend/releases.md`.

  Intermediate stages of the `app` target: `bun-binary` (the `bun` binary),
  `frontend-build` (`bun run build`, standalone mode), `backend-build`
  (`uv sync` without dev dependencies).
- `compose.yaml`: the self-hosting stack on release images
  (`ghcr.io/take-group/open-revoke[-browser]:${OPEN_REVOKE_VERSION}`): `postgres`, `redis`,
  `temporal-schema-setup`, `temporal`, `temporal-create-namespace`,
  `browser`, `app`, and in the `https` profile also `caddy`
  (`docker/caddy/Caddyfile`, site address = `PUBLIC_URL`, Let's Encrypt).
  On the host only the panel (`${OPEN_REVOKE_BIND:-127.0.0.1}:${OPEN_REVOKE_PORT:-18410}`);
  the API is behind the panel (`/api`), the browser has no
  ports. Installation on a domain: `docs/self-hosting.md`.
- `compose.build.yaml`: an overlay with `build:` for `app` and `browser` (building
  from source: `docker compose -f compose.yaml -f compose.build.yaml up -d --build`)
  and the `./captures` mount.
- `docker/entrypoint.sh`: `python -m app.db migrate` (Alembic migrations) with retry;
  exit code 2 (a database from a newer version or from before migrations) ends the start at once; then `exec` of supervisor
- `docker/supervisord.conf`: definitions of the `api`, `worker`, `frontend` processes
- `.dockerignore`: cuts `backend/.venv/`,
  `frontend/node_modules/`, `frontend/.next/` and others from the context.

## Flow (self-hosting, `compose.yaml`)

1. `docker compose up -d` pulls the images of version `OPEN_REVOKE_VERSION`
   (with the `compose.build.yaml` overlay and `--build` it builds `app` and `browser`).
2. Compose starts the infrastructure: PostgreSQL → Temporal schema →
   Temporal server → namespace.
3. The `app` container starts after `service_healthy` (postgres, redis) and
   `service_completed_successfully` (Temporal namespace).
4. `entrypoint.sh` runs `python -m app.db migrate` (up to 30 attempts every 2 s,
   Alembic migrations under a `pg_advisory_xact_lock` lock).
5. `exec supervisord` starts three processes; all log to the container's stdout,
   so `docker compose logs app` shows everything.
6. The healthcheck of the `app` service queries `http://127.0.0.1:8000/health`.

## Local dev stack (`compose.dev.yaml`)

- Services: `api` (`uvicorn --reload`, at start
  `python -m app.db migrate --seed`), `worker` (`watchfiles` restarts it after
  a `.py` change), `web` (`next dev`), `postgres`,
  `redis`, `temporal`, `browser`. The code is mounted from disk, so
  a code change needs no rebuild. A new Python dependency: restart the service
  (`uv sync --frozen` at start).
- Addresses, all on `127.0.0.1`: panel http://localhost:18410, API
  http://localhost:18411, noVNC http://localhost:18412/vnc.html, CDP
  http://127.0.0.1:18415. The panel
  shows the live view through the API (`/api/browser/live/...`), as in self-hosting,
  when `BROWSER_LIVE_VIEW_URL` is not set in `compose.dev.yaml`.
- Commands (`dc` = `docker compose -f compose.dev.yaml`): `dc exec api <cmd>`,
  `dc exec api ruff check .`, `dc logs --tail 100 api`, `dc exec postgres psql -U postgres -d open_revoke -c "select …"`,
  `dc restart worker`. After a model change, a migration
  (`skills/backend/new-model.md`), then `dc exec api python -m app.db reset`.
- In the compose network the API has the alias `open-revoke-app` (the
  `browser_fake` fake panel: http://open-revoke-app:8000/api/dev/fake-panel),
  the CDP browser has the alias `open-revoke-browser`.

## Pitfall: build paths must match the final paths

`uv sync` writes **absolute** paths into the shebangs of the scripts in
`.venv/bin/` (e.g. `#!/app/backend/.venv/bin/python`). If a build stage
uses a different folder than the final image, every script from the venv fails with
`not found` even though the file exists.

That is why `backend-build` has `WORKDIR /app/backend` and `frontend-build`
has `WORKDIR /app/frontend`, exactly as in the `app` target. Do not change
these paths separately. `backend-dev` keeps the venv outside the mounted folder
(`/opt/venv`), because the `/app/backend` mount would cover `.venv`.

## How to extend

- **New process in the `app` container**: add a `[program:name]` section in
  `docker/supervisord.conf` (remember `stdout_logfile=/dev/fd/1`,
  `stdout_logfile_maxbytes=0`, `redirect_stderr=true`). In the local dev
  stack it is a separate service in `compose.dev.yaml`.
- **New system dependency of the backend**: `apt-get install` in the `app`
  and `backend-dev` targets. Example: `libatomic1` for the Node.js driver from the
  `playwright` package (without it `connect_over_cdp` fails on arm64).
- **New infrastructure image**: first an official image with a pinned version
  in `compose.yaml` and `compose.dev.yaml`. A custom target at the end of the
  `Dockerfile` only when the official one is not enough; then also in
  `scripts/build-release.sh`. Do not create separate `Dockerfile.*` files.
- **New public frontend variable (`NEXT_PUBLIC_*`)**: it must be set
  as `ENV` in the `frontend-build` stage, because Next inlines it at build time.
  Setting it only in `compose.yaml` does not work for code in the browser.
  In the local dev stack set it in the `environment` of the `web` service.
- **Restart of a single process in `app`** without rebuilding the image (self-hosting
  only):
  `docker compose exec app supervisorctl -c /etc/supervisor/supervisord.conf restart api`.
  In the local dev stack: `dc restart api` (or `worker`, `web`).

## Limits of the `app` container you need to know

- No hot reload: the frontend is a production build, the backend starts without
  `--reload`. Every code change needs a new image (`compose.build.yaml`
  with `--build` or `scripts/build-release.sh`). That is why
  development runs on `compose.dev.yaml`.
- Backend and frontend restart together when the container restarts.
- You cannot scale the backend separately from the frontend.
