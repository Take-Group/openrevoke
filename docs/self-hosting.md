# Self-hosting on your own domain

This guide puts Open Revoke on a server under an address like `https://revoke.example.com`.
For a first look on your own computer, "Get started" in the README is enough.

Open Revoke holds signed-in admin sessions of your SaaS tools (in the shared browser) and
connector secrets (in the database). Treat the server like a password manager: few people
with shell access, disk encryption, backups you can restore.

## What reaches the network

One port: the panel (`app`, port 3000 in the container, published on
`127.0.0.1:18410` by default). Everything else stays inside the Docker network:

| Service | Reachable from |
|---|---|
| Panel and API (`/api` goes through the panel) | the published port |
| Live view of the shared browser | the panel, `/api/browser/live/...`, signed-in admins only |
| Browser control (CDP) | the compose network only |

Open Revoke needs no inbound connection from the internet. Google and Slack send the admin's
browser back to the panel after sign-in; their servers never call it. The Slack bot keeps an
outbound connection (Socket Mode). So the panel can stay inside a VPN.

## 1. Configure

With the installer (README, "Get started"), answer its question about the address, or pass
`--url https://revoke.example.com --proxy caddy`: it writes `.env` for you, with generated
secrets and the server's time zone. By hand:

```bash
cp .env.example .env
openssl rand -base64 32 | tr '+/' '-_'   # put it into .env as OPEN_REVOKE_SECRET_KEY=
openssl rand -hex 24                     # put it into .env as POSTGRES_PASSWORD=
```

Set the address people will type, in `.env`:

```bash
PUBLIC_URL=https://revoke.example.com
```

Everything follows `PUBLIC_URL`: invite and password reset links, the "Connect with
Google" redirect, the `Secure` flag of the session cookie, and the host names the API answers
to (it refuses any other `Host` header). When the panel is opened under another address, it
shows a warning with both addresses. Opened by IP or by a host name the API does not know, it
shows an error that names `PUBLIC_URL`.

Open Revoke sends no e-mail and needs no mail server. An admin copies invite and password reset
links from the panel and passes them on; an admin who forgot their own password runs
`docker compose exec app /app/backend/.venv/bin/python -m app.cli reset-link you@company.com`.

## 2. Choose how people reach the panel

### A. Public domain, HTTPS from the bundled Caddy

The DNS record of the domain points at the server, and ports 80 and 443 are open to the
internet (Let's Encrypt checks the domain over port 80).

```bash
docker compose --profile https up -d --build
```

Caddy reads `PUBLIC_URL` as its site address, gets the certificate, renews it, and redirects
http to https. The certificate is in the `caddy-data` volume.

### B. Your own reverse proxy or Cloudflare

Leave the profile off (`docker compose up -d --build`). The panel listens on
`127.0.0.1:18410`; point the proxy there. It must:

- pass the original `Host` header (the API checks it against `PUBLIC_URL`),
- pass WebSocket upgrades: the live view uses `/api/browser/live/websockify`.

nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:18410;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;  # map $http_upgrade in the http block
    proxy_read_timeout 1h;                             # the live view stays open
}
```

Cloudflare Tunnel: `cloudflared tunnel` with the service `http://localhost:18410` and the
public host name of `PUBLIC_URL`. WebSockets work through it. Cloudflare Access in front of the
tunnel adds your company sign-in before the panel's own.

When the proxy runs on another machine, publish the panel on the server's private address:
`OPEN_REVOKE_BIND=10.0.0.5` (or `0.0.0.0`) in `.env`. Plain http then crosses that network.

### C. Private network or VPN

The panel is reachable only inside the company network. You still need HTTPS: browsers send
the password and the session cookie in clear text over http, and Google sign-in refuses it.

- Tailscale: `tailscale serve --bg --https=443 http://127.0.0.1:18410` on the server, and
  `PUBLIC_URL=https://<machine>.<tailnet>.ts.net`. Tailscale issues the certificate.
- An internal name under your public domain (`revoke.int.example.com`, resolved only inside
  the VPN): get the certificate with a DNS challenge (Caddy or certbot with your DNS
  provider's plugin; the bundled Caddy has no DNS plugins) and use setup B.

Google's rules for the "Connect with Google" redirect: https, a domain under a public suffix
(`.com`, `.pl`, `ts.net` qualify; `.internal`, `.local`, `.lan` and bare IP addresses do not),
or plain `http://localhost`. The redirect happens in the admin's browser, so a name that
resolves only inside the VPN works. Where none of this fits, connect Google Workspace with a
service account key (Discovery, "Service account key"): it needs no redirect.

## 3. Create the admin

Only the setup link printed on the server creates the first admin, so a stranger who finds the
address first cannot take the panel. The installer prints it; the `app` log shows a new one at
every start until the setup is done; `open-revoke setup-link` (or
`docker compose exec app /app/backend/.venv/bin/python -m app.cli setup-link`) makes a new one
and the old one stops working. Everyone after the first admin needs an invite.

The setup asks for the organization, the admin account and 2FA, then two questions: where your
people come from (Google Workspace, Microsoft 365, a CSV file or by hand) and where your team
talks (Slack, Teams, neither). The dashboard then lists the next steps for those answers.

## Updating and backups

```bash
open-revoke backup                  # database and .env into backups/; --with-browser adds the sessions
open-revoke update                  # newest release: notes, backup, new version, back if it fails
open-revoke rollback                # undo the last update, database included
```

Admins see a notice in the panel when a newer release is out (the app asks GitHub once an hour;
`OPEN_REVOKE_UPDATE_CHECK=false` in `.env` turns it off). Run from source instead:
`git pull && docker compose -f compose.yaml -f compose.build.yaml up -d --build`.

A backup holds `.env` with `OPEN_REVOKE_SECRET_KEY`: without it the stored connector secrets
cannot be read, so keep backups like passwords. Database migrations run when the new version
starts; `open-revoke update` takes a backup first, and `open-revoke rollback` restores it.
