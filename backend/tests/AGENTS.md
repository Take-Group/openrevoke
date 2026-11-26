# open-revoke/backend/tests/

pytest. Policy and commands: `../../CONTRIBUTING.md`, "Tests". Security code and major features add tests here. `conftest.py` sets a throwaway `OPEN_REVOKE_SECRET_KEY` before the app reads its settings.

- `__init__.py`: empty.
- `conftest.py`: throwaway secret key.
- `test_secret_box.py`: encryption, wrong key, rotation with `OPEN_REVOKE_SECRET_KEY_PREVIOUS`.
- `test_config.py`: key from `OPEN_REVOKE_SECRET_KEY_FILE`, previous keys, invalid keys refused.
- `test_auth_basics.py`: Argon2id, password policy, TOTP replay guard, `client_ip`, `safe_cell`.
- `integration/`, no map: marker `integration`, needs a migrated PostgreSQL and Redis: `test_audit_log.py` (append-only trigger, export), `test_sign_in.py` (limits per address, failed sign-in audit).
