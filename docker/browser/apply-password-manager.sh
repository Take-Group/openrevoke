#!/bin/sh
# Fetches the organization's chosen password manager from the panel API and writes the
# Chromium force-install policy, so the single admin signs in to SaaS panels by autofill
# (skills/backend/browser.md, "Password manager"). Prints "changed" when the policy file
# changed, so policy-sync.sh knows to restart Chromium. Best-effort: on any error it leaves
# the current policy in place, so a brief panel outage never drops the extension.
set -eu

POLICY_FILE=/etc/chromium/policies/managed/password-manager.json
UPDATE_URL=https://clients2.google.com/service/update2/crx
API="${BROWSER_POLICY_API_URL:-}"

[ -n "$API" ] || exit 0

# Non-sensitive config: {"manager": "...", "extension_id": "<32 chars>"} or extension_id null.
response=$(curl -fsS --max-time 5 "$API/api/browser/policy" 2>/dev/null) || exit 0
extension_id=$(printf '%s' "$response" | sed -n 's/.*"extension_id"[[:space:]]*:[[:space:]]*"\([a-p]\{32\}\)".*/\1/p')

if [ -n "$extension_id" ]; then
    # toolbar_pin: the icon sits in the toolbar from the first launch instead of hiding in the
    # Extensions menu, so the admin sees the manager's lock and signs in to it at once.
    desired=$(printf '{\n  "ExtensionInstallForcelist": ["%s;%s"],\n  "ExtensionSettings": {"%s": {"toolbar_pin": "force_pinned"}}\n}\n' \
        "$extension_id" "$UPDATE_URL" "$extension_id")
else
    desired=
fi

current=$(cat "$POLICY_FILE" 2>/dev/null || true)
[ "$desired" = "$current" ] && exit 0

if [ -n "$desired" ]; then
    printf '%s' "$desired" > "$POLICY_FILE"
else
    rm -f "$POLICY_FILE"
fi
echo changed
