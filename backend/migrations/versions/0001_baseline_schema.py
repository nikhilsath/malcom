"""baseline schema

Revision ID: 0001_baseline_schema
Revises:
Create Date: 2026-04-03 00:00:00

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_STATEMENTS = (
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
    )
    """,
    """
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
    )
    """,
    """
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
    )
    """,
    """
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
    )
    """,
    """
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
    )
    """,
    """
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
    )
    """,
    """
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
    )
    """,
    """
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
        max_memory_peak_mb REAL NOT NULL DEFAULT 0,
        total_storage_used_bytes BIGINT NOT NULL DEFAULT 0,
        total_storage_capacity_bytes BIGINT NOT NULL DEFAULT 0,
        total_storage_usage_percent REAL NOT NULL DEFAULT 0,
        local_storage_used_bytes BIGINT NOT NULL DEFAULT 0,
        local_storage_capacity_bytes BIGINT NOT NULL DEFAULT 0,
        local_storage_usage_percent REAL NOT NULL DEFAULT 0,
        disk_read_bytes BIGINT NOT NULL DEFAULT 0,
        disk_write_bytes BIGINT NOT NULL DEFAULT 0,
        network_sent_bytes BIGINT NOT NULL DEFAULT 0,
        network_received_bytes BIGINT NOT NULL DEFAULT 0,
        top_processes_json TEXT NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tools (
        id TEXT PRIMARY KEY,
        source_name TEXT NOT NULL,
        source_description TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        name_override TEXT,
        description_override TEXT,
        inputs_schema_json TEXT NOT NULL DEFAULT '[]',
        outputs_schema_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS connectors (
        id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        auth_type TEXT NOT NULL,
        scopes_json TEXT NOT NULL DEFAULT '[]',
        base_url TEXT,
        owner TEXT,
        docs_url TEXT,
        credential_ref TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        auth_config_json TEXT NOT NULL DEFAULT '{}',
        last_tested_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS connector_endpoint_definitions (
        endpoint_id TEXT PRIMARY KEY,
        provider_id TEXT NOT NULL REFERENCES integration_presets(id) ON DELETE CASCADE,
        endpoint_kind TEXT NOT NULL,
        service TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        label TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        http_method TEXT NOT NULL,
        endpoint_path_template TEXT NOT NULL,
        query_params_json TEXT NOT NULL DEFAULT '{}',
        required_scopes_json TEXT NOT NULL DEFAULT '[]',
        input_schema_json TEXT NOT NULL DEFAULT '[]',
        output_schema_json TEXT NOT NULL DEFAULT '[]',
        payload_template TEXT NOT NULL DEFAULT '',
        execution_json TEXT NOT NULL DEFAULT '{}',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
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
    )
    """,
    """
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_steps (
        step_id TEXT PRIMARY KEY,
        automation_id TEXT NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        step_type TEXT NOT NULL,
        name TEXT NOT NULL,
        config_json TEXT NOT NULL DEFAULT '{}',
        on_true_step_id TEXT,
        on_false_step_id TEXT,
        is_merge_target INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(automation_id, position)
    )
    """,
    """
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        language TEXT NOT NULL,
        sample_input TEXT NOT NULL DEFAULT '',
        code TEXT NOT NULL,
        validation_status TEXT NOT NULL DEFAULT 'unknown',
        validation_message TEXT,
        last_validated_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS log_db_tables (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
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
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS automations_enabled_trigger_type_next_run_at_idx
        ON automations (enabled, trigger_type, next_run_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS outgoing_scheduled_apis_enabled_next_run_at_idx
        ON outgoing_scheduled_apis (enabled, next_run_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS outgoing_continuous_apis_enabled_repeat_enabled_next_run_at_idx
        ON outgoing_continuous_apis (enabled, repeat_enabled, next_run_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS automation_runs_automation_id_started_at_idx
        ON automation_runs (automation_id, started_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS connectors_provider_status_idx
        ON connectors (provider, status)
    """,
    """
    CREATE INDEX IF NOT EXISTS runtime_resource_snapshots_captured_at_idx
        ON runtime_resource_snapshots (captured_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS runtime_resource_snapshots_queue_idx
        ON runtime_resource_snapshots (queue_pending_jobs, queue_claimed_jobs)
    """,
)

DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS log_db_columns CASCADE",
    "DROP TABLE IF EXISTS log_db_tables CASCADE",
    "DROP TABLE IF EXISTS scripts CASCADE",
    "DROP TABLE IF EXISTS automation_run_steps CASCADE",
    "DROP TABLE IF EXISTS automation_steps CASCADE",
    "DROP TABLE IF EXISTS automations CASCADE",
    "DROP TABLE IF EXISTS automation_runs CASCADE",
    "DROP TABLE IF EXISTS connector_endpoint_definitions CASCADE",
    "DROP TABLE IF EXISTS connectors CASCADE",
    "DROP TABLE IF EXISTS integration_presets CASCADE",
    "DROP TABLE IF EXISTS settings CASCADE",
    "DROP TABLE IF EXISTS tools CASCADE",
    "DROP TABLE IF EXISTS runtime_resource_snapshots CASCADE",
    "DROP TABLE IF EXISTS outgoing_delivery_history CASCADE",
    "DROP TABLE IF EXISTS webhook_api_events CASCADE",
    "DROP TABLE IF EXISTS webhook_apis CASCADE",
    "DROP TABLE IF EXISTS outgoing_continuous_apis CASCADE",
    "DROP TABLE IF EXISTS outgoing_scheduled_apis CASCADE",
    "DROP TABLE IF EXISTS inbound_api_events CASCADE",
    "DROP TABLE IF EXISTS inbound_apis CASCADE",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(DOWNGRADE_STATEMENTS)