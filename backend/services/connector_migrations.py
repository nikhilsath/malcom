"""Legacy connector storage migration helpers.

Promotes legacy connector state from the ``settings`` table into the canonical
``connectors`` and ``connector_auth_policies`` tables.
Primary entry point: ``ensure_legacy_connector_storage_migrated``.
"""

from __future__ import annotations

import json
from typing import Any

from backend.database import fetch_one
from backend.services.connector_catalog import (
    CONNECTOR_AUTH_POLICY_ROW_ID,
    CONNECTOR_AUTH_POLICY_SETTINGS_KEY,
    normalize_connector_auth_policy,
)
from backend.services.settings import (
    delete_stored_settings_section,
    read_stored_settings_section,
)
from backend.services.utils import utc_now_iso

DatabaseConnection = Any


def _read_connector_auth_policy_row(connection: DatabaseConnection) -> dict[str, Any] | None:
    row = fetch_one(
        connection,
        """
        SELECT auth_policy_json
        FROM connector_auth_policies
        WHERE policy_id = ?
        """,
        (CONNECTOR_AUTH_POLICY_ROW_ID,),
    )
    if row is None:
        return None

    try:
        parsed_value = json.loads(row["auth_policy_json"])
    except json.JSONDecodeError:
        return {"auth_policy": normalize_connector_auth_policy(None)}
    if not isinstance(parsed_value, dict):
        return {"auth_policy": normalize_connector_auth_policy(None)}
    return {"auth_policy": normalize_connector_auth_policy(parsed_value)}


def _migrate_legacy_connector_auth_policy_setting(
    connection: DatabaseConnection,
    settings_value: dict[str, Any],
    *,
    delete_connectors_row: bool = False,
) -> dict[str, Any]:
    auth_policy = normalize_connector_auth_policy(settings_value.get("auth_policy"))
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO connector_auth_policies (policy_id, auth_policy_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(policy_id) DO UPDATE SET
            auth_policy_json = excluded.auth_policy_json,
            updated_at = excluded.updated_at
        """,
        (CONNECTOR_AUTH_POLICY_ROW_ID, json.dumps(auth_policy), now, now),
    )
    connection.execute("DELETE FROM settings WHERE key = ?", (CONNECTOR_AUTH_POLICY_SETTINGS_KEY,))
    if delete_connectors_row:
        connection.execute("DELETE FROM settings WHERE key = ?", ("connectors",))
    connection.commit()
    return {"auth_policy": auth_policy}


def _read_connector_auth_policy_setting(connection: DatabaseConnection) -> dict[str, Any] | None:
    row_value = _read_connector_auth_policy_row(connection)
    if isinstance(row_value, dict):
        return row_value

    row_value = read_stored_settings_section(connection, CONNECTOR_AUTH_POLICY_SETTINGS_KEY)
    if isinstance(row_value, dict):
        return _migrate_legacy_connector_auth_policy_setting(connection, row_value)

    legacy_value = read_stored_settings_section(connection, "connectors")
    if isinstance(legacy_value, dict) and isinstance(legacy_value.get("auth_policy"), dict):
        return _migrate_legacy_connector_auth_policy_setting(connection, legacy_value, delete_connectors_row=False)
    return None


def _migrate_legacy_connectors_from_settings(connection: DatabaseConnection) -> None:
    from backend.services.connectors import replace_stored_connector_records, write_connector_auth_policy

    legacy_value = read_stored_settings_section(connection, "connectors")
    if not isinstance(legacy_value, dict):
        return

    legacy_records = [item for item in legacy_value.get("records", []) if isinstance(item, dict)]
    if legacy_records:
        replace_stored_connector_records(connection, legacy_records)

    auth_policy_value = legacy_value.get("auth_policy")
    if isinstance(auth_policy_value, dict):
        write_connector_auth_policy(connection, auth_policy_value)

    delete_stored_settings_section(connection, "connectors")


def ensure_legacy_connector_storage_migrated(connection: DatabaseConnection) -> None:
    _migrate_legacy_connectors_from_settings(connection)


__all__ = [
    "_migrate_legacy_connector_auth_policy_setting",
    "_migrate_legacy_connectors_from_settings",
    "_read_connector_auth_policy_row",
    "_read_connector_auth_policy_setting",
    "ensure_legacy_connector_storage_migrated",
]
