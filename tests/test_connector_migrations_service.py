"""Unit tests for connector_migrations module."""
from __future__ import annotations
import json
import sqlite3
import pytest
from backend.services.connector_migrations import (
    ensure_legacy_connector_storage_migrated,
    _read_connector_auth_policy_row,
    _migrate_legacy_connector_auth_policy_setting,
)
from backend.services.connector_catalog import CONNECTOR_AUTH_POLICY_ROW_ID


def _make_memory_db():
    """Create a minimal in-memory SQLite DB with required tables."""
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
    return conn


def test_read_auth_policy_row_empty_db():
    conn = _make_memory_db()
    result = _read_connector_auth_policy_row(conn)
    assert result is None


def test_read_auth_policy_row_with_data():
    conn = _make_memory_db()
    policy = {"rotation_interval_days": 30, "reconnect_requires_approval": False, "credential_visibility": "masked"}
    conn.execute(
        "INSERT INTO connector_auth_policies (policy_id, auth_policy_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (CONNECTOR_AUTH_POLICY_ROW_ID, json.dumps(policy), "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()
    result = _read_connector_auth_policy_row(conn)
    assert result is not None
    assert result["auth_policy"]["rotation_interval_days"] == 30


def test_migrate_legacy_connector_auth_policy_setting():
    conn = _make_memory_db()
    settings_value = {"auth_policy": {"rotation_interval_days": 60, "reconnect_requires_approval": True, "credential_visibility": "masked"}}
    result = _migrate_legacy_connector_auth_policy_setting(conn, settings_value)
    assert result["auth_policy"]["rotation_interval_days"] == 60
    # verify it was persisted
    row = _read_connector_auth_policy_row(conn)
    assert row is not None


def test_ensure_legacy_connector_storage_migrated_no_legacy():
    """Should be a no-op when no legacy settings row exists."""
    conn = _make_memory_db()
    ensure_legacy_connector_storage_migrated(conn)  # should not raise


def test_ensure_legacy_connector_storage_migrated_with_legacy():
    conn = _make_memory_db()
    legacy_value = {
        "records": [
            {
                "id": "connector_abc123",
                "provider": "github",
                "name": "Test GitHub",
                "status": "connected",
                "auth_type": "bearer",
                "scopes": [],
                "auth_config": {},
            }
        ],
        "auth_policy": {"rotation_interval_days": 90, "reconnect_requires_approval": True, "credential_visibility": "masked"},
    }
    conn.execute(
        "INSERT INTO settings (key, value_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
        ("connectors", json.dumps(legacy_value), "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
    )
    conn.commit()

    ensure_legacy_connector_storage_migrated(conn)

    # The connector should now be in the connectors table
    row = conn.execute("SELECT id FROM connectors WHERE id = ?", ("connector_abc123",)).fetchone()
    assert row is not None
    # The settings row should be gone
    settings_row = conn.execute("SELECT key FROM settings WHERE key = 'connectors'").fetchone()
    assert settings_row is None
