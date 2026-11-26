# open-revoke/backend/tests/

pytest. Policy and commands: `../../CONTRIBUTING.md`, "Tests". Security code and major features add tests here. `conftest.py` sets a throwaway `OPEN_REVOKE_SECRET_KEY` before the app reads its settings.

- `__init__.py`: empty.
- `conftest.py`: throwaway secret key.
- `test_secret_box.py`: encryption, wrong key, rotation with `OPEN_REVOKE_SECRET_KEY_PREVIOUS`.
- `test_config.py`: key from `OPEN_REVOKE_SECRET_KEY_FILE`, previous keys, invalid keys refused.
- `test_auth_basics.py`: Argon2id, password policy, TOTP replay guard, `client_ip`, `safe_cell`.
- `test_google_assertion.py`: the service account JWT is a valid RS256 token; a non-RSA key is refused.
- `test_input_rules.py`: e-mail with two `@`, http(s)-only app links, connector URL fields that bind the secrets.
- `integration/`, no map: marker `integration`, needs a migrated PostgreSQL and Redis: `test_audit_log.py` (append-only trigger, export), `test_sign_in.py` (limits per address, failed sign-in audit), `test_security_rules.py` (2FA ticket purpose and single use, one code per sign-in across parallel tickets, wrong codes per account, connector and AI secrets bound to their URL, no automatic approval of a self-chosen role).
