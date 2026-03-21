#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import connect, initialize
from tests.postgres_test_utils import get_test_database_url


def main() -> int:
    database_url = get_test_database_url()

    try:
        connection = connect(database_url=database_url)
    except Exception as error:  # pragma: no cover - exercised by shell scripts
        print(
            "PostgreSQL test preflight failed: could not connect to "
            f"{database_url!r}. Set MALCOM_TEST_DATABASE_URL or MALCOM_DATABASE_URL to a reachable local PostgreSQL instance. "
            f"Original error: {error}",
            file=sys.stderr,
        )
        return 1

    try:
        initialize(connection)
    except Exception as error:  # pragma: no cover - exercised by shell scripts
        print(
            "PostgreSQL test preflight failed while initializing the schema. "
            f"Original error: {error}",
            file=sys.stderr,
        )
        return 1
    finally:
        connection.close()

    print(f"PostgreSQL test preflight succeeded for {database_url}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
