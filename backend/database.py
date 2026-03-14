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
            error_message TEXT
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
        """
    )
    connection.commit()


def fetch_one(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return connection.execute(query, params).fetchone()


def fetch_all(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return connection.execute(query, params).fetchall()
