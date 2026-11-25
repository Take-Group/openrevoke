# Skill: Shared browser, CDP session and traffic capture

## What it does

The compose stacks (the local dev stack `compose.dev.yaml` and self-hosting
`compose.yaml`) run one Chromium (service `browser`) with a persistent profile. The admin
signs in to SaaS panels in it through the noVNC live view on the `/browser` page
of the panel (in the dev stack also directly at http://localhost:18412/vnc.html). Browser connectors
(`AuthKind.BROWSER_SESSION`) then send the panel's requests as `fetch()`
in a tab of that app, with the admin's cookies.

**Warning:** the `browser-profile` volume holds the admins' signed-in sessions
(cookies of the Slack, Claude, ChatGPT and other panels) **and the admin's signed-in
password manager extension** (see "Password manager" below). Whoever has this volume
or the live view has not only these sessions but also access to the admin's whole vault. This
raises the stakes: the noVNC live view and CDP never leave `127.0.0.1` (dev
stack); `compose.yaml` publishes no
port. Do not copy the volume. Removing the stack's volumes
(`docker compose down -v`) deletes it (then you must sign in again).
`python -m app.db reset` does not touch it.

## Files

| File | What it does |
|---|---|
| `Dockerfile`, target `browser` | Debian trixie: `chromium`, `tigervnc-standalone-server` (Xvnc), `matchbox-window-manager`, `novnc`, `websockify`, `supervisor`, `socat`, fonts; user `browser` (uid 1000) |
| `docker/browser/supervisord.conf` | processes `xvnc`, `wm`, `chromium`, `cdp-proxy` (socat), `novnc` |
| `docker/browser/entrypoint.sh` | removes the X lock after a container restart, sets `NOVNC_ALLOWED_ORIGINS` |
| `docker/browser/apply-password-manager.sh` | queries `GET /api/browser/policy` and writes `password-manager.json` (`ExtensionInstallForcelist`, icon pinned through `ExtensionSettings.toolbar_pin`); prints "changed" when it changed |
| `docker/browser/policy-sync.sh` | supervisor program: calls `apply-password-manager.sh` every 15 s, on a change runs `supervisorctl restart chromium` |
| `docker/browser/start-chromium.sh` | removes `Singleton*` from the profile, starts Chromium with flags |
| `docker/browser/start-wm.sh` | matchbox: the Chromium window is always maximized |
| `docker/browser/chromium-policies.json` | fixed Chromium policy (`/etc/chromium/policies/managed/open-revoke.json`): Google search instead of Debian's DuckDuckGo. The password manager scripts (above) write the second file, `password-manager.json` |
| `docker/browser/live.html` | live view in the panel (`BROWSER_LIVE_VIEW_URL`, default `/api/browser/live/live.html`; the WebSocket address is relative, so it works through the API and on the published port): the screen only, without the noVNC menu, reconnects, Cmd+V/Ctrl+V pastes the computer's clipboard (passwords from the password manager) through the browser's `paste` event, without clipboard permission; a copy made inside is not overwritten by the old Mac clipboard, on a Mac Cmd+key is sent as Ctrl+key; the full noVNC client is still at `/vnc.html` |
| `compose.yaml` and `compose.dev.yaml`, service `browser` | volume `browser-profile:/profile`, `shm_size: 1gb`, CDP healthcheck; `compose.yaml` without ports; dev stack: noVNC `127.0.0.1:18412:6080`, CDP `127.0.0.1:18415`, network alias `open-revoke-browser` |
| `backend/app/browser/live_proxy.py`, `backend/app/api/browser_live.py` | live view through the API: `GET /api/browser/live/{path}` (only `live.html`, `core/*.js`, `vendor/*.js`) and WebSocket `/api/browser/live/websockify` to `browser:6080`; only an admin with a panel session, WebSocket only from the same origin (`Origin` = `X-Forwarded-Host` or `Host`); `GET /api/browser` gives a member `live_view_url = null` |
| `compose.yaml`, service `app`; `compose.dev.yaml`, services `api` and `worker` | `BROWSER_CDP_HOST` (`browser`, in the dev stack `open-revoke-browser`), `BROWSER_CDP_PORT=9223`, `BROWSER_LIVE_VIEW_URL`, `captures` mounted at `/app/captures` |
| `backend/app/browser/provider.py` | `BrowserProvider` (protocol), `LocalChromiumProvider`, `get_browser_provider()` |
| `backend/app/browser/session.py` | `CdpBrowserSession`: tabs per origin, `fetch`, `local_storage`, `cookies`, `evaluate`, `open_tab` |
| `backend/app/browser/capture.py` | `HeaderCapture`: last auth headers per host, TTL 1 h, in memory only |
| `backend/app/connectors/browser_api.py` | `BrowserSession` (protocol for connectors), `BrowserResponse`, `BrowserUnavailableError`, `raise_for_browser_error`, `browser_json` |
| `backend/app/services/connector_runtime.py` | `open_context` gives `ctx.browser` to `BROWSER_SESSION` connectors |
| `backend/app/services/browser.py`, `backend/app/api/browser.py` | `GET /api/browser`, `POST /api/browser/open` |
| `backend/app/devtools/capture.py`, `masking.py` | records fetch/XHR to JSONL with token masking |
| `backend/app/connectors/browser_fake/`, `backend/app/api/dev_panel.py` | test connector and a fake panel inside the app (only with the fake flag) |

## The `browser` container

Processes under supervisor (user `browser`, not root):

1. `Xvnc :99` (TigerVNC, since 2026-11-23 instead of Xvfb + x11vnc): X server
   and VNC in one, VNC only on `127.0.0.1:5900` (`-localhost`), no password.
   The screen starts at 2560x1440, Chromium at scale 2 (`--force-device-scale-factor=2`):
   two screen pixels per CSS pixel, so the live view is sharp on a Retina screen.
   The panel's `/browser` page loads `live.html?resize=1`: the live view asks Xvnc
   (SetDesktopSize) for a screen the size of its window times 2, so pages lay out
   at the size of the live view and fill it without bars (1280x720
   was too large, full HD too small). The layout is kept between 800x500 and 1920x1200
   CSS (`MIN`, `MAX` in `live.html`); outside this range the image is scaled.
   `SCALE` in `live.html` must equal the Chromium scale. The size is set by the last
   live view that changed; the live view on `/discovery` (without `resize`) only scales.
   The `_requestRemoteResize` extension is a private noVNC 1.6 method: check it after
   a noVNC update. The cursor comes from Xvnc as an image in screen pixels (scale 2),
   so `live.html` shows it through `image-set`, shrunk at most 1.4 times (`CURSOR_SHRINK`;
   at 2 it was too small next to the Mac cursor; `scaleCursor`, also private
   noVNC fields). Xvnc knows what changed on the screen; x11vnc polled
   the whole screen, so it was slower.
2. `matchbox-window-manager`: keeps the Chromium window and its pop-up windows
   (e.g. Google sign-in) maximized to the full screen.
3. Headful Chromium: `--user-data-dir=/profile`,
   `--remote-debugging-port=9222`, `--remote-allow-origins=*`,
   `--no-sandbox`, `about:blank`. Supervisor starts it again after a crash
   and after the user closes the last window.
4. `socat` 0.0.0.0:9223 → 127.0.0.1:9222 (CDP for the compose network).
5. `websockify` with noVNC on 0.0.0.0:6080 (compose network only; the dev stack
   publishes it on `127.0.0.1:18412`), with the `ExpectOrigin` plugin: the VNC
   WebSocket opens only for an origin from `NOVNC_ALLOWED_ORIGINS`. `entrypoint.sh`
   always adds `http://open-revoke-live-proxy`, the origin the API proxy
   connects with (`live_proxy.PROXY_ORIGIN`). The dev stack adds
   `http://localhost:18412` for the published port. Without this plugin any
   page in the admin's browser could connect to the published port
   and control the Chromium with the admins' sessions (WebSocket is not subject to the same-origin
   policy).

Healthcheck: `curl http://127.0.0.1:9222/json/version` in the container.
CDP is not published on the host.

## Pitfalls

- **CDP only on 127.0.0.1.** New Chrome ignores
  `--remote-debugging-address`. Hence socat on port 9223.
- **Host header.** The DevTools HTTP server rejects a request when `Host` is
  a name other than `localhost` (e.g. `browser`). `LocalChromiumProvider`
  resolves `browser` with `socket.gethostbyname` and connects by IP.
  The WebSocket address from `/json/version` then also has the IP.
- **Never `browser.close()`** on a `connect_over_cdp` connection: it can close
  the admin's Chromium. `disconnect()` stops the Playwright driver, which
  only drops the WebSocket.
- **Profile locks.** A container restart leaves `SingletonLock`,
  `SingletonSocket`, `SingletonCookie`. If they are not removed, Chromium treats
  the profile as used by another computer. `start-chromium.sh` removes them.
- **X lock.** A container restart (`dc restart browser`) keeps `/tmp`, so
  `/tmp/.X99-lock` would block Xvnc. `entrypoint.sh` removes it.
- **Sandbox.** Docker's default seccomp profile blocks user
  namespaces, which the Chromium sandbox needs, hence `--no-sandbox`.
  The container is the isolation boundary. `--test-type` hides the warning bar
  about this flag.
- **Google session after a restart.** On 2026-11-23 a container restart signed
  out the Google account ("Signed out" in the account chooser), although the cookies stayed.
  The cause was not checked. After a restart, sign in again.
- **Cookies on disk.** Chromium writes cookies to the profile with
  a delay. `dc restart browser` sends SIGTERM and Chromium
  writes them on shutdown. `docker kill` right after a sign-in can lose them.
  Session cookies (without `Max-Age`) do not survive a restart at all.
- **Shared memory.** `shm_size: 1gb` in compose plus
  `--disable-dev-shm-usage`; Docker's default 64 MB breaks tabs.
- **HSTS for the name `app`.** `.app` is a TLD on the HSTS preload list, so
  Chromium changes `http://app:8000` to `https://` (error
  `ERR_SSL_PROTOCOL_ERROR`). The browser sees the app under the network alias
  `open-revoke-app` (`compose.yaml`, in the dev stack an alias of the `api` service). Internal
  addresses in `.dev`, `.app`, `.page` behave the same way.
- **Screen size.** Automation through CDP sees the page at the size left by the last
  `/browser` live view (CSS, from 800x500 to 1920x1200; after a container restart 1280x720), minus
  the Chromium bar. CDP screenshots have scale 2. To change the size: `-geometry` in `docker/browser/supervisord.conf`
  and rebuild the image.
- **Image.** `fonts-noto` is large; the `browser` image is about 1.6 GB (arm64,
  2026-11-22).

## Password manager (the admin connects apps)

The Open Revoke model: one admin is responsible for onboarding and offboarding, and only
that admin has access to the shared browser. So that this admin does not
type credentials into each panel by hand, Chromium has a force-installed extension
of the admin's password manager, which autofills sign-ins.

- **The admin picks the manager in the panel:** the question in `/welcome` and the select in
  `/settings` save `organization.password_manager` (`1password`,
  `bitwarden`, `other`, `none`; null = not chosen yet). Before the choice
  Chromium has no extension.
- **The container enforces the choice itself, the backend does not touch it** (the rule "the backend does not
  close the browser" stays). The unauthenticated endpoint `GET /api/browser/policy`
  returns `{manager, extension_id}` from `organization` (ID map in
  `services/browser.py`: 1Password `aeblfdkhhhdcdjpifhhbdiojplfjncoa`, Bitwarden
  `nngceckbapebfimnlniiiahkandclblb`). `start-chromium.sh` queries it and writes
  `ExtensionInstallForcelist` and `ExtensionSettings` (`toolbar_pin: force_pinned`,
  icon pinned on the toolbar instead of in the Extensions menu) to
  `/etc/chromium/policies/managed/password-manager.json`
  before Chromium starts (`apply-password-manager.sh`); `policy-sync.sh` queries
  every 15 s and on a change rewrites the policy and runs `supervisorctl restart chromium`,
  so the old extension disappears and the new one installs. `BROWSER_POLICY_API_URL`
  (both compose files) points to the API (`http://open-revoke-app:8000` in dev,
  `http://app:8000` in self-hosting).
- **The extension works on its own**, without the manager's desktop app. The admin
  signs in to it once in the noVNC live view (account + Secret Key + password; the
  first time the manager may ask to authorize a new device).
  The sign-in state lives in the profile, that is, in the `browser-profile` volume.
- **Connecting an app:** the admin opens the SaaS sign-in page in the live view,
  the extension autofills the credentials, the admin completes 2FA (phone or key: the admin is
  present for it). The session stays in the profile; offboarding then runs on it, the same
  as for sessions signed in by hand.
- **Limits, do not promise more:** when a SaaS session expires, signing in
  again still needs the admin present for 2FA (the extension cuts it to a few
  clicks). The manager locks itself after inactivity: this is a security
  feature, not a bug. Autofill does not cover passkeys or push
  sign-in without the admin.
- **Debian Chromium and force-install:** the extension comes from Google's CRX server
  (`clients2.google.com`), not from the Web Store UI. To check that it installed:
  `chrome://policy` (should show `ExtensionInstallForcelist`) and
  `chrome://extensions` in the noVNC live view.

## Session in the backend

- One CDP connection per process (API, worker, capture tool), opened
  lazily under an `asyncio.Lock`, renewed when dropped (Chromium restart).
  The worker connects at startup, so that `HeaderCapture` sees panel traffic
  earlier.
- `HeaderCapture` is per process. Headers stored by the API are not
  visible in the worker. The Slack, Claude and ChatGPT connectors do not need it
  (token from `localStorage`, cookies, `/api/auth/session`).
- When the page reloads during a `fetch`, the request is retried only
  for `GET`, `HEAD`, `OPTIONS` or with `idempotent=True` (Slack: read
  methods sent as POST). A write is not sent a second time: it may already
  have reached the app, so the connector gets `ConnectorError`.
- `fetch(url, page_url=...)` runs in a tab on the origin of `page_url` (default:
  the origin of `url`). No tab: it opens one (first in an empty `about:blank`).
  When the page redirects the tab to another origin (sign-in), the tab is
  closed and the connector gets `NeedsLogin`.
- Browser unavailable: `BrowserUnavailableError` (a subclass of `ConnectorError`).
  The sync ends `failed` and the connection `error`, not `needs_login`.
- Header, token and cookie values do not go into the logs (the
  `browser_fetch` log has the method, host, path and status).

## Browser connector

1. `integration = Integration.BROWSER`, `auth_kind = AuthKind.BROWSER_SESSION`,
   `login_url`, `admin_url`. When the sign-in page depends on the config (Slack:
   subdomain), override `login_page(config)`; extra tab origins go in
   `browser_origins(config)`.
2. Endpoints and payloads as constants at the top of `connector.py`.
3. Requests only through `ctx.browser.fetch(...)`, then
   `raise_for_browser_error(response, NAME, auth_statuses=...)` and
   `browser_json(response, NAME)`. An HTML response instead of JSON is usually
   a sign-in page or an anti-bot page; the message says so directly.
4. Detect sign-out explicitly (no token, 401, `invalid_auth`) and raise
   `NeedsLogin`. Missing admin rights is `ConnectorError`, not `NeedsLogin`.
5. Check by hand: sign in to the app's panel through noVNC, "Sync now"
   in the Open Revoke panel, accounts in the panel or in `psql`, errors
   in `dc logs --tail 100 worker`. A model of the whole path without a real account:
   `browser_fake` (below).

## Traffic capture (`app.devtools.capture`)

Local dev stack (from inside the container, `dc exec api sh`, because Ctrl+C ends
the capture and `dc exec` gives no terminal; with `--seconds`
`dc exec` is enough):

```bash
python -m app.devtools.capture --host app.slack.com --out /app/captures/slack.jsonl
dc exec api python -m app.devtools.capture --host chatgpt.com --out /app/captures/chatgpt.jsonl --seconds 300
```

Self-hosting: `docker compose exec app python -m app.devtools.capture … --out captures/slack.jsonl`.

- It connects to the browser with a separate CDP connection and writes every
  fetch/XHR response to the host (`--subdomains` also subdomains): method, URL,
  status, request and response headers (auth, cookie, csrf, token values
  masked; tokens in the URL query string too), request and response body (up to 200 KB, tokens `xox?-`, JWT,
  `Bearer`, fields `*token*`, `*secret*`, `*password*` masked).
- You click in the panel through noVNC, Ctrl+C ends the capture. The file is
  appended to, not overwritten.
- `open-revoke/captures/` on the host is mounted at `/app/captures`
  (both stacks). When the mount is missing, copy the file out:
  `docker compose cp app:/app/captures/slack.jsonl captures/`.
- On a Linux host the `captures/` folder must be writable for the
  `app` user from the container; on Docker Desktop (Mac) it works out of the box.
- A capture holds real people and parts of tokens that masking did not
  catch. `captures/` is in `.gitignore`. Delete the file after you write the connector.
  Do not move parts of a capture into the repository (docs, examples):
  only fictional data (`example.com`).

## Checking without real accounts: `browser_fake`

With `OPEN_REVOKE_ENABLE_FAKE_CONNECTOR=true` the app serves a fake
panel at `http://open-revoke-app:8000/api/dev/fake-panel` (the address seen from the
`browser` container; outside OpenAPI, 404 without the flag):

- `/login`: the "Log in" button sets the `fake_panel_session` cookie
  (persistent, 30 days), `/logout` removes it,
- `/users?page&per_page&count`: JSON with accounts, 401 without the cookie,
- `POST /users?count` (`{"email", "role"}`): invite, account `invited`;
  409 when the address already exists,
- `POST /users/{id}/remove?count`: removal; 404 for an unknown id.

The panel keeps invites and removals in Redis
(`connectors/browser_fake/panel_state.py`, keys `open-revoke:fake-panel:*`),
so a read after a write (action verification) sees them. The connector sends them with
`ctx.browser.fetch(..., method="POST")`, like real browser
connectors.

The `browser_fake` connector reads this panel through the real browser.
Scenario: an app with the `browser` integration, a `browser_fake` connection,
"Log in" on the `/browser` page (or `POST /api/browser/open` with `app_id`),
click "Log in" in noVNC, "Sync now". `/logout` in the browser and another sync
gives `needs_login`; `dc restart browser` does not lose the session.
Writes: turn on "Allow writes", "Add to app" or offboard a person, approve
the action; `ExecuteActionWorkflow` invites or removes the user in the panel
and confirms it with a read (`skills/backend/actions.md`).
