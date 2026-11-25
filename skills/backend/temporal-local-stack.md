# Local Temporal stack

## Goal

Local Temporal runs in Docker Compose without the Temporal Web UI. Short-lived
`admin-tools` containers initialize the database schema
and the namespace, and the actual server runs on the supported `temporalio/server` image.

## Files

- `compose.yaml` (self-hosting) and `compose.dev.yaml`
  (local dev stack): server, dependencies and start order.
- `Dockerfile` (target `postgres`): a minimal PostgreSQL image that runs
  directly as non-root, without the unused `gosu` binary.
- `backend/temporal/scripts/setup-postgres.sh`: creates and updates
  the `temporal` and `temporal_visibility` schemas.
- `backend/temporal/scripts/create-namespace.sh`: idempotent creation of the
  namespace after the server is ready.
- `backend/temporal/dynamicconfig/development-sql.yaml`: dynamic settings
  meant only for the local SQL environment.
- `backend/app/temporal/worker.py`: the worker that connects to the server.

## Start flow

1. PostgreSQL passes its healthcheck.
2. `temporal-schema-setup` creates or updates both Temporal schemas.
3. `temporal` starts the server with the SQL configuration.
4. `temporal-create-namespace` waits for the server and ensures the `default` namespace.
5. The `app` container starts only after the namespace initialization ends;
   supervisor starts the `worker` process in it. In the local dev stack the worker
   is a separate `worker` service (`watchfiles`), restart: `dc restart worker`.

PostgreSQL, Redis and Temporal are reachable only on the Compose network. The Web UI
is not part of the stack.

## Extending

- Update the server and `admin-tools` versions together.
- Leave Temporal schema changes to `temporal-sql-tool`. They do not belong to
  the app schema (`backend/app/db/`), and `python -m app.db reset` does not
  touch them.
- Add a new namespace as a separate, idempotent init service.
- Add new local server settings to the `development-sql.yaml` file.
- Do not add `temporalio/ui` and do not publish port 7233 without agreeing on
  a new requirement.
