# Skill: releases, installer, updates

What exists today and how to change it. The GitHub release workflow (`.github/workflows/release.yml`;
`release-test.yml`: Trivy scan, install, update and Kubernetes tests; `release-publish.yml`:
multi-arch images, SBOM, signing, SLSA provenance) runs only on GitHub.

## What it does

- **One product version.** The git tag `vX.Y.Z` is the only source. `scripts/build-release.sh`
  passes it to the image (`ARG OPEN_REVOKE_VERSION`); the backend reads it as
  `settings.version` (`OPEN_REVOKE_VERSION`, `dev` in the local stack). `GET /health` and
  `GET /api/system/version` return it; the user menu shows it to admins. `pyproject.toml` and
  `package.json` keep `0.1.0`: they are not published.
- **CHANGELOG.md.** Every change people who run Open Revoke notice adds a line under
  `[Unreleased]`. `scripts/release.sh` turns the section into `## [X.Y.Z] - date`, commits
  `Release X.Y.Z` and tags `vX.Y.Z` (no push). Its checks run in the dev stack's containers when the
  stack is up (the host `node_modules` may be stale), else on the host after `bun install`.
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

## Helm chart

- **Where.** `deploy/helm/open-revoke/` (guide for admins: `docs/kubernetes.md`). Same images,
  versions and env as `compose.yaml`: `app` Deployment (1 replica, `Recreate`), `browser`
  StatefulSet (PVC `profile`, `/dev/shm` in memory), PostgreSQL StatefulSet or
  `externalDatabase`, Redis, Temporal. One `values.yaml` key per `app` env var of compose.yaml;
  `values.schema.json` refuses unknown keys.
- **Version.** The chart's version is the product's: `release.yml` runs
  `helm package --version X.Y.Z --app-version X.Y.Z` and writes the image tags of the
  `artifacthub.io/images` annotation; `Chart.yaml` in git keeps `0.1.0`. Image tags default to
  `.Chart.AppVersion`.
- **Secrets.** `templates/secret.yaml` generates `OPEN_REVOKE_SECRET_KEY` (Fernet: `randBytes 32`
  made URL-safe) and `POSTGRES_PASSWORD` once; on upgrade `lookup` reads the existing Secret.
  Resource policy `keep`: uninstall leaves it next to the PVCs. Or `secrets.existingSecret`.
- **Temporal.** No hook Jobs: init containers of the Temporal pod wait for PostgreSQL and run
  `setup-postgres.sh` (idempotent) at every start; an init container of the app pod runs
  `create-namespace.sh`. Hooks would deadlock `helm install --wait` (Helm runs post-install hooks
  after the wait) and break Argo CD. The scripts are a copy in `files/temporal/`; CI diffs it.
- **Install method.** The chart sets `OPEN_REVOKE_INSTALL_METHOD=helm`; `GET /api/system/version`
  returns it as `install_method` and `UpdateNotice` shows `helm upgrade` instead of
  `open-revoke update`.
- **Host names.** The API refuses unknown `Host` headers: the probes send `Host: localhost`, and
  `ALLOWED_HOSTS` lists the app Service's names, which the browser pod uses for the API.
- **Publishing** (`release.yml`): `build-test` packages the chart and installs it on kind with
  the images it built; `chart` pushes the same `.tgz` to `oci://ghcr.io/take-group/charts`, signs
  its digest with cosign and pushes `deploy/helm/artifacthub-repo.yml` with oras as tag
  `artifacthub.io` (skipped while its `repositoryID` is the placeholder); `release` attaches
  `open-revoke-chart-X.Y.Z.tgz` and lists it in `SHA256SUMS`. `ci.yml`: `helm lint --strict`,
  `helm template` through kubeconform (defaults, ingress, external database).

Try it locally (kind, Helm and kubeconform from Homebrew):

```bash
scripts/build-release.sh 0.0.0-helm --out /tmp/or-releases
kind create cluster --name or-helm
kind load docker-image --name or-helm ghcr.io/take-group/open-revoke:0.0.0-helm ghcr.io/take-group/open-revoke-browser:0.0.0-helm
helm install or deploy/helm/open-revoke -n or --create-namespace --set app.image.tag=0.0.0-helm \
  --set browser.image.tag=0.0.0-helm --set app.telemetry=false --wait --timeout 15m
kubectl -n or port-forward svc/or-open-revoke-app 18410:3000
kind delete cluster --name or-helm
```

A new env var of the `app` service in `compose.yaml` gets a value in `values.yaml`, the schema
and `templates/app.yaml`; a new file mounted from `backend/temporal/` gets copied into
`files/temporal/`.

## Files

- `CHANGELOG.md`, `scripts/release.sh`, `scripts/build-release.sh`
- `deploy/install.sh`, `deploy/open-revoke`, `deploy/lib/{common,backup,update}.sh`
- `compose.yaml` (images, official PostgreSQL and Redis), `compose.build.yaml`, `Dockerfile`
- `deploy/helm/open-revoke/` (chart), `deploy/helm/artifacthub-repo.yml`, `docs/kubernetes.md`
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

## Supply chain

- **Actions are pinned to a commit SHA** with the version in a comment
  (`uses: actions/checkout@<sha> # v7.0.1`). Dependabot (`github-actions`) updates both. A new
  action: resolve the SHA of a release tag, never a branch.
- **Base images are pinned by digest** in the `Dockerfile` (`tag@sha256:...`); Dependabot (`docker`)
  moves tag and digest together. A Debian fix in a base image arrives with that update.
- **Trivy** (`release-test.yml`) scans both images before anything is pushed. A CRITICAL with a
  fixed version fails the release: bump the package or base image, or add the CVE to
  `.trivyignore` with a reason and a date to check again. HIGH and CRITICAL go to the Security tab.
  The organization's daily Trivy scan of the repository (lockfiles and base images) is separate.
- **SLSA provenance** (Build Level 3): GitHub artifact attestations (`actions/attest`) made
  inside the reusable workflow `release-publish.yml`, so they are signed with its identity and a
  verifier pins it with `gh attestation verify --signer-workflow
  Take-Group/openrevoke/.github/workflows/release-publish.yml` (GitHub docs: "Using artifact
  attestations and reusable workflows to achieve SLSA v1 Build Level 3"). `tag-and-sign` attests
  the multi-arch index digests and pushes the attestation to ghcr.io; `release-files` attests every
  line of `SHA256SUMS`, and the release job attaches its bundle as
  `open-revoke-X.Y.Z.provenance.sigstore.json` (offline check with `--bundle`). The images'
  cosign identity is `release-publish.yml@refs/tags/vX.Y.Z`; SHA256SUMS and the chart are signed
  by `release.yml`. Keep build and attestation in `release-publish.yml`: an attestation step in
  `release.yml` would drop the provenance to Level 2. `slsa-github-generator` was dropped
  after 0.1.0: it is unmaintained and ran on Node.js 20.
- **Immutable releases** are on in the repository settings: no step may upload to the release
  after it is created, and a broken release is fixed by a new version, never by
  replacing a file. The tag name of a deleted release cannot be used again.
- **Checks on every push**: `codeql.yml`, `workflow-audit.yml` (zizmor, dependency review on pull
  requests), `scorecard.yml` (OpenSSF Scorecard, published to scorecard.dev). Lint workflows locally
  with `actionlint` and `uvx zizmor --offline .github/workflows`.

## Traps

- Shell scripts are POSIX sh (macOS and Debian/Ubuntu): no bash arrays, no `[[ ]]`, no
  `sed -i`. Check with `docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck:stable -s sh -x deploy/open-revoke`.
- `docker compose run` of the app runs `entrypoint.sh` (migrations) unless
  `--entrypoint` is set; `update` passes the Python entry point so the check changes nothing.
- Migrations run at container start (`entrypoint.sh` → `python -m app.db migrate`); `update`
  backs up first and `app.ops preflight` with the new image refuses a database it cannot
  migrate. There are no downgrades: `rollback` restores the backup.
