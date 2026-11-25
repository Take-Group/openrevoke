# Shared helpers of the host command `open-revoke` (sourced, POSIX sh).
# Expects INSTALL_DIR set by the caller.

DEFAULT_RELEASES_URL="https://github.com/Take-Group/openrevoke/releases"

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
warn() { printf 'Warning: %s\n' "$*" >&2; }
die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

# Value of KEY in .env (last assignment wins, like Compose), empty when unset.
env_get() {
    awk -F= -v key="$1" '$1 == key { sub(/^[^=]*=/, ""); value = $0 } END { print value }' "$INSTALL_DIR/.env"
}

# Set KEY=VALUE in a dotenv file: replaces `KEY=` or a commented `# KEY=` line, else appends.
env_set() {
    file=$3
    tmp="$file.tmp.$$"
    awk -v key="$1" -v value="$2" '
        !done && ($0 ~ "^" key "=" || $0 ~ "^# " key "=") { print key "=" value; done = 1; next }
        { print }
        END { if (!done) print key "=" value }
    ' "$file" > "$tmp"
    mv "$tmp" "$file"
}

compose() {
    (cd "$INSTALL_DIR" && docker compose "$@")
}

releases_url() {
    url=$(env_get OPEN_REVOKE_RELEASES_URL)
    printf '%s' "${url:-$DEFAULT_RELEASES_URL}"
}

# curl for http(s) and file:// release sources (a local directory before the GitHub repo exists).
fetch() {
    curl -fsSL --retry 2 "$1" -o "$2"
}

latest_version() {
    tmp=$(mktemp)
    if fetch "$(releases_url)/latest/download/VERSION" "$tmp" 2>/dev/null; then
        tr -d ' \n\r' < "$tmp"
    fi
    rm -f "$tmp"
}

sha256_of() {
    if command -v sha256sum > /dev/null 2>&1; then
        sha256sum "$1" | awk '{ print $1 }'
    else
        shasum -a 256 "$1" | awk '{ print $1 }'
    fi
}

# Download the bundle of VERSION into DEST and check it against SHA256SUMS of the release.
download_bundle() {
    version=$1
    dest=$2
    base="$(releases_url)/download/v$version"
    fetch "$base/open-revoke-$version.tar.gz" "$dest/bundle.tar.gz" || die "cannot download release $version from $base"
    fetch "$base/SHA256SUMS" "$dest/SHA256SUMS" || die "cannot download SHA256SUMS of release $version"
    expected=$(awk -v name="open-revoke-$version.tar.gz" '$2 == name || $2 == "*" name { print $1 }' "$dest/SHA256SUMS")
    [ -n "$expected" ] || die "SHA256SUMS of release $version does not list the bundle"
    [ "$(sha256_of "$dest/bundle.tar.gz")" = "$expected" ] || die "checksum of the release $version bundle does not match"
}

# 0 when $1 is a newer SemVer than $2 (pre-releases sort before their final release).
version_gt() {
    [ "$1" != "$2" ] || return 1
    newest=$(printf '%s\n%s\n' "$1" "$2" | awk '
        { v = $0; sub(/^v/, "", v); split(v, part, "-"); split(part[1], n, ".")
          printf "%09d%09d%09d%s %s\n", n[1], n[2], n[3], (part[2] == "" ? "~" : part[2]), $0 }
    ' | sort | tail -n 1 | awk '{ print $2 }')
    [ "$newest" = "$1" ]
}

container_of() {
    compose ps -q "$1" 2> /dev/null
}

# Wait until the app container reports healthy, at most $1 seconds.
wait_healthy() {
    limit=${1:-300}
    waited=0
    while [ "$waited" -lt "$limit" ]; do
        id=$(container_of app)
        if [ -n "$id" ]; then
            state=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2> /dev/null || true)
            [ "$state" = "healthy" ] && return 0
            [ "$state" = "exited" ] && return 1
        fi
        sleep 5
        waited=$((waited + 5))
        [ $((waited % 30)) -eq 0 ] && say "   still starting ($waited s)..."
    done
    return 1
}

# Run python -m <module> in the running app container.
app_python() {
    compose exec -T app /app/backend/.venv/bin/python -m "$@"
}

# Read one value from a flat JSON object printed by app.ops (no jq on the host).
json_value() {
    sed -n "s/.*\"$1\": *\"\{0,1\}\([^\",}]*\)\"\{0,1\}.*/\1/p" | head -n 1
}

confirm() {
    [ "${ASSUME_YES:-0}" = 1 ] && return 0
    printf '%s [y/N] ' "$1"
    read -r answer < /dev/tty || return 1
    case $answer in y | Y | yes | YES) return 0 ;; *) return 1 ;; esac
}
