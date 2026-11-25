# Contributing to Open Revoke

Thank you for helping. This file says how to run Open Revoke from source, which checks a change
must pass and what a pull request needs.

Found a security problem? Do not open an issue: follow [SECURITY.md](SECURITY.md).

## Run it from source

For development use the dev stack: hot reload, fictional people and test connectors
(README, "Contributing"):

```bash
cp .env.example .env   # set OPEN_REVOKE_SECRET_KEY (the command is in the file)
docker compose -f compose.dev.yaml up -d --build
```

Panel http://localhost:18410, sign in as `admin@example.com` / `open-revoke-dev-password`. To try
the production image instead, follow "From source" in [README.md](README.md#from-source).

For the checks below you also need, on the host:

- [uv](https://docs.astral.sh/uv/) for the backend (Python 3.14, uv installs it)
- [Bun](https://bun.sh) 1.4 for the panel

Larger features have a short guide in `skills/`. Read the one for the area you change before you
change it; `AGENTS.md` lists them.

## Checks

Run them before you open a pull request. CI runs the same ones.

Backend:

```bash
cd backend
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
```

Panel:

```bash
cd frontend
bun install --frozen-lockfile
bun run lint
bun run typecheck
bun run build
```

Shell scripts in `deploy/` and `scripts/` are POSIX sh. Check them with
[ShellCheck](https://www.shellcheck.net/):

```bash
docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck:stable -s sh -x deploy/install.sh deploy/open-revoke deploy/lib/*.sh scripts/*.sh
```

There are no automated tests of the application logic yet. Check your change by hand in the running
stack as well: call the endpoint, run the sync or the action, open the page. Say in the pull
request what you checked.

## Add a connector

A connector is one Python package per app in `backend/app/connectors/<key>/`. It reads accounts
and can create and remove them; it never writes to the database. The guide is
[skills/backend/new-connector.md](skills/backend/new-connector.md). Browser connectors also need
[skills/backend/browser.md](skills/backend/browser.md).

Recordings made with `app.devtools.capture` go to `captures/`. That folder is git-ignored because
the recordings contain real names, e-mail addresses and session data. Never commit it, never paste
its content into an issue or pull request, and delete it when the connector is done.

## Database changes

The SQLAlchemy models in `backend/app/models/` define the schema. Every change to a model needs an
Alembic migration in `backend/migrations/versions/` in the same pull request.

1. Change the model.
2. Generate the migration against a database that is on the latest revision, from `backend/`:

   ```bash
   uv run alembic revision --autogenerate -m "short description"
   ```

3. Read the generated file and fix it by hand. Autogenerate is a draft, not a result:
   - A renamed column or table is `op.alter_column(..., new_column_name=...)` or
     `op.rename_table(...)`. Never a drop followed by an add: that deletes the data.
   - Leave `downgrade()` empty (`pass`). Open Revoke does not migrate down; a failed update is
     rolled back from the backup taken before it.
   - Do not import application models or services inside a migration. A migration must still work
     after the models change again. Use `op` and `sqlalchemy` constructs only, and write any data
     change with `op.execute` or a table defined inside the migration.
   - A new `NOT NULL` column needs a `server_default` or a data step for existing rows.
4. Run it on a database with data and check `uv run alembic check` reports no differences.

## Changelog

Every change that people who run Open Revoke notice adds one line under `## [Unreleased]` in
[CHANGELOG.md](CHANGELOG.md), in the same pull request. Use the sections `Breaking` (with the
command to run), `Added`, `Changed`, `Fixed`, `Security`. Internal refactors, docs and CI changes
need no line.

## Pull requests

- Keep one change per pull request. Explain what changes and why.
- Write commit messages, code, comments and docs in English.
- Never commit secrets, `.env` files, `captures/`, database dumps, screenshots of real admin panels
  or any real person's data. Seed data and examples use `example.com` and invented names.
- Code works for any company. Do not hard-code one organization, domain or app list.
- Keep files under 600 lines; split them before that.

## License of contributions

Code outside any `ee/` directory is under the [MIT license](LICENSE). By opening a pull request you
agree that your contribution is licensed under the MIT license. There is no Contributor License
Agreement to sign.

Code inside `ee/` is under the [Open Revoke Enterprise License](ee/LICENSE), not MIT.

## Code of conduct

Everyone who takes part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
