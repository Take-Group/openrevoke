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

### Added

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

### Changed

- The first admin is created only with the setup link printed on the server
  (`open-revoke setup-link`), not by whoever opens a fresh installation first.
- Release images instead of building on the server; official PostgreSQL and Redis images.
- The time zone follows the server (`TZ` in `.env`, set by the installer) instead of
  Europe/Warsaw.
