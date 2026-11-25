# Open Revoke

Open Revoke is a self-hosted panel for companies that use dozens of SaaS tools. It keeps one list of
people, the accounts each person has in each app, and what those seats cost per month. From the same
panel you can add an account to an app or remove it, for one person or for everyone who leaves.

Open Revoke talks to an app in one of three ways:

1. **Official API** (for example the Google Admin SDK or the GitHub REST API).
2. **SCIM 2.0**, for any app that exposes a SCIM endpoint. One generic connector covers all of them.
3. **A real browser session.** Chromium runs in Docker. An admin logs in to the app's admin panel
   through a live view in Open Revoke. The connector then sends the same HTTP requests the admin
   panel sends, from inside that logged-in tab.

Every write (an invitation, a removal) waits for a person to approve it, runs in the background and
is then checked by reading the app's account list again. A write that the read does not confirm ends
as failed, even if the app answered 200.

## Status

Early MVP. Read this before you run it.

- **Sign-in.** Password, with optional two-factor authentication (any authenticator app). On a
  fresh install only the setup link printed on the server creates the admin account
  (`open-revoke setup-link`); later users join by an invite link or sign up for an admin to
  approve. The panel sends no e-mail.
- **One port.** Only the panel is published (`127.0.0.1:18410` by default). The API sits behind
  it, and the live view of the shared browser goes through the API, for signed-in admins only. To
  run it on a server under your own domain, follow [docs/self-hosting.md](docs/self-hosting.md).
- **The `browser-profile` Docker volume holds logged-in admin sessions** of the apps you connect
  through the browser (Slack, Claude, ChatGPT and others). Anyone with this volume has those
  sessions. Do not copy it. `docker compose down -v` deletes it.
- **Most connectors are not verified on real accounts yet** (see the table below). Keep "Allow writes"
  off for a connection until a sync has shown you the account list you expect, and test writes on a
  test account first.
- **Google Workspace removal suspends the user.** It never deletes: deletion removes mail and files
  for good.
- Paid usage (tokens, credits), invoices and API key inventory are not part of the MVP.

## Quick start

Requirements: Docker with Docker Compose 2.20 or newer, on Linux or macOS, amd64 or arm64.

### With the installer (from the first release)

```bash
curl -fsSLO https://github.com/Take-Group/openrevoke/releases/latest/download/install.sh
less install.sh   # read it first: it holds admin sessions of your SaaS tools
sh install.sh
```

It checks Docker, writes `.env` with generated secrets and this machine's time zone, starts the
stack and prints the link that creates the first admin. Then `open-revoke status`,
`open-revoke backup`, `open-revoke update` (backs up the database first and goes back if the new
version does not start), `open-revoke help`. Releases and updates: `CHANGELOG.md`.

### From this source

Run the commands in this folder (the one with `compose.yaml`).

```bash
cp .env.example .env
openssl rand -base64 32 | tr '+/' '-_'   # put it into .env as OPEN_REVOKE_SECRET_KEY=
openssl rand -hex 24                     # put it into .env as POSTGRES_PASSWORD=
docker compose -f compose.yaml -f compose.build.yaml up -d --build
docker compose exec app /app/backend/.venv/bin/python -m app.cli setup-link
```

The last command prints the link that creates the first admin (the `app` log shows one too).

`OPEN_REVOKE_SECRET_KEY` encrypts the connector secrets (API tokens, SCIM tokens, the Google
service account key) in the database. The stack refuses to start without it. If you lose the key,
you have to enter those secrets again. Keep a copy in a password manager.

After start:

| Service | Address |
|---|---|
| Panel (the API is behind it, under `/api`) | http://localhost:18410 |
| Browser live view | in the panel, page **Browser** (admins) |

Stop with `docker compose down` (or `open-revoke stop`). Your data stays in Docker volumes (`pgdata`, `browser-profile`).

The `app` container applies the database migrations when it starts. `open-revoke update` backs
the database up first; there are no downgrades, `open-revoke rollback` restores that backup.

## How browser login works

1. Add the app in **Apps**, choose the integration `browser` and save a browser connector (Slack,
   Claude or ChatGPT) in the app's connection settings.
2. Open **Browser** in the panel. It embeds the live view of the shared Chromium. Click
   **Log in** next to the app: the app's login page opens in that Chromium.
3. Log in by hand in the live view, including 2FA. Open Revoke never sees your password.
4. Click **Sync now** on the app. The connector reads the member list from inside the logged-in tab.

The session lives in the `browser-profile` volume and survives container restarts. When the app logs
you out, the next sync ends with the status `needs_login` (not with removed accounts) and the
dashboard asks you to log in again. The live view (noVNC in the browser container) has no
port of its own: the API passes it to the panel after it checks the admin's session.

## Connectors

| Connector | Method | Reads | Creates | Removes | Verified on a real account |
|---|---|---|---|---|---|
| Google Workspace | Admin SDK Directory API, "Connect with Google" (OAuth) or a service account with domain-wide delegation | users, also as a source of people; sign-ins to third-party apps (app discovery) | user with a temporary password shown once | suspends the user | Reading and app discovery: yes. Writes: no |
| GitHub | REST API, organization token | members and pending invitations | invitation to the organization | removes from the organization or cancels the invitation | No. Written from the public API docs |
| SCIM 2.0 | SCIM, bearer token | `GET /Users` | `POST /Users` | `active: false` or `DELETE /Users/{id}` | No. Written from RFC 7643 and RFC 7644 |
| Slack | browser session: web client API for reads, a click recipe in the admin page for writes | members, plan and price from billing | invitation | deactivation | Yes, on a Pro workspace |
| Claude (Team) | browser session, private claude.ai endpoints | members and pending invites | invitation | removes the member or revokes the invite | No. Endpoints are a best guess, not recorded yet |
| ChatGPT (Team) | browser session, private chatgpt.com endpoints | members and pending invites | invitation | removes the member or revokes the invite | No. Endpoints are a best guess, not recorded yet |

Apps without a connector use the integration `manual`: you enter accounts by hand, and onboarding
or offboarding creates a checklist task instead of a write.

Sync rules that protect your data:

- A connector returns the full account list or fails. It never returns part of a list.
- If one sync would mark more than 30% of an app's accounts as removed, it stops and changes
  nothing. When the removals are real, run the sync again with force.
- An account you assigned to a person by hand keeps that owner across syncs.

## Adding a connector

A connector is one Python module per app in `backend/app/connectors/<key>/`. It reads accounts and
optionally creates and removes them; it never writes to the database. The guide is in
[skills/backend/new-connector.md](skills/backend/new-connector.md).

For browser connectors, record what the admin panel does while you click through it in the live
view:

```bash
docker compose exec app python -m app.devtools.capture --host app.slack.com --out captures/slack.jsonl
```

The tool saves every fetch/XHR request to that host as JSON lines, with tokens and auth headers
masked. The file still contains real names and e-mails: `captures/` is in `.gitignore`, keep it out of
git and delete it when the connector is done. Details:
[skills/backend/browser.md](skills/backend/browser.md).

## Development

`compose.dev.yaml` runs the whole stack with hot reload and fictional data (12 people at
example.com from a fake directory, test connectors `fake` and `browser_fake`):

```bash
cp .env.example .env   # set OPEN_REVOKE_SECRET_KEY (command in the file)
docker compose -f compose.dev.yaml up -d --build
```

Panel http://localhost:18410 (sign in as `admin@example.com` / `open-revoke-dev-password`), API
http://localhost:18411, browser live view http://localhost:18412/vnc.html. A model change needs an
Alembic migration: [skills/backend/new-model.md](skills/backend/new-model.md). How to contribute:
[CONTRIBUTING.md](CONTRIBUTING.md); security reports: [SECURITY.md](SECURITY.md).

## Checks for contributors

There are no automated tests yet. Check a change by hand in the dev stack (call the endpoint, run
the sync or action, open the page) and run the linters; CI runs the same.

Backend lint (ruff), with [uv](https://docs.astral.sh/uv/) on the host:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
```

Frontend checks, with [Bun](https://bun.sh) on the host:

```bash
cd frontend
bun install
bun run lint && bun run typecheck && bun run build
```

## Project layout

| Folder | Contents |
|---|---|
| `backend/` | Python 3.14, FastAPI, SQLAlchemy with Alembic migrations, Temporal workflows, connectors |
| `frontend/` | Next.js 16, React 19, TypeScript, Tailwind CSS |
| `docker/` | entrypoints and supervisor configuration of the containers |
| `deploy/`, `scripts/` | installer and host command `open-revoke`; release scripts |
| `docs/` | self-hosting, click recipes, API contract (`openapi.json`), connector notes |
| `skills/` | how the larger features work, for contributors and coding agents |

## License

Open Revoke is open source under the [MIT license](LICENSE), copyright Take Group sp. z o.o.
You may use, change and redistribute it, also commercially and in your own products.

The only exception is code in an `ee/` directory: it is under the
[Open Revoke Enterprise License](ee/LICENSE): you may read it and evaluate
it outside production, but production or commercial use, changes and
redistribution need a commercial license from Take Group. Today no `ee/` directory holds code; every feature in this
repository is MIT.

The license covers the code, not the "Open Revoke" name and logo
([trademark terms](https://openrevoke.com/terms)).

The app catalog shows names and logos of third-party SaaS products only so that you can
recognize those apps. They are trademarks of their owners, who do not endorse Open Revoke, and
the MIT license does not cover them. Details: [NOTICE](NOTICE).
Contributions outside `ee/` are accepted under the MIT license.
