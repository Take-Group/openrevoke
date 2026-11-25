# `open-revoke backup` and `open-revoke restore` (sourced after common.sh).
#
# A backup is one tar.gz in backups/: the open_revoke database (pg_dump custom format), a copy of
# .env (with OPEN_REVOKE_SECRET_KEY: treat the file like a password), the version, and with
# --with-browser the browser-profile volume (signed-in admin sessions). Temporal's own databases
# are not included: schedules are rebuilt by the worker at start.

BACKUP_LAST=""

cmd_backup() {
    with_browser=0
    for arg in "$@"; do
        case $arg in
            --with-browser) with_browser=1 ;;
            *) die "unknown option for backup: $arg" ;;
        esac
    done
    version=$(env_get OPEN_REVOKE_VERSION)
    stamp=$(date -u +%Y%m%d-%H%M%S)
    work=$(mktemp -d)
    mkdir -p "$INSTALL_DIR/backups"
    chmod 700 "$INSTALL_DIR/backups"
    step "Backing up the database (Open Revoke $version)"
    compose exec -T postgres pg_dump -U postgres -Fc open_revoke > "$work/database.dump" || {
        rm -rf "$work"
        die "pg_dump failed: is the postgres container running? (open-revoke status)"
    }
    cp "$INSTALL_DIR/.env" "$work/env"
    printf '%s\n' "$version" > "$work/VERSION"
    if [ "$with_browser" = 1 ]; then
        step "Backing up the browser profile"
        compose run --rm --no-deps -T -u 0 -v "$work:/out" --entrypoint tar browser czf /out/browser-profile.tgz -C /profile . \
            || warn "browser profile not saved"
    fi
    BACKUP_LAST="$INSTALL_DIR/backups/open-revoke-$version-$stamp.tar.gz"
    (umask 077 && tar -czf "$BACKUP_LAST" -C "$work" .)
    rm -rf "$work"
    say "Backup: $BACKUP_LAST"
    say "It contains .env with OPEN_REVOKE_SECRET_KEY: keep it like a password, off this server too."
}

# Replace the open_revoke database with the dump in $1 (the app container must be stopped).
restore_database() {
    dump=$1
    compose exec -T postgres psql -q -U postgres -d postgres -c "DROP DATABASE IF EXISTS open_revoke WITH (FORCE)" > /dev/null
    compose exec -T postgres createdb -U postgres open_revoke
    compose exec -T postgres pg_restore -U postgres -d open_revoke --no-owner < "$dump"
}

cmd_restore() {
    file=""
    with_browser=0
    for arg in "$@"; do
        case $arg in
            --with-browser) with_browser=1 ;;
            --yes) ASSUME_YES=1 ;;
            -*) die "unknown option for restore: $arg" ;;
            *) file=$arg ;;
        esac
    done
    [ -n "$file" ] || die "usage: open-revoke restore <backup.tar.gz> [--with-browser]"
    [ -f "$file" ] || die "no such file: $file"
    work=$(mktemp -d)
    tar -xzf "$file" -C "$work"
    [ -f "$work/database.dump" ] || die "$file is not an Open Revoke backup"
    from=$(cat "$work/VERSION")
    current=$(env_get OPEN_REVOKE_VERSION)
    if version_gt "$from" "$current"; then
        die "the backup is from Open Revoke $from, newer than this installation ($current). Update first."
    fi
    if [ "$(awk -F= '$1 == "OPEN_REVOKE_SECRET_KEY" { sub(/^[^=]*=/, ""); print }' "$work/env")" != "$(env_get OPEN_REVOKE_SECRET_KEY)" ]; then
        warn "OPEN_REVOKE_SECRET_KEY in the backup differs from .env: stored connector secrets will not decrypt."
        warn "The backup's .env is inside $file (file env) if you need its key."
    fi
    say "Restore $file (Open Revoke $from) over the current data? Everything saved since that backup is lost."
    confirm "Continue?" || die "cancelled"
    step "Stopping the app"
    compose stop app
    step "Restoring the database"
    restore_database "$work/database.dump"
    if [ "$with_browser" = 1 ] && [ -f "$work/browser-profile.tgz" ]; then
        step "Restoring the browser profile"
        compose stop browser
        compose run --rm --no-deps -T -u 0 -v "$work:/in" --entrypoint sh browser -c \
            'find /profile -mindepth 1 -delete && tar xzf /in/browser-profile.tgz -C /profile && chown -R 1000:1000 /profile'
    fi
    rm -rf "$work"
    step "Starting"
    compose up -d
    wait_healthy 300 || die "the app did not become healthy; see: open-revoke logs app"
    say "Restored."
}
