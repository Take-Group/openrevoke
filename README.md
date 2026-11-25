# Open Revoke

**Self-hosted SaaS access management: who has an account where, what it costs, and offboarding
that removes a leaver's accounts, also in apps without an API.**

[Website](https://openrevoke.com) · [Docs](https://openrevoke.com/docs) ·
[Connectors](docs/connectors/README.md) · [Self-hosting](docs/self-hosting.md) ·
[Contributing](CONTRIBUTING.md)

## What is Open Revoke

A panel you run on your own server, for companies that use dozens of SaaS tools.

- **Inventory.** One list of people and the accounts each person has in each app, synced from
  Google Workspace, GitHub, SCIM, Slack and others, matched by e-mail.
- **Costs.** Price per seat or per plan, in your currency.
- **Onboarding and offboarding.** Add or remove a person's accounts in one step: through the app's
  API, SCIM, or a logged-in browser session for apps without an API. Every write waits for an
  approval and is checked by reading the app's account list again.
- **AI assistants.** A built-in MCP server lets Claude Code, Codex or Cursor do what you can do in
  the panel.

## Status

Early MVP. Most connectors are not verified on real accounts yet: keep "Allow writes" off until a
sync shows the account list you expect. Details per app: [docs/connectors](docs/connectors/README.md).

## Get started

Requirements: Docker with Docker Compose 2.20 or newer, Linux or macOS, amd64 or arm64.

### Installer (from the first release)

```bash
curl -fsSLO https://github.com/Take-Group/openrevoke/releases/latest/download/install.sh
less install.sh   # read it first: the server will hold admin sessions of your SaaS tools
sh install.sh
```

It writes `.env` with generated secrets, starts the stack and prints the link that creates the
first admin. Then: `open-revoke status | backup | update | help`.

### From source

```bash
cp .env.example .env
openssl rand -base64 32 | tr '+/' '-_'   # put into .env as OPEN_REVOKE_SECRET_KEY=
openssl rand -hex 24                     # put into .env as POSTGRES_PASSWORD=
docker compose -f compose.yaml -f compose.build.yaml up -d --build
docker compose exec app /app/backend/.venv/bin/python -m app.cli setup-link
```

Open the printed link to create the first admin. The panel runs on http://localhost:18410.
Keep `OPEN_REVOKE_SECRET_KEY` in a password manager: it encrypts the connector secrets, and
without it you enter them again.

Next steps:

- Run it under your own domain: [docs/self-hosting.md](docs/self-hosting.md).
- Connect your apps: [docs/connectors](docs/connectors/README.md).
- Connect an AI assistant: create a token in **Settings, API and MCP**; the page shows the command.

## Security

The `browser-profile` Docker volume holds logged-in admin sessions of the apps you connect through
the browser. Do not copy it. Google Workspace removal suspends users and never deletes them.
Report vulnerabilities privately: [SECURITY.md](SECURITY.md). Telemetry: [TELEMETRY.md](TELEMETRY.md).

## Contributing

Dev stack with hot reload and fictional data: `docker compose -f compose.dev.yaml up -d --build`.
Checks, migrations and pull requests: [CONTRIBUTING.md](CONTRIBUTING.md). Coding agents start with
[AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE), except code in an `ee/` directory ([Open Revoke Enterprise License](ee/LICENSE));
today no `ee/` directory holds code. The "Open Revoke" name and logo are not covered
([trademark terms](https://openrevoke.com/terms)); third-party app names and logos: [NOTICE](NOTICE).
