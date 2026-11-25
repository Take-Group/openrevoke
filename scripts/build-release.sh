#!/bin/sh
# Build the images and the release bundle of one version, on this machine.
#
#   scripts/build-release.sh 0.1.0                  images for this machine's platform + dist/releases/
#   scripts/build-release.sh 0.1.0 --out /srv/rel   another release directory
#   scripts/build-release.sh 0.1.0 --platform linux/amd64   images for another platform (emulated)
#
# The output is laid out like GitHub Releases, so install.sh and `open-revoke update` read it
# with OPEN_REVOKE_RELEASES_URL=file://<out>:
#
#   <out>/download/v0.1.0/open-revoke-0.1.0.tar.gz   bundle (compose.yaml, config/, open-revoke, lib/, ...)
#   <out>/download/v0.1.0/install.sh
#   <out>/download/v0.1.0/SHA256SUMS
#   <out>/download/v0.1.0/VERSION
#   <out>/latest/download/VERSION                    newest final release (not for -rc builds)
#
# Images are tagged ghcr.io/take-group/open-revoke[-browser]:<version> and stay local; pushing,
# multi-arch builds and signing come with the GitHub workflow.
set -eu

cd "$(dirname "$0")/.."
VERSION=${1:-}
[ -n "$VERSION" ] || {
    echo "usage: scripts/build-release.sh <version> [--out DIR] [--platform P] [--skip-images]" >&2
    exit 1
}
shift
OUT=dist/releases
SKIP_IMAGES=0
PLATFORM=""
while [ $# -gt 0 ]; do
    case $1 in
        --out) OUT=$2; shift ;;
        --platform) PLATFORM=$2; shift ;;
        --skip-images) SKIP_IMAGES=1 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done
VERSION=${VERSION#v}
echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$' || {
    echo "not a SemVer version: $VERSION" >&2
    exit 1
}
IMAGE=${OPEN_REVOKE_IMAGE:-ghcr.io/take-group/open-revoke}
BROWSER_IMAGE=${OPEN_REVOKE_BROWSER_IMAGE:-ghcr.io/take-group/open-revoke-browser}

if [ "$SKIP_IMAGES" = 0 ]; then
    set -- # docker build options
    [ -n "$PLATFORM" ] && set -- --platform "$PLATFORM"
    echo "==> Building $IMAGE:$VERSION ${PLATFORM:-for this machine}"
    docker build "$@" --target app --build-arg "OPEN_REVOKE_VERSION=$VERSION" -t "$IMAGE:$VERSION" .
    echo "==> Building $BROWSER_IMAGE:$VERSION"
    docker build "$@" --target browser --label "org.opencontainers.image.version=$VERSION" -t "$BROWSER_IMAGE:$VERSION" .
fi

echo "==> Bundle"
release="$OUT/download/v$VERSION"
mkdir -p "$release"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/config/caddy" "$stage/config/temporal"
# The compose file of the repo, with the paths of the bundle and this version as the default.
sed -e "s#\./backend/temporal/#./config/temporal/#g" \
    -e "s#\./docker/caddy/#./config/caddy/#g" \
    -e "s#\${OPEN_REVOKE_VERSION:-dev}#\${OPEN_REVOKE_VERSION:-$VERSION}#g" \
    compose.yaml > "$stage/compose.yaml"
grep -q '\./backend/\|\./docker/' "$stage/compose.yaml" && {
    echo "compose.yaml mounts a path the bundle does not have; add it to scripts/build-release.sh" >&2
    exit 1
}
cp docker/caddy/Caddyfile "$stage/config/caddy/"
cp -R backend/temporal/scripts backend/temporal/dynamicconfig "$stage/config/temporal/"
cp deploy/open-revoke deploy/install.sh "$stage/"
cp -R deploy/lib "$stage/lib"
chmod +x "$stage/open-revoke" "$stage/install.sh"
sed "s/^OPEN_REVOKE_VERSION=.*/OPEN_REVOKE_VERSION=$VERSION/" .env.example > "$stage/.env.example"
cp CHANGELOG.md "$stage/"
echo "$VERSION" > "$stage/VERSION"
# macOS tar (bsdtar) adds Apple metadata that GNU tar on the server warns about.
if tar --version 2> /dev/null | grep -q bsdtar; then
    COPYFILE_DISABLE=1 tar --no-mac-metadata --no-xattrs -czf "$release/open-revoke-$VERSION.tar.gz" -C "$stage" .
else
    tar -czf "$release/open-revoke-$VERSION.tar.gz" -C "$stage" .
fi
cp deploy/install.sh "$release/install.sh"
echo "$VERSION" > "$release/VERSION"
(
    cd "$release"
    if command -v sha256sum > /dev/null 2>&1; then
        sha256sum "open-revoke-$VERSION.tar.gz" install.sh > SHA256SUMS
    else
        shasum -a 256 "open-revoke-$VERSION.tar.gz" install.sh > SHA256SUMS
    fi
)
case $VERSION in
    *-*) echo "Pre-release: latest/ is not changed." ;;
    *)
        mkdir -p "$OUT/latest/download"
        echo "$VERSION" > "$OUT/latest/download/VERSION"
        ;;
esac
abs_out=$(cd "$OUT" && pwd)
echo ""
echo "Release $VERSION in $abs_out"
echo "Install from it: OPEN_REVOKE_RELEASES_URL=file://$abs_out sh $abs_out/download/v$VERSION/install.sh --version $VERSION"
