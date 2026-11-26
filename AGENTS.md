# Open Revoke (product): agent instructions

Rules: no automated tests yet: check a change by running it (checks below,
then the dev stack). A model change needs an Alembic revision
(`skills/backend/new-model.md`). Development data is fictional
(`backend/app/db/seed.py`). English code and docs; max 600 lines per file.
A workspace that holds this repo may add rules in `../AGENTS.md`.

## What it is

Open source app for companies with dozens of SaaS tools and no single place
that shows people, costs and access. Three features:

1. **Inventory**: who has an account in which app, synced from Google
   Workspace, GitHub, SCIM, Slack, Claude, ChatGPT and others, matched to
   people by e-mail.
2. **Costs**: price per seat or plan, converted to the organization's
   currency with daily exchange rates.
3. **Offboarding**: when someone leaves, write actions remove or suspend
   their accounts, through the app's API or, without an API, through a shared
   Chromium (`browser` container) where an admin is signed in. Each write is
   verified by reading the account list again.

An MCP server lets AI assistants (Claude Code, Codex) do what a panel user can.

A Slack agent (`skills/backend/slack-agent.md`) takes access requests in
direct messages: a language model (Anthropic, OpenAI, OpenRouter or any
OpenAI-compatible endpoint) turns "I need Notion" into an onboarding action
for the person who wrote, per-app policy decides if an admin approves it.

App discovery scans Google Workspace sign-in logs for apps people use with
the company account. The code must work for any company, not only one.

Connectors are checked on the test connectors, not yet on real accounts.

## Files

- `.agents/`: skills (explore, verify, diagnose, harness).
- `.claude/`: `skills` symlink to `.agents/skills` for Claude Code.
- `.github/`: CI (ruff, `alembic check`, panel lint/typecheck/build, Helm, ShellCheck), release on tag `v*` (`release.yml`: images, SBOM, cosign, SLSA L3 provenance, chart on GHCR; `release-test.yml`: Trivy, install, update and kind tests), CodeQL, zizmor, Scorecard, weekly Chromium check, Dependabot, templates. Actions pinned to SHA.
- `.dockerignore`, `.gitignore`: build context and git filters.
- `.trivyignore`: vulnerabilities a release accepts, each with a reason.
- `.env.example`: template of the git-ignored `.env`; `install.sh` fills it.
- `CHANGELOG.md`: release notes; a noticeable change adds a line under `[Unreleased]`.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`: MIT, no CLA; Contributor Covenant; private vulnerability reports.
- `LICENSE`: MIT outside `ee/`; `ee/LICENSE` (commercial, no code yet) for paid features.
- `NOTICE`: copyright; catalog app names and logos are their owners' trademarks.
- `README.md`: public overview and get started; details in `docs/`.
- `TELEMETRY.md`: what telemetry sends, how to turn it off.
- `Dockerfile`: targets `app` (API, worker and panel under supervisor), `backend-dev` (dev stack), `browser`.
- `compose.yaml`: self-hosting on release images, one port, Caddy profile `https`.
- `compose.build.yaml`: overlay that builds `app` and `browser` from source.
- `compose.dev.yaml`: development stack, hot reload, fictional data, ports 18410-18415 on 127.0.0.1.
- `backend/`: own AGENTS.md. Python 3.14, FastAPI, SQLAlchemy 2 with Alembic, Temporal, Redis.
- `frontend/`: own AGENTS.md. Next.js 16 panel, React 19, Tailwind 4, Bun.
- `deploy/`, no map: release bundle's `install.sh`, host command `open-revoke`, `lib/*.sh` (POSIX sh); `helm/open-revoke/` Helm chart (own AGENTS.md), `helm/artifacthub-repo.yml` (Artifact Hub metadata).
- `scripts/`, no map: `release.sh` (changelog, tag), `build-release.sh` (images and bundle). Skill `skills/backend/releases.md`.
- `docker/`, no map: `entrypoint.sh` (`python -m app.db migrate`, then supervisor), `supervisord.conf`, `caddy/Caddyfile`, `browser/` (own AGENTS.md).
- `docs/`: own AGENTS.md. Click recipes, self-hosting, `openapi.json`, `connectors/`.
- `ee/`, no map: `LICENSE` only.
- `skills/`: features that span several files (list below).

Plans and business data never go into this repo: it is public.

## Architecture in one paragraph

The panel (`web`) calls `/api/...` on its own origin; Next.js proxies it to
FastAPI (`api`). Business logic lives in `backend/app/services/`, endpoints in
`backend/app/api/` stay thin. Long work runs as Temporal workflows in
`worker`: `SyncConnectionWorkflow` (accounts of one connection, scheduled per
connection), `ExecuteActionWorkflow` (write actions with read-back
verification), scan and exchange-rate workflows. Connectors implement
`backend/app/connectors/base.py` and register in `backend/app/connectors/registry.py`; browser connectors
talk to the `browser` container over CDP. Connector secrets are encrypted
with `OPEN_REVOKE_SECRET_KEY` (Fernet).

## Checks before "done"

`dc` below is `docker compose -f compose.dev.yaml`, run in this folder
(maintainers may have a wrapper such as `dock exec api ...`).

```bash
dc exec api ruff check .
dc exec api ruff format --check .
dc exec web bun run lint
dc exec web bun run typecheck
```

A noticeable change also adds a line to `CHANGELOG.md`.

Then check the behaviour in the running stack: call the endpoint
(`curl http://localhost:18411/...`), run the workflow, open the
page (http://localhost:18410/people). After an endpoint or schema change refresh the
contract:
`dc exec -T api python scripts/export_openapi.py > docs/openapi.json`,
then update `frontend/src/lib/api/types.ts` by hand.

## Secrets

`.env` in this folder (git-ignored, template `.env.example`) holds
`OPEN_REVOKE_SECRET_KEY`. Both stacks read it. Losing the key makes stored
connector secrets unreadable. Real admin credentials for tests stay in a
password manager, never in the repo or in fixtures.

## Task to skill

Procedures in `.agents/skills/` (Claude Code finds them through the
`.claude/skills` symlink). Feature skills are in the next section.

| Task | Skill |
|---|---|
| unfamiliar area, 3+ unread files, backend + frontend | [explore](.agents/skills/explore/SKILL.md) (subagent `open-revoke-explore`) |
| bug, error, stuck workflow, wrong data | [diagnose](.agents/skills/diagnose/SKILL.md) |
| end of every change: checks, stack run, local commit | [verify](.agents/skills/verify/SKILL.md) |
| `AGENTS.md`, folder map, skill, subagent, hook | [harness](.agents/skills/harness/SKILL.md) |

## Skills

Before changing a feature listed here, read its skill. When you change code a
skill covers, update the skill in the same commit. New skill: a file in
`skills/backend/` or `skills/frontend/` with what the feature does, its files,
the data flow and how to extend it; add it to this list. Skills are in English.

Backend (`skills/backend/`):

- [auth.md](skills/backend/auth.md): panel sign-in: first admin, invites, self sign-up, password, 2FA, sessions, reset links, CLI
- [exchange-rates.md](skills/backend/exchange-rates.md): daily rates, costs in the organization currency
- [domain-model.md](skills/backend/domain-model.md): domain model, account matching, costs, actions, API conventions
- [app-discovery.md](skills/backend/app-discovery.md): Google Workspace scan of third-party sign-ins, risk, `/discovery`
- [app-catalog.md](skills/backend/app-catalog.md): known SaaS apps (`backend/app/catalog/apps.json`), matching, logos
- [setup-checklist.md](skills/backend/setup-checklist.md): `/welcome` questions, dashboard checklist
- [google-cloud-setup.md](skills/backend/google-cloud-setup.md): automatic Google Cloud setup in the shared browser (Discovery "Automatic")
- [actions.md](skills/backend/actions.md): write actions, `ExecuteActionWorkflow`, read-back verification
- [docker-single-image.md](skills/backend/docker-single-image.md): Dockerfile targets, self-hosting image, `compose.dev.yaml`
- [releases.md](skills/backend/releases.md): versions, release build, installer, `open-revoke` command, update check, Helm chart
- [click-recipes.md](skills/backend/click-recipes.md): writes in apps without an API: format, runner, fake panel
- [browser.md](skills/backend/browser.md): `browser` container, CDP, live view, `BrowserSession`, header capture
- [new-connector.md](skills/backend/new-connector.md): app connector, secrets, account sync, `SyncConnectionWorkflow`
- [new-endpoint.md](skills/backend/new-endpoint.md): new REST endpoint (router, service, schema)
- [new-model.md](skills/backend/new-model.md): SQLAlchemy model, Alembic migration, seed data
- [new-workflow.md](skills/backend/new-workflow.md): Temporal workflow and activities
- [temporal-local-stack.md](skills/backend/temporal-local-stack.md): local Temporal server without Web UI
- [timezone.md](skills/backend/timezone.md): time zone in backend services
- [mcp.md](skills/backend/mcp.md): MCP server at `/api/mcp`, personal API tokens
- [access-requests.md](skills/backend/access-requests.md): request policy, manager and admin steps, `/requests`, CSV, Slack buttons
- [access-profiles.md](skills/backend/access-profiles.md): apps with roles, assignment with onboarding batch, missing and extra access
- [slack-agent.md](skills/backend/slack-agent.md): Slack bot for access requests, AI model settings, Socket Mode runner

Frontend (`skills/frontend/`):

- [auth.md](skills/frontend/auth.md): sign-in pages, `AuthGate`, 2FA, settings
- [currency.md](skills/frontend/currency.md): amounts in the organization currency
- [new-page.md](skills/frontend/new-page.md): new page (App Router)
- [ui-kit.md](skills/frontend/ui-kit.md): read before any screen work: shared components only, tokens, loading, motion
- [new-component.md](skills/frontend/new-component.md): UI component (shadcn and CVA)
- [api-communication.md](skills/frontend/api-communication.md): `/api` proxy, types, React Query, errors
- [pages.md](skills/frontend/pages.md): pages, their hooks, connection form from JSON Schema
- [timezone.md](skills/frontend/timezone.md): date formatting
