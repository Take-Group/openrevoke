# Skill: releases, installer, updates

What exists today and how to change it. The GitHub release workflow (`.github/workflows/release.yml`:
multi-arch images, SBOM, signing, install and update tests) runs once the repo is on GitHub.

## What it does

- **One product version.** The git tag `vX.Y.Z` is the only source. `scripts/build-release.sh`
  passes it to the image (`ARG OPEN_REVOKE_VERSION`); the backend reads it as
  `settings.version` (`OPEN_REVOKE_VERSION`, `dev` in the local stack). `GET /health` and
  `GET /api/system/version` return it; the user menu shows it to admins. `pyproject.toml` and
  `package.json` keep `0.1.0`: they are not published.
- **CHANGELOG.md.** Every change people who run Open Revoke notice adds a line under
  `[Unreleased]`. `scripts/release.sh` turns the section into `## [X.Y.Z] - date`, commits
  `Release X.Y.Z` and tags `vX.Y.Z` (no push).
- **Release bundle.** `scripts/build-release.sh X.Y.Z` builds `ghcr.io/take-group/open-revoke`
  and `open-revoke-browser` for this machine's platform and writes
  `dist/releases/download/vX.Y.Z/` (bundle tar.gz, `install.sh`, `SHA256SUMS`, `VERSION`) plus
  `dist/releases/latest/download/VERSION`: the same paths as GitHub Releases, so the scripts
  read a local directory with `OPEN_REVOKE_RELEASES_URL=file://...`.
- **Installer** (`deploy/install.sh`): checks Docker and Compose, ports, disk and RAM; downloads
  and checks the bundle; writes `.env` (generated `OPEN_REVOKE_SECRET_KEY` and
  `POSTGRES_PASSWORD`, `PUBLIC_URL`, `TZ` from the host, `COMPOSE_PROJECT_NAME`, port);
  links `open-revoke` into PATH; starts; prints the setup link. Never overwrites an install.
- **Host command** (`deploy/open-revoke` + `deploy/lib/`): `status`, `version`, `update`,
  `rollback`, `backup`, `restore`, `doctor`, `logs`, `setup-link`, `admin reset-link`, `start`,
  `stop`, `restart`, `uninstall`. Logic that depends on the version runs in the image:
  `python -m app.ops version | preflight | in-flight` (JSON on stdout).
- **Update** (`deploy/lib/update.sh`): release notes between the versions (and a warning for
  `### Breaking`), images, `app.ops preflight` with the new image, waits up to 10 min for write
  actions in flight, backup, saves the old bundle in `releases/<old>/`, puts the new files in,
  adds new `.env.example` keys, starts, waits for healthy; otherwise rolls back (files and
  database). `rollback` undoes the last update from `.update-state`.
- **Update check**: `CheckForUpdateWorkflow` on schedule `update-check-hourly` (30 min jitter)
  asks `OPEN_REVOKE_UPDATE_URL` (GitHub "latest release": no drafts, no pre-releases) and keeps
  the answer in Redis (`services/update_check.py`). `UpdateNotice` in the panel shows admins a
  newer release; a `### Security` heading in the release notes makes it a warning. Off with
  `OPEN_REVOKE_UPDATE_CHECK=false` and for `dev` builds. 404 (no repo yet) means "no news".
- **Telemetry**: after `POST /api/auth/setup` commits, a background task posts
  `{"event": "setup_completed", "version": ...}` to `OPEN_REVOKE_TELEMETRY_URL`
  (`https://openrevoke.com/api/v1/telemetry`, the website sends it to Telegram;
  `services/telemetry.py`). Nothing else, no id: the setup runs once per database. Release
  builds only; off with `OPEN_REVOKE_TELEMETRY=false`. A new field or event changes
  `TELEMETRY.md` in the same commit.
- **Setup link**: `/api/auth/setup` needs the token of a link printed on the server. The API
  makes a new one at every start while no user exists (log line `Open Revoke setup link:`);
  `python -m app.cli setup-link` (`open-revoke setup-link`) makes a new one. SHA-256 in Redis
  (`services/auth/setup_link.py`); Redis has no volume, so after a Redis restart run
  `setup-link` again. The setup page checks the token first (`POST /api/auth/setup/check`).
- **Time zone**: nothing is baked into the images. `TZ` in `.env` (from the host, default UTC)
  goes to every container; the panel uses the browser's zone until it knows the organization's.

## Files

- `CHANGELOG.md`, `scripts/release.sh`, `scripts/build-release.sh`
- `deploy/install.sh`, `deploy/open-revoke`, `deploy/lib/{common,backup,update}.sh`
- `compose.yaml` (images, official PostgreSQL and Redis), `compose.build.yaml`, `Dockerfile`
- `backend/app/ops.py`, `backend/app/services/{update_check,system_info,maintenance}.py`,
  `backend/app/services/auth/setup_link.py`, `backend/app/api/system.py`,
  `backend/app/temporal/update_check_{workflow,activities,schedule}.py`
- `frontend/src/components/layout/update-notice.tsx`, `frontend/src/hooks/use-system.ts`,
  `frontend/src/components/auth/setup-view.tsx`

## Try a release locally

```bash
cd open-revoke
scripts/build-release.sh 0.1.0
OPEN_REVOKE_RELEASES_URL=file://$PWD/dist/releases \
  sh dist/releases/download/v0.1.0/install.sh --yes --dir /tmp/or-test --name or-test --port 18420 --no-link
/tmp/or-test/open-revoke status
```

`--name` keeps it apart from the local dev stack (both would be `open-revoke`). Remove it with
`/tmp/or-test/open-revoke uninstall --purge --yes`.

## How to extend

- **A new file the stack mounts**: add it to `compose.yaml` and to the copy step in
  `scripts/build-release.sh` (it fails when the bundle's compose still points at `./backend/`
  or `./docker/`).
- **A new `.env` variable**: give it a default in `compose.yaml`. If it must be set, put
  `KEY=value` (uncommented) into `.env.example`: `update` adds missing uncommented keys to
  existing installs. A required value without a default is a `### Breaking` entry.
- **A check before updating**: add it to `app.ops preflight` (runs with the new image), not
  to the shell script.
- **A new bundle file**: add it to `BUNDLE_FILES` in `deploy/lib/update.sh` and the copy
  step in `scripts/build-release.sh`.

## Traps

- Shell scripts are POSIX sh (macOS and Debian/Ubuntu): no bash arrays, no `[[ ]]`, no
  `sed -i`. Check with `docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck:stable -s sh -x deploy/open-revoke`.
- `docker compose run` of the app runs `entrypoint.sh` (migrations) unless
  `--entrypoint` is set; `update` passes the Python entry point so the check changes nothing.
- Migrations run at container start (`entrypoint.sh` → `python -m app.db migrate`); `update`
  backs up first and `app.ops preflight` with the new image refuses a database it cannot
  migrate. There are no downgrades: `rollback` restores the backup.
