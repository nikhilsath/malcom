"""Contract tests for connector_migrations module."""
from __future__ import annotations
import inspect
import pytest
import backend.services.connector_migrations as migrations_module

EXPECTED_EXPORTS = {
    "ensure_legacy_connector_storage_migrated",
    "_read_connector_auth_policy_row",
    "_migrate_legacy_connector_auth_policy_setting",
    "_read_connector_auth_policy_setting",
    "_migrate_legacy_connectors_from_settings",
}


def test_all_expected_exports_present():
    for name in EXPECTED_EXPORTS:
        assert hasattr(migrations_module, name), f"Missing export: {name}"


def test_no_toplevel_connectors_import():
    """connector_migrations must use lazy imports for connectors module functions."""
    src = inspect.getsource(migrations_module)
    lines = src.split("\n")
    top_level_import_lines = [
        line for line in lines
        if line.startswith("from backend.services.connectors import") or
           line.startswith("import backend.services.connectors")
    ]
    assert len(top_level_import_lines) == 0, f"Found top-level connectors imports: {top_level_import_lines}"


def test_ensure_migration_is_idempotent():
    """Calling ensure_legacy_connector_storage_migrated multiple times must not fail."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS connector_auth_policies (
            policy_id TEXT PRIMARY KEY,
            auth_policy_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS connectors (
            id TEXT PRIMARY KEY,
            provider TEXT,
            name TEXT,
            status TEXT,
            auth_type TEXT,
            scopes_json TEXT,
            base_url TEXT,
            owner TEXT,
            docs_url TEXT,
            credential_ref TEXT,
            created_at TEXT,
            updated_at TEXT,
            auth_config_json TEXT,
            last_tested_at TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS integration_presets (
            id TEXT PRIMARY KEY,
            integration_type TEXT,
            name TEXT,
            description TEXT,
            category TEXT,
            auth_types_json TEXT,
            default_scopes_json TEXT,
            docs_url TEXT,
            base_url TEXT,
            created_at TEXT,
            updated_at TEXT
        );
    """)
    from backend.services.connector_migrations import ensure_legacy_connector_storage_migrated
    ensure_legacy_connector_storage_migrated(conn)
    ensure_legacy_connector_storage_migrated(conn)  # second call should not raise
