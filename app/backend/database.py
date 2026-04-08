from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


DEFAULT_POSTGRES_URL = "postgresql://postgres:postgres@127.0.0.1:5432/malcom"
DatabaseConnection = Any


CREATE_SCHEMA_SQL = """
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
    webhook_signing_json TEXT NOT NULL DEFAULT '{}',
    payload_template TEXT NOT NULL DEFAULT '{}',
    scheduled_time TEXT NOT NULL DEFAULT '09:00',
    schedule_expression TEXT NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT,
    last_error TEXT,
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
    webhook_signing_json TEXT NOT NULL DEFAULT '{}',
    payload_template TEXT NOT NULL DEFAULT '{}',
    stream_mode TEXT NOT NULL DEFAULT 'continuous',
    last_run_at TEXT,
    next_run_at TEXT,
    last_error TEXT,
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

CREATE TABLE IF NOT EXISTS webhook_api_events (
    event_id TEXT PRIMARY KEY,
    api_id TEXT NOT NULL REFERENCES webhook_apis(id) ON DELETE CASCADE,
    received_at TEXT NOT NULL,
    status TEXT NOT NULL,
    event_name TEXT,
    verification_ok INTEGER NOT NULL DEFAULT 0,
    signature_ok INTEGER NOT NULL DEFAULT 0,
    request_headers_subset TEXT NOT NULL DEFAULT '{}',
    payload_json TEXT,
    raw_body TEXT,
    source_ip TEXT,
    error_message TEXT,
    triggered_automation_count INTEGER NOT NULL DEFAULT 0,
    is_mock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS outgoing_delivery_history (
    delivery_id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    status TEXT NOT NULL,
    http_status_code INTEGER,
    request_summary TEXT,
    response_summary TEXT,
    error_summary TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS runtime_resource_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    captured_at TEXT NOT NULL,
    process_memory_mb REAL NOT NULL DEFAULT 0,
    process_cpu_percent REAL NOT NULL DEFAULT 0,
    queue_pending_jobs INTEGER NOT NULL DEFAULT 0,
    queue_claimed_jobs INTEGER NOT NULL DEFAULT 0,
    tracked_operations INTEGER NOT NULL DEFAULT 0,
    total_error_count INTEGER NOT NULL DEFAULT 0,
    hottest_operation TEXT,
    hottest_total_duration_ms REAL NOT NULL DEFAULT 0,
    max_memory_peak_mb REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_description TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS integration_presets (
    id TEXT PRIMARY KEY,
    integration_type TEXT NOT NULL DEFAULT 'connector_provider',
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general',
    auth_types_json TEXT NOT NULL DEFAULT '[]',
    default_scopes_json TEXT NOT NULL DEFAULT '[]',
    docs_url TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
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
    detail_json TEXT,
    response_body_json TEXT,
    extracted_fields_json TEXT,
    inputs_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS scripts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL,
    sample_input TEXT NOT NULL DEFAULT '',
    expected_output TEXT NOT NULL DEFAULT '{}',
    code TEXT NOT NULL,
    validation_status TEXT NOT NULL DEFAULT 'unknown',
    validation_message TEXT,
    last_validated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS log_db_tables (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS log_db_columns (
    id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL REFERENCES log_db_tables(id) ON DELETE CASCADE,
    column_name TEXT NOT NULL,
    data_type TEXT NOT NULL DEFAULT 'text',
    nullable INTEGER NOT NULL DEFAULT 1,
    default_value TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(table_id, column_name)
);

CREATE TABLE IF NOT EXISTS connectors (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    auth_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS automations_enabled_trigger_type_next_run_at_idx
    ON automations (enabled, trigger_type, next_run_at);

CREATE INDEX IF NOT EXISTS outgoing_scheduled_apis_enabled_next_run_at_idx
    ON outgoing_scheduled_apis (enabled, next_run_at);

CREATE INDEX IF NOT EXISTS outgoing_continuous_apis_enabled_repeat_enabled_next_run_at_idx
    ON outgoing_continuous_apis (enabled, repeat_enabled, next_run_at);

CREATE INDEX IF NOT EXISTS automation_runs_automation_id_started_at_idx
    ON automation_runs (automation_id, started_at);

CREATE TABLE IF NOT EXISTS docs_articles (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    source_path TEXT NOT NULL DEFAULT '',
    is_ai_created INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS docs_tags (
    id TEXT PRIMARY KEY,
    tag TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'freeform',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS docs_article_tags (
    article_id TEXT NOT NULL REFERENCES docs_articles(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES docs_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, tag_id)
);

CREATE INDEX IF NOT EXISTS automation_run_steps_run_id_idx
    ON automation_run_steps (run_id);

CREATE INDEX IF NOT EXISTS automation_runs_next_run_at_idx
    ON automation_runs (automation_id, status);

CREATE INDEX IF NOT EXISTS connectors_provider_status_idx
    ON connectors (provider, status);

CREATE TABLE IF NOT EXISTS storage_locations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location_type TEXT NOT NULL,
    path TEXT,
    connector_id TEXT REFERENCES connectors(id) ON DELETE SET NULL,
    folder_template TEXT,
    file_name_template TEXT,
    max_size_mb INTEGER,
    is_default_logs INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repo_checkouts (
    id TEXT PRIMARY KEY,
    storage_location_id TEXT NOT NULL REFERENCES storage_locations(id) ON DELETE CASCADE,
    repo_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT 'main',
    last_synced_at TEXT,
    size_bytes INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS storage_locations_type_idx
    ON storage_locations (location_type);

CREATE INDEX IF NOT EXISTS repo_checkouts_location_idx
    ON repo_checkouts (storage_location_id);

CREATE INDEX IF NOT EXISTS runtime_resource_snapshots_captured_at_idx
    ON runtime_resource_snapshots (captured_at DESC);

CREATE INDEX IF NOT EXISTS runtime_resource_snapshots_queue_idx
    ON runtime_resource_snapshots (queue_pending_jobs, queue_claimed_jobs);
"""


class PostgresCursorAdapter:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._cursor.fetchall()]


class PostgresConnectionAdapter:
    def __init__(self, connection: Any):
        self._connection = connection
        self.backend = "postgres"

    def execute(self, query: str, params: Sequence[Any] = ()) -> PostgresCursorAdapter:
        translated_query = _translate_qmark_placeholders(query)
        cursor = self._connection.execute(translated_query, tuple(params))
        return PostgresCursorAdapter(cursor)

    def executescript(self, script: str) -> None:
        for statement in _split_sql_script(script):
            self.execute(statement)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def connect(*, database_url: str) -> Any:
    if not _is_postgres_url(database_url):
        raise RuntimeError("MALCOM_DATABASE_URL must be a valid PostgreSQL URL (postgresql://...)")
    return _connect_postgres(database_url)


def get_database_url() -> str:
    return os.getenv("MALCOM_DATABASE_URL", DEFAULT_POSTGRES_URL).strip()


def is_unique_violation(error: Exception) -> bool:
    sqlstate = getattr(error, "sqlstate", None)
    if sqlstate == "23505":
        return True

    cause = getattr(error, "__cause__", None)
    if cause is not None and getattr(cause, "sqlstate", None) == "23505":
        return True

    message = str(error).lower()
    return "duplicate key value violates unique constraint" in message


def initialize(connection: Any) -> None:
    connection.executescript(CREATE_SCHEMA_SQL)
    _ensure_column(connection, "inbound_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "inbound_api_events", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_continuous_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "webhook_apis", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "webhook_api_events", "is_mock", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "status", "TEXT NOT NULL DEFAULT 'active'")
    _ensure_column(connection, "outgoing_scheduled_apis", "repeat_enabled", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_scheduled_apis", "destination_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "outgoing_scheduled_apis", "http_method", "TEXT NOT NULL DEFAULT 'POST'")
    _ensure_column(connection, "outgoing_scheduled_apis", "auth_type", "TEXT NOT NULL DEFAULT 'none'")
    _ensure_column(connection, "outgoing_scheduled_apis", "auth_config_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_scheduled_apis", "webhook_signing_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_scheduled_apis", "payload_template", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_scheduled_apis", "scheduled_time", "TEXT NOT NULL DEFAULT '09:00'")
    _ensure_column(connection, "outgoing_scheduled_apis", "last_run_at", "TEXT")
    _ensure_column(connection, "outgoing_scheduled_apis", "next_run_at", "TEXT")
    _ensure_column(connection, "outgoing_scheduled_apis", "last_error", "TEXT")
    _ensure_column(connection, "outgoing_continuous_apis", "repeat_enabled", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_continuous_apis", "repeat_interval_minutes", "INTEGER")
    _ensure_column(connection, "outgoing_continuous_apis", "destination_url", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "outgoing_continuous_apis", "http_method", "TEXT NOT NULL DEFAULT 'POST'")
    _ensure_column(connection, "outgoing_continuous_apis", "auth_type", "TEXT NOT NULL DEFAULT 'none'")
    _ensure_column(connection, "outgoing_continuous_apis", "auth_config_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_continuous_apis", "webhook_signing_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_continuous_apis", "payload_template", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "outgoing_continuous_apis", "last_run_at", "TEXT")
    _ensure_column(connection, "outgoing_continuous_apis", "next_run_at", "TEXT")
    _ensure_column(connection, "outgoing_continuous_apis", "last_error", "TEXT")
    _ensure_column(connection, "webhook_apis", "callback_path", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "verification_token", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "signing_secret", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "signature_header", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_apis", "event_filter", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "webhook_api_events", "event_name", "TEXT")
    _ensure_column(connection, "webhook_api_events", "verification_ok", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "webhook_api_events", "signature_ok", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "webhook_api_events", "request_headers_subset", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "webhook_api_events", "payload_json", "TEXT")
    _ensure_column(connection, "webhook_api_events", "raw_body", "TEXT")
    _ensure_column(connection, "webhook_api_events", "source_ip", "TEXT")
    _ensure_column(connection, "webhook_api_events", "error_message", "TEXT")
    _ensure_column(connection, "webhook_api_events", "triggered_automation_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "outgoing_delivery_history", "http_status_code", "INTEGER")
    _ensure_column(connection, "outgoing_delivery_history", "request_summary", "TEXT")
    _ensure_column(connection, "outgoing_delivery_history", "response_summary", "TEXT")
    _ensure_column(connection, "outgoing_delivery_history", "error_summary", "TEXT")
    _ensure_column(connection, "outgoing_delivery_history", "finished_at", "TEXT")
    _ensure_column(connection, "runtime_resource_snapshots", "process_memory_mb", "REAL NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "process_cpu_percent", "REAL NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "queue_pending_jobs", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "queue_claimed_jobs", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "tracked_operations", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "total_error_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "hottest_operation", "TEXT")
    _ensure_column(connection, "runtime_resource_snapshots", "hottest_total_duration_ms", "REAL NOT NULL DEFAULT 0")
    _ensure_column(connection, "runtime_resource_snapshots", "max_memory_peak_mb", "REAL NOT NULL DEFAULT 0")
    _ensure_column(connection, "tools", "enabled", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "tools", "inputs_schema_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(connection, "tools", "outputs_schema_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(connection, "automation_run_steps", "inputs_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "automation_run_steps", "response_body_json", "TEXT")
    _ensure_column(connection, "automation_run_steps", "extracted_fields_json", "TEXT")
    _ensure_column(connection, "automation_runs", "worker_id", "TEXT")
    _ensure_column(connection, "automation_runs", "worker_name", "TEXT")
    _ensure_column(connection, "scripts", "validation_status", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(connection, "scripts", "validation_message", "TEXT")
    _ensure_column(connection, "scripts", "last_validated_at", "TEXT")
    _ensure_column(connection, "scripts", "sample_input", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "scripts", "expected_output", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "automations", "last_run_at", "TEXT")
    _ensure_column(connection, "automations", "next_run_at", "TEXT")
    _ensure_column(connection, "automation_steps", "on_true_step_id", "TEXT")
    _ensure_column(connection, "automation_steps", "on_false_step_id", "TEXT")
    _ensure_column(connection, "automation_steps", "is_merge_target", "INTEGER NOT NULL DEFAULT 0")
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


def _connect_postgres(database_url: str) -> PostgresConnectionAdapter:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "PostgreSQL is configured but psycopg is not installed. Add 'psycopg[binary]' to requirements."
        ) from error

    raw_connection = psycopg.connect(database_url, autocommit=False, row_factory=dict_row)
    return PostgresConnectionAdapter(raw_connection)


def _split_sql_script(script: str) -> list[str]:
    return [segment.strip() for segment in script.split(";") if segment.strip()]


def _is_postgres_url(database_url: str | None) -> bool:
    if not database_url:
        return False
    normalized = database_url.strip().lower()
    return normalized.startswith("postgresql://") or normalized.startswith("postgres://")


def _translate_qmark_placeholders(query: str) -> str:
    builder: list[str] = []
    in_single_quote = False
    in_double_quote = False
    index = 0

    while index < len(query):
        char = query[index]

        if char == "'" and not in_double_quote:
            if in_single_quote and index + 1 < len(query) and query[index + 1] == "'":
                builder.append("''")
                index += 2
                continue
            in_single_quote = not in_single_quote
            builder.append(char)
            index += 1
            continue

        if char == '"' and not in_single_quote:
            if in_double_quote and index + 1 < len(query) and query[index + 1] == '"':
                builder.append('""')
                index += 2
                continue
            in_double_quote = not in_double_quote
            builder.append(char)
            index += 1
            continue

        if char == "?" and not in_single_quote and not in_double_quote:
            builder.append("%s")
        else:
            builder.append(char)

        index += 1

    return "".join(builder)


def _quote_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return f'"{identifier}"'


def _ensure_column(connection: Any, table_name: str, column_name: str, definition: str) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ?
          AND column_name = ?
        LIMIT 1
        """,
        (table_name, column_name),
    ).fetchone()
    if row is not None:
        return

    quoted_table = _quote_identifier(table_name)
    quoted_column = _quote_identifier(column_name)
    connection.execute(f"ALTER TABLE {quoted_table} ADD COLUMN IF NOT EXISTS {quoted_column} {definition}")


def fetch_one(connection: Any, query: str, params: Sequence[Any] = ()) -> Mapping[str, Any] | None:
    return connection.execute(query, tuple(params)).fetchone()


def fetch_all(connection: Any, query: str, params: Sequence[Any] = ()) -> list[Mapping[str, Any]]:
    return connection.execute(query, tuple(params)).fetchall()


def run_migrations(*, database_url: str) -> None:
    """Run Alembic migrations to head against the given database URL."""
    from alembic import command
    from alembic.config import Config

    project_root = Path(__file__).parent.parent.parent
    cfg = Config(str(project_root / "data" / "config" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(project_root / "app" / "backend" / "migrations"))
    command.upgrade(cfg, "head")
