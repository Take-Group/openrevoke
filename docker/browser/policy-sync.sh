#!/bin/sh
# Keeps the force-installed password manager in step with the admin's choice in the panel.
# The admin picks it in /welcome or /settings; this polls the API and, when the choice
# changes, rewrites the policy and restarts Chromium so the old extension is removed and the
# new one installed. The backend never drives this: the browser container restarts its own
# Chromium (skills/backend/browser.md keeps the "backend never closes the browser" rule).
set -eu

while true; do
    if [ "$(/usr/local/bin/apply-password-manager.sh 2>/dev/null || true)" = changed ]; then
        supervisorctl -c /etc/supervisor/browser.conf restart chromium >/dev/null 2>&1 || true
    fi
    sleep 15
done
