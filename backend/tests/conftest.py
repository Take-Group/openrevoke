"""Shared setup. Unit tests need only OPEN_REVOKE_SECRET_KEY; tests marked ``integration`` also
need a migrated PostgreSQL (DATABASE_URL) and Redis (REDIS_URL). How to run: CONTRIBUTING.md."""

import os

from cryptography.fernet import Fernet

# Before any app module reads the settings: a throwaway key when none is set.
os.environ.setdefault("OPEN_REVOKE_SECRET_KEY", Fernet.generate_key().decode())
