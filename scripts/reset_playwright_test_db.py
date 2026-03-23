#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.postgres_test_utils import get_test_database_url, reset_database


def main() -> int:
    database_url = get_test_database_url()
    reset_database(database_url)
    print(f"Reset Playwright test database at {database_url}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
