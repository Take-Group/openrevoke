# Security overview

Answers to the questions a security team asks before it approves Open Revoke. Details and the
reasoning behind them: [threat-model.md](threat-model.md). Reporting a vulnerability:
[SECURITY.md](../../SECURITY.md).

## Hosting and data location

- Self-hosted only: Docker Compose on one server or the Helm chart on Kubernetes. All data stays in
  the deployment's PostgreSQL and volumes, in the region and network you choose.
- The maintainers run no service that receives your data. Outbound traffic: the SaaS APIs and admin
  panels you connect, GitHub (hourly release check, can be turned off), one anonymous event after
  the first setup (can be turned off; [TELEMETRY.md](../../TELEMETRY.md)), the exchange-rate API,
  the Slack workspace and the language model provider, only if you connect them.
- Source code: MIT licence, public at https://github.com/Take-Group/openrevoke.

## Data stored

People (name, e-mail, manager, department, job title), their accounts in SaaS tools, prices,
access requests and their decisions, write actions, an audit log, panel users. No passwords of
employees; no content of the SaaS tools beyond account lists, roles and, for some apps, billing.

## Identity and access

- Panel sign-in: e-mail and password (Argon2id, at least 12 characters), optional TOTP 2FA,
  invites, self sign-up that an admin can turn off or approve per account (or auto-approve for
  the company's domains). Single sign-on: not yet.
- Roles: `admin` (everything) and `user` (own accounts and access requests; managers decide their
  reports' requests).
- Sessions: random tokens stored as SHA-256, `HttpOnly` and `SameSite=Lax` cookies, `Secure` over
  HTTPS, revoked on password change. Personal API tokens (REST and MCP) with `read` or `write`
  scope, stored as SHA-256, revocable.
- Brute force: limits per address, per e-mail from one address and per e-mail.

## Encryption

- In transit: HTTPS terminated by the bundled Caddy (Let's Encrypt) or your proxy; SaaS calls over
  HTTPS; database TLS for an external PostgreSQL in Kubernetes.
- At rest: connector secrets, 2FA secrets and stored API keys are encrypted with Fernet
  (AES-128-CBC with HMAC-SHA256) under `OPEN_REVOKE_SECRET_KEY`, which you hold. `open-revoke
  rotate-key` replaces the key and re-encrypts. The database and volumes rely on the host's disk
  encryption.

## Logging and monitoring

- Append-only audit log of every change, sign-in and failed sign-in with the source address; the
  database refuses edits and deletions. Export as CSV or JSON Lines from the panel or
  `GET /api/audit/export` into your SIEM or archive.
- Container logs to stdout (Docker or Kubernetes logging).

## Changes in your SaaS tools

Removals and new accounts are write actions an admin approves. The one exception is an access
request for an app whose request policy an admin set to automatic, or that an access profile
marks as pre-approved; even then the app's connection must have "Allow writes" on. Every write is checked by reading the account list again. A sync that would remove
more than 30% of an app's accounts stops.

## Vulnerability management

- Dependencies: lockfiles, weekly Dependabot updates, a daily Trivy scan of the repository, and a
  Trivy scan of both images in every release (a fixable CRITICAL stops the release).
- Code: CodeQL, zizmor for the CI workflows, dependency review, OpenSSF Scorecard.
- Fixes: security releases carry a `Security` section; the panel tells admins about them. Only the
  latest MINOR line gets fixes ([SECURITY.md](../../SECURITY.md)).
- Reports: private vulnerability reporting on GitHub, first answer within 7 days.

## Release integrity

Releases are built only by GitHub Actions from a tag. Images and `SHA256SUMS` are signed with
cosign (keyless, Sigstore), images carry an SBOM, images and release files carry SLSA Build Level
3 provenance, GitHub releases are immutable, and every workflow action is pinned to a commit. The
commands to verify a release are in its notes.

## Hardening of the deployment

- Compose: one published port (the panel, `127.0.0.1` by default), `no-new-privileges` for every
  container, no Linux capabilities for the app, browser and Temporal containers, non-root users.
- Kubernetes: restricted security contexts (non-root, no capabilities, `RuntimeDefault` seccomp)
  except PostgreSQL's entrypoint, network policies around the browser, PostgreSQL, Redis and
  Temporal, no service account token.

## Certifications

Open Revoke is software you run, so certifications such as ISO 27001 or SOC 2 apply to your
organization's operation of it, not to the code. The controls above are meant to support yours:
access control, audit trail, encryption, change approval and offboarding evidence.
