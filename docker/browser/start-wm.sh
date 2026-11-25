#!/bin/sh
# Window manager: keeps the Chromium window maximized on the whole screen, also
# for windows and popups Chromium opens later (e.g. a Google sign-in popup).
set -eu

i=0
until [ -e /tmp/.X11-unix/X99 ] || [ "$i" -ge 100 ]; do
    i=$((i + 1))
    sleep 0.1
done

exec /usr/bin/matchbox-window-manager -use_titlebar no -use_cursor yes
