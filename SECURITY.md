# Security policy

Open Revoke holds the keys to a company's SaaS tools: API tokens, SCIM tokens, a Google service
account key and signed-in admin sessions in a shared browser. We treat security reports as the most
important kind of report.

How Open Revoke protects that data, and the risks it does not cover:
[docs/security/overview.md](docs/security/overview.md) and
[docs/security/threat-model.md](docs/security/threat-model.md).

## Supported versions

Open Revoke is in beta. Only the latest MINOR release line (for example `0.4.x` when `0.4.2` is the
newest release) gets security fixes. Older lines do not. Update with `open-revoke update`; the panel
shows admins a warning when a newer release carries a `Security` section in its notes.

| Version | Security fixes |
|---|---|
| Latest MINOR release (`X.Y.*`) | Yes |
| Older releases | No: update first |
| Unreleased `main` | Fixed on `main`, released in the next PATCH |

## Report a vulnerability

Report it privately through GitHub:

1. Open the [Security tab](https://github.com/Take-Group/openrevoke/security) of the repository.
2. Click **Report a vulnerability**
   ([direct link](https://github.com/Take-Group/openrevoke/security/advisories/new)).
3. Describe the problem, the version (`open-revoke version`), how to reproduce it and what an
   attacker gains.

Do not open a public issue, pull request or discussion for a vulnerability, and do not put exploit
details in one. If you are not sure whether something is a vulnerability, report it privately
anyway.

What to expect:

- We aim to reply within 7 days.
- We work on the fix in a private advisory and may invite you to it.
- We publish the advisory and a release with a `Security` section in `CHANGELOG.md` when the fix
  is out. We credit you in the advisory unless you ask us not to.

Please give us a reasonable time to release a fix before you disclose the issue in public.

## Scope

In scope:

- **The panel and the API**: authentication (password, two-factor, sessions, invites, the setup
  link, password reset links), authorization between admins and members, CSRF, host header and
  origin checks, anything that lets a person read or change data they should not.
- **Connector secret handling**: how API tokens, SCIM tokens and service account keys are stored
  (encrypted with `OPEN_REVOKE_SECRET_KEY`), shown, logged or sent anywhere.
- **The shared browser**: any way to reach the `browser` container, its CDP port or its noVNC live
  view without a signed-in admin session, or to read the sessions it holds.
- **Write actions**: a way to make Open Revoke create, remove or change an account without the
  approval it requires.
- **The installer and the `open-revoke` command** (`install.sh`, `deploy/`): file permissions,
  secret generation, checksum and signature checks, backups, updates and rollbacks.
- **Release artifacts**: the container images on `ghcr.io/take-group/`, the release bundle and
  their signatures.

Out of scope:

- Vulnerabilities in the SaaS apps Open Revoke connects to. Report those to their vendors.
- Problems that need an attacker who already has root on the server, the Docker socket, the `.env`
  file or a copy of the `browser-profile` volume. Those give full control by design (see below).
- Reports from automated scanners without a working impact, missing security headers without an
  attack, and denial of service by sheer request volume.
- Deployments that publish ports this project tells you not to publish.

## What you must know when you run Open Revoke

- **The `browser-profile` Docker volume holds signed-in admin sessions** of the apps you connect
  through the browser (Slack, Claude, ChatGPT and others). Whoever has a copy of that volume has
  those sessions. Never copy it to another machine, never put it in a shared backup, and never mount
  it into another container. `open-revoke backup` leaves it out unless you pass `--with-browser`;
  keep such a backup as secret as the sessions themselves.
- **Never publish the browser's noVNC or CDP ports.** They have no sign-in of their own. The release
  stack publishes only the panel port (default `127.0.0.1:18410`); the live view of the browser goes
  through the API, for signed-in admins only. Do not add `ports:` to the `browser` service and do
  not route it through your reverse proxy.
- **`OPEN_REVOKE_SECRET_KEY` encrypts the connector secrets** in the database. Anyone with the key
  and a database dump can read every stored token. Keep `.env` at mode `600` (the installer does
  this) and store a copy of the key in a password manager, apart from your database backups. If you
  lose the key, the stored secrets cannot be read and you have to enter them again. Replace a key
  that may have leaked with `open-revoke rotate-key`: it re-encrypts every stored secret.
- **The audit log is append-only.** Every change, sign-in and failed sign-in (with the address) is
  recorded; the database refuses to update or delete entries. Export it from the Audit page or
  `GET /api/audit/export` (CSV or JSON Lines) into your own archive or SIEM.
- **Bind the panel to `127.0.0.1`** and put an HTTPS proxy in front of it (the bundled Caddy with
  `--proxy caddy`, your own proxy, Cloudflare or Tailscale). Do not expose plain HTTP to the
  internet.
- **Keep it updated.** The browser image ships Chromium from Debian. Its security patches arrive as
  Open Revoke PATCH releases.
- **Verify what you download.** Every release lists SHA-256 sums of its files in `SHA256SUMS`.
  The release notes show how to check the `cosign` signatures of the images, the Helm chart and
  `SHA256SUMS`, the SLSA Build Level 3 provenance of the images and files (`slsa-verifier`), and
  the GitHub release attestation (`gh release verify`). Releases are immutable: once published,
  their files and tag cannot change.

## How we build releases

- Releases are built only by GitHub Actions from a `vX.Y.Z` tag, on GitHub-hosted runners. Images
  are pushed only after the install, update, rollback and Kubernetes tests pass.
- Both images are scanned with Trivy before they are pushed. A CRITICAL vulnerability with a fixed
  version stops the release; accepted findings are listed with a reason in `.trivyignore`.
- Images carry an SBOM and build provenance, are signed with `cosign` (keyless, Sigstore), and get
  SLSA Build Level 3 provenance from `slsa-framework/slsa-github-generator`.
- Every workflow action is pinned to a commit SHA. CodeQL, zizmor, dependency review and OpenSSF
  Scorecard check the code and the workflows; Dependabot proposes dependency updates weekly.
