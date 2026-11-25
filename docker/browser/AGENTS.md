# open-revoke/docker/browser/

Scripts of the `browser` container: Chromium on a virtual screen, shown through noVNC and driven by connectors over CDP. `supervisord.conf` starts the processes; the profile (signed-in admin sessions) lives in the volume mounted at `/profile`: never copy it.

- `entrypoint.sh`: removes stale X locks left by `docker compose restart`, sets `NOVNC_ALLOWED_ORIGINS` (includes `http://open-revoke-live-proxy`, the origin the API uses for the live view), then execs supervisor.
- `supervisord.conf`: programs `xvnc` (X :99 and VNC on 127.0.0.1:5900, starts at 2560x1440, viewers may resize it), `wm`, `chromium` (CDP on 127.0.0.1:9222), `policy-sync`, `cdp-proxy` (socat 0.0.0.0:9223 to 9222), `novnc` (websockify on 0.0.0.0:6080).
- `start-chromium.sh`: waits for the X display, runs `apply-password-manager.sh`, then starts Chromium headful with the `/profile` directory; supervisor restarts it whenever it exits.
- `apply-password-manager.sh`: polls `GET /api/browser/policy` (`BROWSER_POLICY_API_URL`) and writes the force-install and toolbar-pin policy `password-manager.json` for the org's chosen password manager; prints `changed` when the file changed.
- `policy-sync.sh`: `policy-sync` program; every 15 s runs `apply-password-manager.sh` and, on a change, `supervisorctl restart chromium` so the extension swaps (skills/backend/browser.md, "Password manager").
- `start-wm.sh`: matchbox window manager, keeps every Chromium window (popups too) maximized.
- `chromium-policies.json`: static managed policy (`open-revoke.json`): Google as the default search provider. The extension force-install policy is written at runtime to `password-manager.json` by `apply-password-manager.sh`.
- `live.html`: noVNC page without menu for the panel's live view (served via `/api/browser/live/live.html`); query `quality`, `compression`, `resize=1` (the display follows the page size times Chromium's scale 2); the remote cursor is shown as an image-set shrunk by at most `CURSOR_SHRINK` (1.4); Cmd+V pastes the local clipboard, Cmd+key is sent as Ctrl+key.
