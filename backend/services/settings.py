from __future__ import annotations

import json
from typing import Any

from backend.database import fetch_one
from backend.services.utils import utc_now_iso


def merge_settings_section(default_value: Any, stored_value: Any) -> Any:
    """Merge a stored settings section over its defaults.

    If both values are dicts, stored values take precedence for each key while
    any key present only in the default is preserved.  For scalar values the
    stored value is returned unchanged.
    """
    if not isinstance(default_value, dict) or not isinstance(stored_value, dict):
        return stored_value

    merged_value = dict(default_value)
    merged_value.update(stored_value)
    return merged_value


def read_stored_settings_section(connection: Any, key: str) -> Any:
    """Return the parsed JSON value stored for *key*, or ``None`` if absent."""
    row = fetch_one(connection, "SELECT value_json FROM settings WHERE key = ?", (key,))
    if row is None:
        return None

    try:
        return json.loads(row["value_json"])
    except json.JSONDecodeError:
        return None


def write_settings_section(connection: Any, key: str, value: Any) -> None:
    """Upsert *value* for *key* in the settings table and commit."""
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO settings (key, value_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        (key, json.dumps(value), now, now),
    )
    connection.commit()


__all__ = [
    "merge_settings_section",
    "read_stored_settings_section",
    "write_settings_section",
]
