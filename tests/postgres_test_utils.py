from __future__ import annotations

import os
import unittest
from pathlib import Path

from backend.database import connect, initialize
from backend.runtime import runtime_event_bus


TABLES_TO_TRUNCATE = (
    "automation_run_steps",
    "automation_steps",
    "automation_runs",
    "automations",
    "inbound_api_events",
    "inbound_apis",
    "outgoing_scheduled_apis",
    "outgoing_continuous_apis",
    "webhook_apis",
    "scripts",
    "tools",
    "settings",
)


def get_test_database_url() -> str:
    return (
        os.getenv("MALCOM_TEST_DATABASE_URL", "").strip()
        or os.getenv("MALCOM_DATABASE_URL", "").strip()
        or "postgresql://postgres:postgres@127.0.0.1:5432/malcom_test"
    )


def reset_database(database_url: str) -> None:
    connection = connect(database_url=database_url)
    try:
        initialize(connection)
        for table_name in TABLES_TO_TRUNCATE:
            connection.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
        connection.commit()
    finally:
        connection.close()


def setup_postgres_test_app(*, app, root_dir: Path, skip_ui_build_check: bool = True) -> str:
    database_url = get_test_database_url()
    try:
        reset_database(database_url)
    except Exception as error:
        raise unittest.SkipTest(f"PostgreSQL test database is unavailable: {error}") from error

    runtime_event_bus.clear()
    app.state.root_dir = root_dir
    app.state.db_path = "postgresql"
    app.state.database_url = database_url
    app.state.skip_ui_build_check = skip_ui_build_check
    return database_url
