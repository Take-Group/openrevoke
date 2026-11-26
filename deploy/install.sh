#!/bin/sh
# Open Revoke installer. Read it before you run it: it only does what this header says.
#
#   curl -fsSL https://openrevoke.com/install.sh | sh
#   sh install.sh --yes --url https://revoke.example.com --proxy caddy
#
# 1. Checks Docker, Docker Compose, free ports and disk; changes nothing when a check fails.
# 2. Downloads the release bundle and checks its SHA-256 against the release's SHA256SUMS.
# 3. Writes .env: generated OPEN_REVOKE_SECRET_KEY, POSTGRES_PASSWORD and REDIS_PASSWORD, the panel address,
#    the time zone of this machine, the version. chmod 600.
# 4. Links the `open-revoke` command into PATH and starts the stack.
# 5. Prints the setup link: only it can create the first admin.
#
# It never calls another script from the network and never overwrites an installation.
# POSIX sh, no bash, no Python on the host.
set -eu

RELEASES_URL=${OPEN_REVOKE_RELEASES_URL:-https://github.com/Take-Group/openrevoke/releases}
VERSION=""
INSTALL_DIR=""
PUBLIC_URL=""
PROXY=""
PORT=18410
BIND=127.0.0.1
NAME=open-revoke
ZONE=""
ASSUME_YES=0
LINK=1
MIN_COMPOSE="2.20"

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
warn() { printf 'Warning: %s\n' "$*" >&2; }
die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat << 'EOF'
Usage: sh install.sh [options]

  --version X.Y.Z     release to install (default: the newest stable)
  --dir PATH          install directory (default: /opt/open-revoke as root, else ~/open-revoke)
  --url URL           address people open the panel at (default: http://localhost:<port>)
  --proxy MODE        caddy (HTTPS with Let's Encrypt from the bundled Caddy) or none
  --port N            port of the panel on this machine (default 18410)
  --bind IP           interface of that port (default 127.0.0.1)
  --tz ZONE           time zone (default: this machine's)
  --name NAME         Docker Compose project name (default open-revoke)
  --releases URL      where releases come from (default GitHub; a file:// directory works)
  --no-link           do not link the open-revoke command into PATH
  --yes               do not ask; take the defaults and the options above
EOF
}

while [ $# -gt 0 ]; do
    case $1 in
        --version) VERSION=${2#v}; shift ;;
        --dir) INSTALL_DIR=$2; shift ;;
        --url) PUBLIC_URL=$2; shift ;;
        --proxy) PROXY=$2; shift ;;
        --port) PORT=$2; shift ;;
        --bind) BIND=$2; shift ;;
        --tz) ZONE=$2; shift ;;
        --name) NAME=$2; shift ;;
        --releases) RELEASES_URL=$2; shift ;;
        --no-link) LINK=0 ;;
        --yes) ASSUME_YES=1 ;;
        -h | --help) usage; exit 0 ;;
        *) die "unknown option: $1 (see --help)" ;;
    esac
    shift
done

# Questions come from the terminal even when the script itself arrives on stdin (curl | sh).
ask() {
    prompt=$1
    default=$2
    if [ "$ASSUME_YES" = 1 ] || ! [ -r /dev/tty ]; then
        printf '%s' "$default"
        return
    fi
    printf '%s [%s]: ' "$prompt" "$default" > /dev/tty
    read -r answer < /dev/tty || answer=""
    printf '%s' "${answer:-$default}"
}

version_at_least() {
    [ "$(printf '%s\n%s\n' "$2" "$1" | sort -t. -k1,1n -k2,2n | head -n 1)" = "$2" ]
}

port_busy() {
    if command -v nc > /dev/null 2>&1; then nc -z 127.0.0.1 "$1" > /dev/null 2>&1; else return 1; fi
}

sha256_of() {
    if command -v sha256sum > /dev/null 2>&1; then sha256sum "$1" | awk '{ print $1 }'; else shasum -a 256 "$1" | awk '{ print $1 }'; fi
}

detect_timezone() {
    zone=""
    if command -v timedatectl > /dev/null 2>&1; then zone=$(timedatectl show -p Timezone --value 2> /dev/null || true); fi
    if [ -z "$zone" ] && [ -f /etc/timezone ]; then zone=$(head -n 1 /etc/timezone); fi
    if [ -z "$zone" ] && [ -L /etc/localtime ]; then zone=$(readlink /etc/localtime | sed -n 's#.*zoneinfo/##p'); fi
    printf '%s' "${zone:-UTC}"
}

env_set() {
    tmp="$3.tmp.$$"
    # umask 077: the copy holds the secrets and replaces .env, so it is never readable by others.
    (umask 077 && awk -v key="$1" -v value="$2" '
        !done && ($0 ~ "^" key "=" || $0 ~ "^# " key "=") { print key "=" value; done = 1; next }
        { print }
        END { if (!done) print key "=" value }
    ' "$3" > "$tmp")
    mv "$tmp" "$3"
}

step "Checking this machine"
case $(uname -s) in Linux | Darwin) ;; *) die "Open Revoke installs on Linux or macOS" ;; esac
case $(uname -m) in x86_64 | amd64 | aarch64 | arm64) ;; *) die "images exist for amd64 and arm64 only, not $(uname -m)" ;; esac
for tool in docker curl tar openssl awk; do
    command -v "$tool" > /dev/null 2>&1 || die "$tool is missing; install it first (Docker: https://docs.docker.com/engine/install/)"
done
docker info > /dev/null 2>&1 || die "Docker does not answer: start it, or add this user to the docker group"
compose_version=$(docker compose version --short 2> /dev/null | sed 's/^v//') || true
[ -n "$compose_version" ] || die "the Docker Compose plugin (docker compose) is missing"
version_at_least "$compose_version" "$MIN_COMPOSE" || die "Docker Compose $compose_version is too old; $MIN_COMPOSE or newer is needed"
say "Docker $(docker version --format '{{.Server.Version}}' 2> /dev/null), Compose $compose_version"

if [ -z "$INSTALL_DIR" ]; then
    if [ "$(id -u)" = 0 ]; then INSTALL_DIR=/opt/open-revoke; else INSTALL_DIR="$HOME/open-revoke"; fi
fi
[ -f "$INSTALL_DIR/.env" ] && die "Open Revoke is already installed in $INSTALL_DIR. Start it with: open-revoke start; update it with: open-revoke update"

PUBLIC_URL=$(ask "Address people will open the panel at" "${PUBLIC_URL:-http://localhost:$PORT}")
PUBLIC_URL=${PUBLIC_URL%/}
if [ -z "$PROXY" ]; then
    case $PUBLIC_URL in
        https://localhost* | http://*) PROXY=none ;;
        https://*)
            answer=$(ask "Get the HTTPS certificate from Let's Encrypt with the bundled Caddy? (no: your own proxy, Cloudflare or Tailscale)" "yes")
            case $answer in y* | Y*) PROXY=caddy ;; *) PROXY=none ;; esac
            ;;
    esac
fi
[ "$PROXY" = caddy ] || [ "$PROXY" = none ] || die "--proxy must be caddy or none"
ZONE=${ZONE:-$(detect_timezone)}

port_busy "$PORT" && die "port $PORT is in use; pick another with --port"
if [ "$PROXY" = caddy ]; then
    for p in 80 443; do port_busy "$p" && die "port $p is in use, and Caddy needs it for Let's Encrypt"; done
fi
mkdir -p "$INSTALL_DIR"
free_kb=$(df -Pk "$INSTALL_DIR" | awk 'NR == 2 { print $4 }')
[ "${free_kb:-0}" -ge 10485760 ] || warn "less than 10 GB free in $INSTALL_DIR; images and the database need room"
if [ -r /proc/meminfo ]; then
    mem_kb=$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo)
    [ "${mem_kb:-0}" -ge 3500000 ] || warn "less than 4 GB of RAM: Temporal, PostgreSQL and Chromium may not fit"
fi

step "Downloading Open Revoke"
if [ -z "$VERSION" ]; then
    VERSION=$(curl -fsSL "$RELEASES_URL/latest/download/VERSION" | tr -d ' \n\r') || die "cannot read the newest release from $RELEASES_URL"
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
base="$RELEASES_URL/download/v$VERSION"
curl -fsSL "$base/open-revoke-$VERSION.tar.gz" -o "$work/bundle.tar.gz" || die "cannot download release $VERSION from $base"
curl -fsSL "$base/SHA256SUMS" -o "$work/SHA256SUMS" || die "cannot download SHA256SUMS of release $VERSION"
expected=$(awk -v name="open-revoke-$VERSION.tar.gz" '$2 == name || $2 == "*" name { print $1 }' "$work/SHA256SUMS")
[ -n "$expected" ] && [ "$(sha256_of "$work/bundle.tar.gz")" = "$expected" ] || die "checksum of the bundle does not match SHA256SUMS"
if command -v cosign > /dev/null 2>&1; then
    say "cosign found: verify the images later with the command in the release notes."
fi
say "Open Revoke $VERSION, checksum ok"
tar -xzf "$work/bundle.tar.gz" -C "$INSTALL_DIR"

step "Writing $INSTALL_DIR/.env"
env_file="$INSTALL_DIR/.env"
(umask 077 && cp "$INSTALL_DIR/.env.example" "$env_file")
env_set OPEN_REVOKE_VERSION "$VERSION" "$env_file"
env_set OPEN_REVOKE_SECRET_KEY "$(openssl rand -base64 32 | tr '+/' '-_')" "$env_file"
env_set POSTGRES_PASSWORD "$(openssl rand -hex 24)" "$env_file"
env_set REDIS_PASSWORD "$(openssl rand -hex 24)" "$env_file"
env_set PUBLIC_URL "$PUBLIC_URL" "$env_file"
env_set TZ "$ZONE" "$env_file"
env_set COMPOSE_PROJECT_NAME "$NAME" "$env_file"
env_set OPEN_REVOKE_PORT "$PORT" "$env_file"
env_set OPEN_REVOKE_BIND "$BIND" "$env_file"
[ "$PROXY" = caddy ] && env_set COMPOSE_PROFILES https "$env_file"
case $RELEASES_URL in https://github.com/Take-Group/openrevoke/releases) ;; *) env_set OPEN_REVOKE_RELEASES_URL "$RELEASES_URL" "$env_file" ;; esac
chmod 600 "$env_file"
chmod +x "$INSTALL_DIR/open-revoke"
say "Secrets generated; time zone $ZONE; panel $PUBLIC_URL"

if [ "$LINK" = 1 ]; then
    if [ -w /usr/local/bin ]; then bin=/usr/local/bin; else bin="$HOME/.local/bin"; mkdir -p "$bin"; fi
    ln -sf "$INSTALL_DIR/open-revoke" "$bin/open-revoke"
    case ":$PATH:" in *":$bin:"*) ;; *) warn "$bin is not in PATH; run $bin/open-revoke or add it" ;; esac
fi

step "Starting (the first start downloads the images and takes a few minutes)"
cd "$INSTALL_DIR"
# Docker Hub sometimes resets connections while several images download at once: try again
# before giving up. Everything up to here is written, so `open-revoke start` finishes the job.
tries=1
until docker compose up -d --pull missing; do
    [ "$tries" -ge 3 ] && die "the stack did not start (see above). When the cause is fixed (network, disk), run: open-revoke start"
    warn "start failed (try $tries of 3); trying again in 10 s"
    tries=$((tries + 1))
    sleep 10
done
waited=0
while :; do
    id=$(docker compose ps -q app 2> /dev/null || true)
    state=$( [ -n "$id" ] && docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$id" 2> /dev/null || echo starting)
    [ "$state" = healthy ] && break
    [ "$waited" -ge 600 ] && die "the app did not start in 10 minutes; see: open-revoke logs app"
    sleep 5
    waited=$((waited + 5))
    [ $((waited % 30)) -eq 0 ] && say "   still starting ($waited s)..."
done
link=$(docker compose exec -T app /app/backend/.venv/bin/python -m app.cli setup-link | tail -n 1)

step "Open Revoke $VERSION is running"
say ""
say "  1. Create the first admin with this link (only this link can do it):"
say "     $link"
say "  2. Keep $env_file in a password manager: without OPEN_REVOKE_SECRET_KEY the stored"
say "     connector secrets cannot be read."
say "  3. Back up regularly: open-revoke backup. Update: open-revoke update. Help: open-revoke help."
[ "$PROXY" = none ] && case $PUBLIC_URL in https://*) say "  4. Point your HTTPS proxy at http://$BIND:$PORT (docs/self-hosting.md)." ;; esac
say ""
