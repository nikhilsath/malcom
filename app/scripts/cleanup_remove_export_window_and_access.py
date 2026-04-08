"""Cleanup script: remove deprecated settings keys.

Removes `export_window_utc` from the stored `data` settings and deletes
the entire `access` settings section if present. Safe to run multiple
times; prints a summary of actions taken.

Usage: python scripts/cleanup_remove_export_window_and_access.py
Ensure `MALCOM_DATABASE_URL` is set to the target database URL.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from backend.database import connect, get_database_url
from backend.services.settings import (
    read_stored_settings_section,
    write_settings_section,
    delete_stored_settings_section,
)


def main() -> int:
    database_url = os.getenv("MALCOM_DATABASE_URL") or get_database_url()
    try:
        conn = connect(database_url=database_url)
    except Exception as exc:  # pragma: no cover - operational script
        print(f"ERROR: could not connect to database: {exc}")
        return 2

    actions = []

    # Remove export_window_utc from stored `data` settings if present.
    stored_data = read_stored_settings_section(conn, "data")
    if isinstance(stored_data, dict) and "export_window_utc" in stored_data:
        new_data = dict(stored_data)
        new_data.pop("export_window_utc", None)
        # If new_data is empty, delete the section entirely; otherwise write back.
        if new_data:
            write_settings_section(conn, "data", new_data)
            actions.append("removed export_window_utc from 'data' and updated section")
        else:
            delete_stored_settings_section(conn, "data")
            actions.append("removed export_window_utc and deleted empty 'data' section")
    else:
        actions.append("no export_window_utc found in 'data' settings")

    # Delete the entire 'access' settings section if present.
    stored_access = read_stored_settings_section(conn, "access")
    if stored_access is not None:
        delete_stored_settings_section(conn, "access")
        actions.append("deleted 'access' settings section")
    else:
        actions.append("no 'access' settings section present")

    print("Cleanup actions:")
    for a in actions:
        print(" - ", a)

    return 0


if __name__ == "__main__":
    sys.exit(main())
