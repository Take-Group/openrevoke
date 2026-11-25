#!/bin/sh
# Cut a release: checks, CHANGELOG.md section, commit "Release X.Y.Z" and the tag vX.Y.Z.
#
#   scripts/release.sh 0.2.0
#   scripts/release.sh 0.2.0 --skip-checks     only when the checks already ran on this commit
#
# No push: pushing is a human decision (repo AGENTS.md, "Git"). Then build the images and the
# bundle with scripts/build-release.sh 0.2.0 (locally until the GitHub workflow exists).
# The version lives only in the tag and the image (OPEN_REVOKE_VERSION); pyproject.toml and
# package.json are not published, so their version fields are not bumped.
# skills/backend/releases.md.
set -eu

cd "$(dirname "$0")/.."
VERSION=${1:-}
[ -n "$VERSION" ] || {
    echo "usage: scripts/release.sh <version> [--skip-checks]" >&2
    exit 1
}
VERSION=${VERSION#v}
SKIP_CHECKS=0
[ "${2:-}" = "--skip-checks" ] && SKIP_CHECKS=1
die() {
    echo "Error: $*" >&2
    exit 1
}

echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$' || die "not a SemVer version: $VERSION"
git rev-parse --verify --quiet "refs/tags/v$VERSION" > /dev/null && die "tag v$VERSION exists already"
[ -z "$(git status --porcelain -- .)" ] || die "open-revoke/ has uncommitted changes; commit them first"
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = main ] || [ "${RELEASE_ANY_BRANCH:-0}" = 1 ] || die "releases are cut on main (now: $branch); RELEASE_ANY_BRANCH=1 overrides"

last=$(git tag -l 'v*' --sort=-v:refname | head -n 1)
if [ -n "$last" ]; then
    newest=$(printf '%s\n%s\n' "${last#v}" "$VERSION" | sort -V | tail -n 1)
    [ "$newest" = "$VERSION" ] && [ "${last#v}" != "$VERSION" ] || die "$VERSION is not newer than the last release ${last#v}"
fi

unreleased=$(awk '/^## \[Unreleased\]/ { on = 1; next } /^## \[/ { on = 0 } on && NF' CHANGELOG.md)
[ -n "$unreleased" ] || die "CHANGELOG.md has nothing under ## [Unreleased]"

if [ "$SKIP_CHECKS" = 0 ]; then
    echo "==> Checks"
    (cd backend && uvx ruff check . && uvx ruff format --check .)
    (cd frontend && bun run lint && bun run typecheck)
fi

echo "==> CHANGELOG.md"
today=$(date +%Y-%m-%d)
tmp=$(mktemp)
awk -v version="$VERSION" -v today="$today" '
    /^## \[Unreleased\]/ && !done { print; print ""; print "## [" version "] - " today; done = 1; next }
    { print }
' CHANGELOG.md > "$tmp"
mv "$tmp" CHANGELOG.md

notes=$(awk -v version="$VERSION" '
    $0 ~ "^## \\[" version "\\]" { on = 1; next } /^## \[/ && on { exit } on
' CHANGELOG.md)
git add CHANGELOG.md
git commit -q -m "Release $VERSION"
git tag -a "v$VERSION" -m "Open Revoke $VERSION

$notes"
echo ""
echo "Tagged v$VERSION. Next: scripts/build-release.sh $VERSION"
