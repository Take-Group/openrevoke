"""Print the OpenAPI schema of the API as pretty JSON.

The frontend's API types follow this file. Regenerate docs/openapi.json after
every change of an endpoint or schema (from the repository root, local stack):

    dc exec -T api python scripts/export_openapi.py > docs/openapi.json
"""

import json
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the backend directory, home of ``app``

# Settings need a key to load; the schema does not depend on its value.
os.environ.setdefault("OPEN_REVOKE_SECRET_KEY", Fernet.generate_key().decode())

from app.main import app  # noqa: E402


def main() -> None:
    json.dump(app.openapi(), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
