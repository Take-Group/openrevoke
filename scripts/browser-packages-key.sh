#!/bin/sh
# Print a key of the Debian packages the browser image would install now: a SHA-256 over the
# package versions that `apt-get install --simulate` picks for docker/browser/packages.txt and
# all their dependencies, in the base image of the Dockerfile's browser stage, on this machine's
# platform. The release workflows pass it as --build-arg BROWSER_PACKAGES_HASH, so the browser
# image's package layer comes from the build cache until Debian ships a newer version of any of
# those packages (a Chromium security release, a curl fix) and is rebuilt then.
#
#   scripts/browser-packages-key.sh            prints e.g. 3f1c...e9 (64 hex characters)
set -eu
cd "$(dirname "$0")/.."
base=$(awk '/^FROM .* AS browser$/ { print $2 }' Dockerfile)
[ -n "$base" ] || { echo "no 'FROM ... AS browser' line in Dockerfile" >&2; exit 1; }
# The package list goes in on stdin, the same file the Dockerfile reads with xargs. The output is
# captured first: a failed or interrupted docker run stops the script (set -e) instead of hashing
# a partial plan, which a pipeline would hide behind the exit status of its last command.
simulation=$(docker run --rm -i "$base" sh -c '
    apt-get update -qq > /dev/null && xargs apt-get install --simulate --no-install-recommends
' < docker/browser/packages.txt)
plan=$(printf '%s\n' "$simulation" | grep '^Inst ' | LC_ALL=C sort || true)
[ -n "$plan" ] || { echo "apt-get --simulate listed no packages" >&2; exit 1; }
printf '%s\n%s\n' "$base" "$plan" | sha256sum | cut -d' ' -f1
