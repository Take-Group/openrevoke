# `open-revoke update` and `open-revoke rollback` (sourced after common.sh and backup.sh).
# Steps and reasons: skills/backend/releases.md.

# Files of a release bundle in the install directory; .env, backups/ and releases/ are never replaced.
BUNDLE_FILES="compose.yaml config open-revoke lib .env.example CHANGELOG.md VERSION install.sh"
STATE_FILE=".update-state"

save_current_bundle() {
    dest="$INSTALL_DIR/releases/$1"
    rm -rf "$dest"
    mkdir -p "$dest"
    for name in $BUNDLE_FILES; do
        [ -e "$INSTALL_DIR/$name" ] && cp -R "$INSTALL_DIR/$name" "$dest/$name"
    done
    return 0
}

# Copy the bundle files from $1 into the install directory. rm first: the running script keeps
# reading its old copy (a new inode), so replacing `open-revoke` mid-run is safe.
put_bundle() {
    for name in $BUNDLE_FILES; do
        rm -rf "${INSTALL_DIR:?}/$name"
        [ -e "$1/$name" ] && cp -R "$1/$name" "$INSTALL_DIR/$name"
    done
    chmod +x "$INSTALL_DIR/open-revoke"
}

# New keys in .env.example (uncommented KEY=value lines) go to .env with their default;
# existing values and secrets stay (like Supabase's update.sh).
merge_env_keys() {
    grep -E '^[A-Z_][A-Z0-9_]*=' "$1" | while IFS= read -r line; do
        key=${line%%=*}
        if ! grep -q "^$key=" "$INSTALL_DIR/.env"; then
            printf '%s\n' "$line" >> "$INSTALL_DIR/.env"
            say "   .env: added $key"
        fi
    done
}

# CHANGELOG.md sections newer than $3, up to and including $2.
changelog_between() {
    awk -v target="$2" -v current="$3" '
        /^## \[/ { v = $2; gsub(/[][]/, "", v); if (v == current) exit; show = (v != "Unreleased") }
        show
    ' "$1"
}

ensure_images() {
    images=$(OPEN_REVOKE_VERSION=$1 docker compose --project-directory "$INSTALL_DIR" -f "$2/compose.yaml" config --images)
    for image in $images; do
        docker image inspect "$image" > /dev/null 2>&1 || docker pull "$image" || die "cannot pull $image"
    done
}

wait_for_actions() {
    waited=0
    while :; do
        count=$(app_python app.ops in-flight 2> /dev/null | json_value actions_in_flight)
        [ -z "$count" ] || [ "$count" = 0 ] && return 0
        if [ "$waited" -ge 600 ]; then
            confirm "$count write action(s) still running. A code change can break them. Update anyway?" && return 0
            die "cancelled: wait for the actions in the panel (Actions) and run open-revoke update again"
        fi
        say "   waiting for $count write action(s) to finish ($waited s)..."
        sleep 15
        waited=$((waited + 15))
    done
}

rollback_to() {
    version=$1
    backup=$2
    [ -d "$INSTALL_DIR/releases/$version" ] || die "no saved files of $version in releases/"
    step "Going back to $version"
    put_bundle "$INSTALL_DIR/releases/$version"
    env_set OPEN_REVOKE_VERSION "$version" "$INSTALL_DIR/.env"
    compose stop app
    if [ -n "$backup" ] && [ -f "$backup" ]; then
        work=$(mktemp -d)
        # The whole archive (env, database.dump, VERSION): GNU tar stores members as ./name.
        tar -xzf "$backup" -C "$work"
        step "Restoring the database from $backup"
        restore_database "$work/database.dump"
        rm -rf "$work"
    else
        warn "no backup to restore: the database stays as the newer version left it"
    fi
    compose up -d --remove-orphans
    wait_healthy 300 || die "$version did not become healthy either; see: open-revoke logs app"
    rm -f "$INSTALL_DIR/$STATE_FILE"
    say "Back on Open Revoke $version. Apps signed in through the browser may ask for a new sign-in."
}

cmd_update() {
    target=""
    skip_backup=0
    while [ $# -gt 0 ]; do
        case $1 in
            --to) target=${2:?--to needs a version}; shift ;;
            --yes) ASSUME_YES=1 ;;
            --skip-backup) skip_backup=1 ;;
            *) die "unknown option for update: $1" ;;
        esac
        shift
    done
    current=$(env_get OPEN_REVOKE_VERSION)
    [ -n "$target" ] || target=$(latest_version)
    [ -n "$target" ] || die "cannot read the latest release from $(releases_url)"
    target=${target#v}
    if [ "$target" = "$current" ]; then
        say "Open Revoke $current is the latest release."
        return 0
    fi
    version_gt "$target" "$current" || die "$target is older than $current; go back with open-revoke rollback or restore"

    stage=$(mktemp -d)
    step "Downloading Open Revoke $target"
    download_bundle "$target" "$stage"
    mkdir "$stage/new"
    tar -xzf "$stage/bundle.tar.gz" -C "$stage/new"

    step "What changes from $current to $target"
    notes=$(changelog_between "$stage/new/CHANGELOG.md" "$target" "$current")
    say "${notes:-(no release notes)}"
    if printf '%s\n' "$notes" | grep -qi '^### Breaking'; then
        say ""
        say "This update has manual steps: read the Breaking sections above first."
    fi
    confirm "Update Open Revoke $current to $target?" || die "cancelled"

    step "Getting the images"
    ensure_images "$target" "$stage/new"

    step "Checking $target against this installation"
    report=$(OPEN_REVOKE_VERSION=$target docker compose --project-directory "$INSTALL_DIR" -f "$stage/new/compose.yaml" \
        run --rm --no-deps -T -w /app/backend --entrypoint /app/backend/.venv/bin/python app -m app.ops preflight) \
        || die "the new version refuses this installation: $report"

    step "Waiting for write actions in progress"
    wait_for_actions

    backup=""
    if [ "$skip_backup" = 1 ]; then
        warn "no backup (--skip-backup): a failed update cannot bring the data back"
    else
        cmd_backup
        backup=$BACKUP_LAST
    fi

    step "Installing $target"
    save_current_bundle "$current"
    printf 'PREVIOUS_VERSION=%s\nBACKUP=%s\n' "$current" "$backup" > "$INSTALL_DIR/$STATE_FILE"
    put_bundle "$stage/new"
    merge_env_keys "$INSTALL_DIR/.env.example"
    env_set OPEN_REVOKE_VERSION "$target" "$INSTALL_DIR/.env"
    rm -rf "$stage"

    step "Starting $target"
    compose up -d --remove-orphans
    if wait_healthy 300; then
        say "Updated Open Revoke $current -> $target."
        say "If something is wrong: open-revoke rollback (restores the database from before the update)."
        return 0
    fi
    warn "$target did not become healthy; going back automatically"
    compose logs --tail 40 app >&2 || true
    rollback_to "$current" "$backup"
    exit 1
}

cmd_rollback() {
    [ "${1:-}" = "--yes" ] && ASSUME_YES=1
    [ -f "$INSTALL_DIR/$STATE_FILE" ] || die "nothing to roll back: no update since the last rollback"
    previous=$(awk -F= '$1 == "PREVIOUS_VERSION" { print $2 }' "$INSTALL_DIR/$STATE_FILE")
    backup=$(awk -F= '$1 == "BACKUP" { sub(/^[^=]*=/, ""); print }' "$INSTALL_DIR/$STATE_FILE")
    say "Go back to Open Revoke $previous and restore the database from before the update?"
    say "Everything saved since the update (syncs, actions, audit log) is lost."
    confirm "Continue?" || die "cancelled"
    rollback_to "$previous" "$backup"
}
