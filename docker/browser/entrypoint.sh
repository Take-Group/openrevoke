#!/bin/sh
# Entry point of the `browser` container. `docker compose restart` keeps the
# container's /tmp, so the X server lock of the previous run is still there and
# Xvnc would refuse to start on display :99. Remove it, then start supervisor.
set -eu

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 /tmp/supervisord.pid /tmp/supervisor.sock

# The API passes the panel's live view through and opens the VNC WebSocket with this
# origin (backend/app/browser/live_proxy.py). Other origins only for a published port.
export NOVNC_ALLOWED_ORIGINS="http://open-revoke-live-proxy ${NOVNC_ALLOWED_ORIGINS:-}"

# The password manager force-installed in this Chromium is the admin's choice from the panel
# (/welcome, /settings), applied by start-chromium.sh and policy-sync.sh from the API, not a
# static env var (skills/backend/browser.md, "Password manager").

exec "$@"
