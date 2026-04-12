from __future__ import annotations

import json
import re
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


def delete_stored_settings_section(connection: Any, key: str) -> None:
    """Delete *key* from the settings table and commit."""
    connection.execute("DELETE FROM settings WHERE key = ?", (key,))
    connection.commit()


_SENSITIVE_PAYLOAD_FIELD_PATTERNS = (
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "private_key",
    "credential",
    "password",
    "secret",
    "token",
    "cookie",
    "session",
)
_REDACTED_PAYLOAD_VALUE = "[redacted]"


def _normalize_sensitive_payload_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _is_sensitive_payload_key(key: Any) -> bool:
    normalized_key = _normalize_sensitive_payload_key(key)
    if not normalized_key:
        return False
    return any(pattern in normalized_key for pattern in _SENSITIVE_PAYLOAD_FIELD_PATTERNS)


def redact_sensitive_payload_sample(value: Any, *, enabled: bool = True) -> Any:
    """Return a redacted copy of a stored event sample when redaction is enabled."""
    if not enabled:
        return value

    if isinstance(value, dict):
        redacted_value: dict[Any, Any] = {}
        for key, item in value.items():
            if _is_sensitive_payload_key(key):
                redacted_value[key] = _REDACTED_PAYLOAD_VALUE
            else:
                redacted_value[key] = redact_sensitive_payload_sample(item, enabled=True)
        return redacted_value

    if isinstance(value, list):
        return [redact_sensitive_payload_sample(item, enabled=True) for item in value]

    return value


__all__ = [
    "delete_stored_settings_section",
    "merge_settings_section",
    "read_stored_settings_section",
    "redact_sensitive_payload_sample",
    "write_settings_section",
]
