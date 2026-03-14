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
            started_at TEXT NOT NULL,
            finished_at TEXT,
            duration_ms INTEGER,
            error_summary TEXT
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
        """
    )
    _ensure_column(connection, "inbound_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "inbound_api_events", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_continuous_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "webhook_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
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
