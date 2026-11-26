# Threat model

What Open Revoke protects, who could attack it, how, and what stops them. Read it before you
deploy Open Revoke, and before you change authentication, secrets, the shared browser, write
actions or the release pipeline. Report a gap you find through [SECURITY.md](../../SECURITY.md).

Method: assets, trust boundaries, then threats per boundary in the STRIDE categories (Spoofing,
Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege). Each
threat names the control that exists today, or says plainly that the risk is accepted.

## What Open Revoke is, for this model

A self-hosted application that a company runs on its own server or Kubernetes cluster. It holds
credentials to the company's SaaS tools (Google Workspace, GitHub, Slack, SCIM endpoints and
others) and uses them to read who has an account and to create or remove accounts. For apps
without an API it drives a Chromium in which an admin has signed in to the app's admin panel.

There is no Open Revoke cloud: the maintainers never see a deployment's data. What leaves a
deployment is listed in [TELEMETRY.md](../../TELEMETRY.md).

## Assets

| Asset | Where it lives | Impact if stolen or changed |
|---|---|---|
| Connector secrets: API tokens, SCIM tokens, Google service account keys, OAuth refresh tokens | PostgreSQL, Fernet-encrypted (`OPEN_REVOKE_SECRET_KEY`) | Admin access to the company's SaaS tools |
| Signed-in admin sessions of SaaS panels | `browser-profile` volume (Chromium profile), not encrypted by Open Revoke | Same as above, for the apps connected through the browser |
| `OPEN_REVOKE_SECRET_KEY` | `.env` (mode 600) or a Kubernetes Secret | Decrypts every stored secret together with a database copy |
| Panel accounts: Argon2id password hashes, TOTP secrets (encrypted), session and API token hashes (SHA-256) | PostgreSQL | Control of Open Revoke, and through it of the SaaS tools |
| Inventory: people, accounts, costs, access requests | PostgreSQL | Personal data of employees, the company's tool list |
| Audit log | PostgreSQL, append-only | Evidence of who did what |
| Release artifacts: images, install bundle, Helm chart | ghcr.io, GitHub Releases | Code execution on every deployment that installs them |

## Trust boundaries

```
 people's browsers ──HTTPS──> reverse proxy ──> app container ────────> SaaS APIs (internet)
 (admins, members)            (Caddy / own)     panel :3000              │
                                                API   :8000              │ CDP :9223 (compose network)
 Slack (Socket Mode) <─────────────────────────> worker                   ▼
                                                  │                    browser container
                                     PostgreSQL, Redis, Temporal         Chromium + admin sessions
                                     (internal network only)              ──> SaaS admin panels
```

1. **Internet to panel.** The only published port is the panel (`127.0.0.1:18410` by default,
   behind a reverse proxy). The API and the browser's live view are reached through the panel.
2. **Panel and API to the data stores.** PostgreSQL, Redis and Temporal publish no port; in
   Kubernetes, network policies limit them to the pods that use them.
3. **App to the browser container.** CDP and noVNC have no authentication. Only the app reaches
   them (compose network; a Kubernetes network policy).
4. **App and browser to SaaS tools.** Outbound HTTPS with the stored credentials.
5. **Third-party content into Open Revoke.** Data from SaaS APIs, SaaS web pages (click recipes),
   Slack messages and the language model's answers.
6. **Maintainers to deployments.** Release images and scripts, built by GitHub Actions.

## Threats and controls

### 1. Internet to panel

| Threat | Control | Residual risk |
|---|---|---|
| S: password guessing | Argon2id; sign-in limits per address (50 / 15 min), per e-mail from one address (10) and per e-mail overall (100); optional TOTP; failed sign-ins in the audit log with the address | 2FA is optional. The address comes from the last `X-Forwarded-For` entry: a proxy that does not set it makes every client one address |
| S: stolen session cookie | Random 32-byte token, only its SHA-256 stored; `HttpOnly`, `SameSite=Lax`, `Secure` with an https `PUBLIC_URL`; sessions revoked on password change and user removal | A cookie stolen from an admin's machine works until it expires (default 7 days) |
| T: cross-site request forgery | Unsafe requests with a cookie need the `X-Open-Revoke-Client` header, which a cross-site form cannot set | |
| S: DNS rebinding, host header attacks | `ALLOWED_HOSTS` check on `Host` and `X-Forwarded-Host` | |
| E: member reaching admin functions | Every panel route is admin-only except `/api/me`; API tokens act as their owner, `read` tokens get safe methods only | |
| S: stolen API token (MCP, scripts) | Only its SHA-256 stored, revocable, `last_used_at` shown | No expiry date yet |
| I: setup link of a fresh install | One-time token, printed only on the server, refused after the first admin exists | Anyone with the link before the admin uses it becomes admin |
| D: request floods | Not handled by Open Revoke | Put rate limiting in your proxy if the panel is public |

### 2. Data stores

| Threat | Control | Residual risk |
|---|---|---|
| I: database dump or backup leaks | Connector secrets, TOTP secrets, AI and Slack keys are Fernet-encrypted; passwords Argon2id; tokens SHA-256 | A dump together with `.env` reveals everything: `open-revoke backup` puts both in one file, keep it like a password |
| I: key leak | `open-revoke rotate-key` re-encrypts every stored secret with a new key | Rotation does not invalidate the SaaS credentials themselves: rotate those in the SaaS tools too |
| T, R: rewriting history | A database trigger refuses `UPDATE`, `DELETE` and `TRUNCATE` on `audit_event`; export to CSV or JSON Lines for an outside archive | The table owner can drop the trigger; export regularly to a system admins of Open Revoke cannot change |
| S, I: other containers on the host reaching Redis or Temporal | No published ports; Kubernetes network policies | Redis and Temporal have no password: anything on the compose network or in the namespace that the policies allow can use them |

### 3. App to the browser container

| Threat | Control | Residual risk |
|---|---|---|
| I, E: someone drives the signed-in Chromium | CDP and noVNC are not published; the live view goes through the API for signed-in admins only, same-origin checked | Anyone who reaches port 9223 or 6080 controls the sessions: never publish them |
| E: a malicious web page escapes Chromium | The browser opens only SaaS admin panels; the container runs as an unprivileged user with no capabilities and `no-new-privileges` | Chromium runs with `--no-sandbox` (Docker's default seccomp profile blocks the namespaces its sandbox needs): the container is the only isolation. Keep the image updated, Chromium fixes ship as PATCH releases |
| I: the profile volume is copied | Excluded from `open-revoke backup` unless `--with-browser` | Not encrypted at rest by Open Revoke: use disk encryption on the host |

### 4. Writes to SaaS tools

| Threat | Control | Residual risk |
|---|---|---|
| T: an account removed or created by mistake | Write actions need an admin's approval (access requests can be pre-approved per app or by an access profile, never removals); writes switch off when a connection's target changes; a sync that would remove more than 30% of accounts stops | An admin who approves the wrong action |
| T: wrong person matched by e-mail | Matching by primary e-mail and aliases; manual matches win; every write is verified by reading the account list again | |
| R: who approved a removal | `action.created_by`, `approved_by` and the audit log | |

### 5. Third-party content

| Threat | Control | Residual risk |
|---|---|---|
| T: prompt injection through a SaaS page while the AI repairs a click recipe | A fix for an irreversible step (a removal) waits for an admin's approval; every fix is listed and can be reverted | A fix for a reversible step applies at once |
| T: prompt injection through a Slack message to the access-request agent | The model only files a request for the person who wrote; the app's request policy and the manager or admin decide | |
| T: CSV injection in exports | Cells that start with `=`, `+`, `-`, `@` are prefixed with `'` | |
| T: malicious app logo (SVG) | SVG checked on upload, served with `nosniff` and a restrictive CSP | |

### 6. Supply chain

| Threat | Control | Residual risk |
|---|---|---|
| T: a modified image or install script | Built only by GitHub Actions from a tag; images signed with cosign (keyless); SBOM and SLSA Build Level 3 provenance; `SHA256SUMS` signed; immutable GitHub releases; verification commands in every release's notes | Verification is up to the person who installs |
| T: a compromised dependency or action | Lockfiles; Dependabot; actions pinned to commit SHAs; Trivy blocks a release with a fixable CRITICAL vulnerability; CodeQL, zizmor, dependency review, OpenSSF Scorecard | A malicious release of a dependency that no scanner knows yet |
| T: tampered release tag | Tag ruleset: release tags cannot be moved or deleted; `main` cannot be force-pushed | Maintainers push to `main` without a second reviewer |

## What the operator must do

- Bind the panel to `127.0.0.1` and put HTTPS in front of it; set `X-Forwarded-For` in your proxy.
- Never publish the browser's ports. Never copy the `browser-profile` volume.
- Keep `.env` and backups like passwords, apart from each other where you can; store the key in a
  password manager. Encrypt the host's disk.
- Turn on 2FA for every admin; give SaaS credentials the narrowest scopes the connector docs list.
- Export the audit log to a system outside Open Revoke.
- Update when a release has a `Security` section; verify releases before installing.

## Known gaps

Planned, not built: single sign-on (OIDC, SAML) for the panel, enforced 2FA for admins, expiring
API tokens, a Redis password, encryption of the browser profile at rest.
