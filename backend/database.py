from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "malcom.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS inbound_apis (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            path_slug TEXT NOT NULL UNIQUE,
            auth_type TEXT NOT NULL,
            secret_hash TEXT NOT NULL,
            is_mock INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inbound_api_events (
            event_id TEXT PRIMARY KEY,
            api_id TEXT NOT NULL REFERENCES inbound_apis(id) ON DELETE CASCADE,
            received_at TEXT NOT NULL,
            status TEXT NOT NULL,
            request_headers_subset TEXT NOT NULL,
            payload_json TEXT,
            source_ip TEXT,
            error_message TEXT,
            is_mock INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS outgoing_scheduled_apis (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            path_slug TEXT NOT NULL UNIQUE,
            is_mock INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            repeat_enabled INTEGER NOT NULL DEFAULT 0,
            destination_url TEXT NOT NULL DEFAULT '',
            http_method TEXT NOT NULL DEFAULT 'POST',
            auth_type TEXT NOT NULL DEFAULT 'none',
            auth_config_json TEXT NOT NULL DEFAULT '{}',
            payload_template TEXT NOT NULL DEFAULT '{}',
            scheduled_time TEXT NOT NULL DEFAULT '09:00',
            schedule_expression TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS outgoing_continuous_apis (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            path_slug TEXT NOT NULL UNIQUE,
            is_mock INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            repeat_enabled INTEGER NOT NULL DEFAULT 0,
            repeat_interval_minutes INTEGER,
            destination_url TEXT NOT NULL DEFAULT '',
            http_method TEXT NOT NULL DEFAULT 'POST',
            auth_type TEXT NOT NULL DEFAULT 'none',
            auth_config_json TEXT NOT NULL DEFAULT '{}',
            payload_template TEXT NOT NULL DEFAULT '{}',
            stream_mode TEXT NOT NULL DEFAULT 'continuous',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS webhook_apis (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            path_slug TEXT NOT NULL UNIQUE,
            is_mock INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            delivery_mode TEXT NOT NULL DEFAULT 'webhook',
            callback_path TEXT NOT NULL DEFAULT '',
            verification_token TEXT NOT NULL DEFAULT '',
            signing_secret TEXT NOT NULL DEFAULT '',
            signature_header TEXT NOT NULL DEFAULT '',
            event_filter TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_description TEXT NOT NULL,
            name_override TEXT,
            description_override TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS automation_runs (
            run_id TEXT PRIMARY KEY,
            automation_id TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            status TEXT NOT NULL,
            worker_id TEXT,
            worker_name TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            duration_ms INTEGER,
            error_summary TEXT
        );

        CREATE TABLE IF NOT EXISTS automations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            trigger_type TEXT NOT NULL,
            trigger_config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT
        );

        CREATE TABLE IF NOT EXISTS automation_steps (
            step_id TEXT PRIMARY KEY,
            automation_id TEXT NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            step_type TEXT NOT NULL,
            name TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(automation_id, position)
        );

        CREATE TABLE IF NOT EXISTS automation_run_steps (
            step_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES automation_runs(run_id) ON DELETE CASCADE,
            step_name TEXT NOT NULL,
            status TEXT NOT NULL,
            request_summary TEXT,
            response_summary TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            duration_ms INTEGER,
            detail_json TEXT
        );

        CREATE TABLE IF NOT EXISTS scripts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL,
            code TEXT NOT NULL,
            validation_status TEXT NOT NULL DEFAULT 'unknown',
            validation_message TEXT,
            last_validated_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    _ensure_column(connection, "inbound_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "inbound_api_events", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_continuous_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "webhook_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "status", "TEXT NOT NULL DEFAULT 'active'")
    _ensure_column(connection, "outgoing_scheduled_apis", "repeat_enabled", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "destination_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "outgoing_scheduled_apis", "http_method", "TEXT NOT NULL DEFAULT 'POST'")
    _ensure_column(connection, "outgoing_scheduled_apis", "auth_type", "TEXT NOT NULL DEFAULT 'none'")
    _ensure_column(connection, "outgoing_scheduled_apis", "auth_config_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_scheduled_apis", "payload_template", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_scheduled_apis", "scheduled_time", "TEXT NOT NULL DEFAULT '09:00'")
    _ensure_column(connection, "outgoing_scheduled_apis", "last_run_at", "TEXT")
    _ensure_column(connection, "outgoing_scheduled_apis", "next_run_at", "TEXT")
    _ensure_column(connection, "outgoing_continuous_apis", "repeat_enabled", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_continuous_apis", "repeat_interval_minutes", "INTEGER")
    _ensure_column(connection, "outgoing_continuous_apis", "destination_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "outgoing_continuous_apis", "http_method", "TEXT NOT NULL DEFAULT 'POST'")
    _ensure_column(connection, "outgoing_continuous_apis", "auth_type", "TEXT NOT NULL DEFAULT 'none'")
    _ensure_column(connection, "outgoing_continuous_apis", "auth_config_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_continuous_apis", "payload_template", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "webhook_apis", "callback_path", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "verification_token", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "signing_secret", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "signature_header", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "event_filter", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "automation_runs", "worker_id", "TEXT")
    _ensure_column(connection, "automation_runs", "worker_name", "TEXT")
    _ensure_column(connection, "scripts", "validation_status", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(connection, "scripts", "validation_message", "TEXT")
    _ensure_column(connection, "scripts", "last_validated_at", "TEXT")
    _ensure_column(connection, "automations", "last_run_at", "TEXT")
    _ensure_column(connection, "automations", "next_run_at", "TEXT")
    connection.execute(
        """
        UPDATE outgoing_scheduled_apis
        SET status = CASE
            WHEN enabled = 1 THEN 'active'
            ELSE 'paused'
        END
        WHERE status IS NULL OR TRIM(status) = ''
        """
    )
    connection.commit()


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }

    if column_name in existing_columns:
        return

    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def fetch_one(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return connection.execute(query, params).fetchone()


def fetch_all(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return connection.execute(query, params).fetchall()
