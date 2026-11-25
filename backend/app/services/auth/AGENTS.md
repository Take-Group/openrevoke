# open-revoke/backend/app/services/auth/

Panel sign-in. Flow: `sign_in.login` checks the password and opens a session (`sessions`), or, with 2FA on, returns a ticket (`tickets`) that a TOTP code (`totp`) in `sign_in.complete` turns into a session. Called by `app/api/` auth endpoints.

- `__init__.py`: docstring only.
- `actor.py`: context var with the current user for the audit log; the API sets it, workflows and CLI keep the default.
- `sign_in.py`: `setup_required`, `setup` (first-run admin and organization with the setup token, the only 2FA offer), `login` and `register` (`SignInResult`: a session at once without 2FA, a ticket with it), `complete`, `skip_enrollment`, `invite_info`, `logout`.
- `two_factor.py`: Settings 2FA `start`, `enable` (first code), `disable` (current code, rate-limited).
- `tickets.py`: `issue`, `load`, `discard`; short-lived second-step ticket in Redis, can carry an encrypted new TOTP secret.
- `totp.py`: `new_secret`, `enrollment`, `matching_step` (RFC 6238, replay guard through `after_step`).
- `sessions.py`: `create`, `find`, `revoke`, `revoke_all`; random cookie token, SHA-256 stored in `user_session`.
- `passwords.py`: `check_policy`, `hash_password`, `verify_password` (Argon2id).
- `passwords_flow.py`: `issue_link` (admin or CLI reset link, 24 h), `reset`, `change`.
- `api_tokens.py`: personal API tokens for the REST API and MCP: `create`, `list_for_user`, `revoke`, `authenticate` (active owner, touches `last_used_at`), `actor_name`, `hash_token`.
- `tokens.py`: one-time link tokens (invite, reset) `create`, `find_valid`, `consume`, `revoke_open`, `hash_token`.
- `invites.py`: `list_open`, `create`, `revoke`; invite links (role chosen by the admin).
- `signup.py`: self sign-up `sign_up` (active for an auto-approved domain, else pending), `auto_approves`, `email_domain`, `sign_in_blocker` (pending accounts cannot sign in).
- `users.py`: admin actions `list_users`, `approve`, `set_role`, `reset_totp`, `remove` (also rejects a sign-up).
- `setup_link.py`: first-run setup token: `issue` (new link, old one stops working), `is_valid`, `require_valid` (403), `discard`, `announce` (log line at API start); SHA-256 in Redis key `open-revoke:auth:setup-token`.
- `rate_limit.py`: Redis counters `hit`, `enforce`, `reset` for sign-in, sign-up and turning 2FA off.
