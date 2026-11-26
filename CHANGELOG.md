# Changelog

What changes in each Open Revoke release, for the people who run it. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/) as described in
`skills/backend/releases.md`: a PATCH release never changes the database or
`.env`, a MINOR release may migrate the database by itself, a MAJOR release needs
a manual step listed under **Breaking**.

Every change people notice adds one line under `[Unreleased]` in the same commit.
`scripts/release.sh` turns that section into the release. Sections: `Breaking`
(with the command to run), `Added`, `Changed`, `Fixed`, `Security`.

## [Unreleased]

### Security

- Releases are immutable, carry SLSA Build Level 3 provenance for the images and every release
  file, and stop on a fixable CRITICAL vulnerability found by Trivy in either image. The release
  notes show how to verify each of them.
- PostgreSQL 18.7: fixes in the base image's Kerberos libraries (CVE-2026-107364 and others).
- `open-revoke rotate-key` replaces `OPEN_REVOKE_SECRET_KEY` and re-encrypts every stored secret;
  the key can also come from a file (`OPEN_REVOKE_SECRET_KEY_FILE`).
- The audit log is append-only in the database, records failed sign-ins with the address, and
  exports to CSV or JSON Lines (Audit page, `GET /api/audit/export`).
- Sign-in limits per address and per e-mail from one address: a stranger can no longer lock an
  account out with ten wrong passwords. Your own reverse proxy must set `X-Forwarded-For`
  (docs/self-hosting.md).

### Added

- Access profiles: named sets of apps with a role in each ("Developer"). Assigning one to a person
  previews and creates one onboarding batch with the profile's roles; removing one suggests the
  accounts to remove. Profile and person pages show missing and extra access, the dashboard warns
  when members miss access, and the Onboard page can tick a profile's apps.
- Helm chart for Kubernetes (`oci://ghcr.io/take-group/charts/open-revoke`, docs/kubernetes.md):
  the same services as Docker Compose, generated secrets kept on upgrade, optional ingress and
  external PostgreSQL; the panel's update notice shows the `helm upgrade` command.
- Installer (`install.sh`) and the `open-revoke` command on the server: status, update with a
  database backup and automatic rollback, backup, restore, doctor.
- The panel shows its version, and admins see a notice when a newer stable release is out
  (checked hourly on GitHub; `OPEN_REVOKE_UPDATE_CHECK=false` turns it off).
- Database migrations: the `app` container migrates the database when it starts and refuses a
  database that a newer version already migrated.
- `compose.dev.yaml`: development stack with hot reload and fictional people.
- MCP server at `/api/mcp`: Claude Code, Codex, Cursor and other AI assistants can do everything a
  panel user can (people, apps, connections, offboarding), with a personal API token.
- Personal API tokens (Settings, API and MCP), read-only or read and write, also for the REST API
  (`Authorization: Bearer`).
- Anonymous telemetry: one event (`setup_completed` and the version) when the first admin
  finishes the setup; `TELEMETRY.md` says what is sent, `OPEN_REVOKE_TELEMETRY=false` turns it off.
- People have a manager, a department and a job title: from Google Workspace (manager relation,
  primary organization), from the people CSV (`manager_email`, `department`, `job_title`) or set in
  the panel. A manager set by hand is kept by syncs; a loop of managers is refused. The person page
  shows the reporting line, the people list a Department column and a "No manager" filter, and the
  dashboard warns about people without a manager while an app sends requests to managers.

- Access requests approved by the person's manager: each app's "Who approves requests" policy
  (automatic, manager, manager then admin, admin) routes a request to the manager on
  "Approvals" (`/me/approvals`) or Slack, then to an admin when needed; no manager who can decide
  sends it to an admin with the reason. A justification is required, a rejection needs a comment,
  nobody decides their own request.
- Request history: `/requests` with filters, Export CSV, and `/requests/<id>` with the timeline of
  every decision (who, when, via panel, API or Slack, comment); admins can decide for the manager.
- Managers can ask for access for their reports; "Approved by" on actions.
- Fast inventory: "Add app" starts with a search of the app catalog (name, website, logo and
  the matching connector), "Add several apps" adds many catalog apps in one save, and an app
  can have its own website, category and uploaded logo (PNG, JPEG, WebP or a checked SVG).
- Accounts in bulk: a CSV import for many manual apps at once (with a preview and "Create missing
  apps"), pasted e-mails on a manual app, and "Track" in discovery can add accounts for the
  people who signed in.

### Changed

- The first admin is created only with the setup link printed on the server
  (`open-revoke setup-link`), not by whoever opens a fresh installation first.
- Release images instead of building on the server; official PostgreSQL and Redis images.
- The time zone follows the server (`TZ` in `.env`, set by the installer) instead of
  Europe/Warsaw.
