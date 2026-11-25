#!/bin/sh
# Starts Chromium headful on the Xvnc display with the persistent profile.
# Supervisor restarts this script whenever Chromium exits (crash, or the user
# closed the last window), so the browser is always there for the backend.
set -eu

PROFILE_DIR=/profile

# Wait for the X display (Xvnc starts in parallel under supervisor).
i=0
until [ -e /tmp/.X11-unix/X99 ] || [ "$i" -ge 100 ]; do
    i=$((i + 1))
    sleep 0.1
done

# A container restart leaves lock files of the previous Chromium behind. With
# them Chromium thinks the profile is used by another computer and refuses it.
rm -f "$PROFILE_DIR/SingletonLock" "$PROFILE_DIR/SingletonSocket" "$PROFILE_DIR/SingletonCookie"

# Mark the last session as clean so Chromium does not show the "restore pages"
# bubble after a crash or a hard container stop.
PREFS="$PROFILE_DIR/Default/Preferences"
if [ -f "$PREFS" ]; then
    sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/; s/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS" || true
fi

# Install the admin's password manager before Chromium starts, so its extension is present at
# first launch (policy-sync.sh handles later changes). Best-effort: never blocks the browser.
/usr/local/bin/apply-password-manager.sh >/dev/null 2>&1 || true

# --no-sandbox: Docker's default seccomp profile blocks the user namespaces the
# Chromium sandbox needs. The container is the isolation boundary instead.
# --remote-debugging-port binds to 127.0.0.1 only (Chrome ignores
# --remote-debugging-address); socat exposes it on :9223 to the compose network.
# --force-device-scale-factor=2: two display pixels per CSS pixel, so the live view is sharp
# on a Retina screen. live.html (resize=1) sizes the display to the panel's view times 2;
# keep its SCALE equal to this factor.
exec /usr/bin/chromium \
    --user-data-dir="$PROFILE_DIR" \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    --no-first-run \
    --no-default-browser-check \
    --no-sandbox \
    --test-type \
    --disable-gpu \
    --disable-dev-shm-usage \
    --password-store=basic \
    --disable-features=Translate,MediaRouter,DialMediaRouteProvider \
    --disable-session-crashed-bubble \
    --start-maximized \
    --force-device-scale-factor=2 \
    --lang=en-US \
    --log-level=3 \
    about:blank
