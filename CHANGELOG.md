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

## [0.1.1-rc.2] - 2026-11-26

### Changed

- Images are renamed to `ghcr.io/take-group/openrevoke` and `ghcr.io/take-group/openrevoke-browser`,
  and are also published on Docker Hub as `takegroup/openrevoke` and `takegroup/openrevoke-browser`.
  If you set `OPEN_REVOKE_IMAGE` or `OPEN_REVOKE_BROWSER_IMAGE` in `.env`, change them to the new names.

- `.env` gets `REDIS_PASSWORD`. `install.sh` generates it; `open-revoke update`, `start` and
  `restart` generate it once for an older `.env`. Updating from 0.1.x with the old command leaves
  Redis without a password until the next `open-revoke restart` (`open-revoke doctor` says so).
  Helm: the chart's Secret gets `REDIS_PASSWORD` by itself; a Secret of your own
  (`secrets.existingSecret`) needs the key `REDIS_PASSWORD` (letters and digits) before the upgrade.
- Fewer third-party packages: the Google service account token is signed with `cryptography`
  (no `google-auth`), the API runs on plain `uvicorn` (no uvloop, httptools, PyYAML), and the panel
  no longer installs the shadcn CLI (about 110 packages fewer).

### Security

- Redis needs a password (`REDIS_PASSWORD`) in Docker Compose and in the Helm chart.
- Docker Compose: PostgreSQL, Redis and Temporal moved to an internal network without a route out
  that only the app joins. The shared browser, which opens any SaaS page, can no longer reach
  them. Temporal's open source server has no password; this network is what protects it.
- `TELEMETRY.md` describes the hourly update check against GitHub and how to turn it off.
- SLSA Build Level 3 provenance is now made with GitHub artifact attestations from the reusable
  workflow `release-publish.yml` instead of the unmaintained `slsa-github-generator`. Check it with
  `gh attestation verify --signer-workflow Take-Group/openrevoke/.github/workflows/release-publish.yml`
  (commands in the release notes); the images' `cosign` identity is `release-publish.yml` too.
  Release 0.1.0 keeps its `.intoto.jsonl` for `slsa-verifier`.
- A saved connector token (SCIM, GitHub Enterprise) or AI key is no longer sent to a changed base URL:
  changing the URL needs the secret again. Pending and approved writes of a connection are cancelled
  when its target changes.
- A role the requester typed (for example `admin`) is never approved automatically by an `automatic`
  app policy or an access profile: an admin approves it, unless one of the person's access profiles
  gives that role.
- An AI fix of any step of a removal click recipe waits for an admin's approval.
- 2FA: wrong codes count per account over all sign-in attempts; a sign-in ticket works once and only
  for its own step (a Settings enrollment ticket cannot skip 2FA).
- The per-account sign-in limit counts only wrong passwords; self sign-up is limited per address too;
  an e-mail with two `@` is refused; removing or demoting the last admin cannot race.
- App website and admin links accept only `http(s)` (no `javascript:` links in the panel).
- The panel sends `X-Frame-Options`, `frame-ancestors`, `nosniff` and `Referrer-Policy`; the Caddy
  profile adds HSTS.
- `.env` stays mode 600 when the installer or `open-revoke rotate-key` rewrites it.
- CSV exports escape formulas after leading spaces or line breaks too.

## [0.1.0] - 2026-11-26

### Fixed

- Versions compare in SemVer order everywhere: a release is newer than its pre-releases and
  `rc.10` is newer than `rc.2` (the update notice in the panel, `open-revoke update`, the release
  scripts).

### Security

- E-mail validation no longer slows down on crafted input (found by CodeQL); app logos and the
  browser live view serve only files from their own lists.
- Dependabot waits 7 days after a dependency's release before proposing it (security updates do
  not wait).

## [0.1.0-rc.2] - 2026-11-26

### Fixed

- Release workflow: the Trivy gate scans for vulnerabilities only; its secret scanner took the text
  `"type": "service_account"` for a Google key. 0.1.0-rc.1 stopped there and was never published.

## [0.1.0-rc.1] - 2026-11-26

### Security

- Releases are immutable, carry SLSA Build Level 3 provenance for the images and every release
  file, and stop on a fixable CRITICAL vulnerability found by Trivy in either image. The release
  notes show how to verify each of them.
- PostgreSQL 18.7: fixes in the base image's Kerberos libraries (CVE-2026-107364 and others).
- `open-revoke rotate-key` replaces `OPEN_REVOKE_SECRET_KEY` and re-encrypts every stored secret;
  the key can also come from a file (`OPEN_REVOKE_SECRET_KEY_FILE`).
- The audit log is append-only in the database, records failed sign-ins with the address, and
  exports to CSV or JSON Lines (Audit page, `GET /api/audit/export`).
- Containers run with `no-new-privileges`; the app, browser and Temporal containers with no Linux
  capabilities (Caddy keeps only the one to bind ports 80 and 443). The app image runs as uid
  10001. The Helm chart sets restricted security contexts and network policies for PostgreSQL,
  Redis and Temporal.
- Security documentation for your review: docs/security/overview.md and the threat model.
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
