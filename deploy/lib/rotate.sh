# `open-revoke rotate-key` (sourced after common.sh and backup.sh).
#
# Replaces OPEN_REVOKE_SECRET_KEY and re-encrypts every stored secret with the new key: a backup
# first, then the new key in .env with the old one as OPEN_REVOKE_SECRET_KEY_PREVIOUS (it still
# decrypts), a restart, `python -m app.cli rotate-secrets`, and a restart without the old key.
# Interrupted halfway, .env keeps both keys and running the command again finishes the rotation.

cmd_rotate_key() {
    for arg in "$@"; do
        case $arg in
            --yes) ASSUME_YES=1 ;;
            *) die "unknown option for rotate-key: $arg" ;;
        esac
    done
    if [ -n "$(env_get OPEN_REVOKE_SECRET_KEY_PREVIOUS)" ]; then
        say "OPEN_REVOKE_SECRET_KEY_PREVIOUS is set: finishing the rotation that was interrupted."
        finish_key_rotation
        return
    fi
    [ -n "$(env_get OPEN_REVOKE_SECRET_KEY)" ] || die "OPEN_REVOKE_SECRET_KEY is empty in .env"
    say "This replaces OPEN_REVOKE_SECRET_KEY and re-encrypts the stored connector secrets, 2FA"
    say "secrets and API keys with a new key. The panel restarts twice (about a minute each)."
    confirm "Rotate the key now?" || die "cancelled"
    cmd_backup
    rotation_backup=$BACKUP_LAST
    old_key=$(env_get OPEN_REVOKE_SECRET_KEY)
    new_key=$(openssl rand -base64 32 | tr '+/' '-_')
    [ ${#new_key} = 44 ] || die "could not generate a new key (is openssl installed?)"
    env_set OPEN_REVOKE_SECRET_KEY_PREVIOUS "$old_key" "$INSTALL_DIR/.env"
    env_set OPEN_REVOKE_SECRET_KEY "$new_key" "$INSTALL_DIR/.env"
    finish_key_rotation
    say "The backup made before the rotation ($rotation_backup) holds the old key and data"
    say "encrypted with it; restoring it brings the old key back too."
}

finish_key_rotation() {
    step "Starting with the new key (the old one still decrypts)"
    compose up -d app && wait_healthy 300 \
        || die "the app did not start; .env keeps both keys. See open-revoke logs app, then run open-revoke rotate-key again"
    step "Re-encrypting stored secrets"
    app_python app.cli rotate-secrets \
        || die "some secrets could not be re-encrypted (listed above); .env keeps both keys. Run open-revoke rotate-key again, or enter those secrets in the panel"
    env_set OPEN_REVOKE_SECRET_KEY_PREVIOUS "" "$INSTALL_DIR/.env"
    step "Restarting without the old key"
    compose up -d app && wait_healthy 300 || die "the app did not start without the old key: open-revoke logs app"
    say "Done. Store the new OPEN_REVOKE_SECRET_KEY from $INSTALL_DIR/.env in your password manager"
    say "and remove the old one from it."
}
