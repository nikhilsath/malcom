#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import connect, get_database_url, initialize
from backend.services.docs import sync_docs_from_repo


def main() -> int:
    connection = connect(database_url=get_database_url())
    try:
        initialize(connection)
        synced = sync_docs_from_repo(connection, ROOT_DIR)
    finally:
        connection.close()

    print(f"Synced {synced} docs markdown file(s) into docs_articles metadata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
