from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend.database import connect, fetch_one
from backend.main import app
from backend.services import automation_execution
from tests.postgres_test_utils import setup_postgres_test_app


class StartupLifecycleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        self.previous_root_dir = app.state.root_dir
        self.previous_db_path = app.state.db_path
        self.previous_database_url = app.state.database_url
        self.previous_skip_ui_build_check = getattr(app.state, "skip_ui_build_check", False)
        self.database_url = setup_postgres_test_app(app=app, root_dir=self.root_dir)

    def tearDown(self) -> None:
        app.state.root_dir = self.previous_root_dir
        app.state.db_path = self.previous_db_path
        app.state.database_url = self.previous_database_url
        app.state.skip_ui_build_check = self.previous_skip_ui_build_check
        self.tempdir.cleanup()

    def test_lifespan_runs_startup_bootstrap_and_shutdown_cleanup(self) -> None:
        with (
            mock.patch(
                "backend.services.automation_execution.run_migrations",
                wraps=automation_execution.run_migrations,
            ) as run_migrations_mock,
            mock.patch("backend.services.automation_execution.runtime_scheduler.start") as scheduler_start_mock,
            mock.patch("backend.services.automation_execution.runtime_scheduler.stop") as scheduler_stop_mock,
            mock.patch("backend.services.automation_execution.sync_smtp_tool_runtime") as sync_smtp_runtime_mock,
            mock.patch("backend.services.automation_execution.threading.Thread") as thread_cls_mock,
        ):
            worker_thread = mock.Mock()
            thread_cls_mock.return_value = worker_thread

            with TestClient(app) as client:
                response = client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(hasattr(app.state, "connection"))
                self.assertTrue(hasattr(app.state, "smtp_manager"))

                settings_response = client.get("/api/v1/settings")
                self.assertEqual(settings_response.status_code, 200)
                self.assertNotIn("connectors", settings_response.json())

            run_migrations_mock.assert_called_once_with(database_url=self.database_url)
            scheduler_start_mock.assert_called_once()
            scheduler_stop_mock.assert_called_once()
            sync_smtp_runtime_mock.assert_called_once()
            thread_cls_mock.assert_called_once()
            worker_thread.start.assert_called_once()
            worker_thread.join.assert_called_once_with(timeout=2.0)

        connection = connect(database_url=self.database_url)
        try:
            general_row = fetch_one(
                connection,
                "SELECT key FROM settings WHERE key = ?",
                ("general",),
            )
            presets_count = fetch_one(
                connection,
                "SELECT COUNT(*) AS total FROM integration_presets",
            )
            endpoint_defs_count = fetch_one(
                connection,
                "SELECT COUNT(*) AS total FROM connector_endpoint_definitions",
            )
        finally:
            connection.close()

        self.assertIsNotNone(general_row)
        self.assertGreater(int(presets_count["total"]), 0)
        self.assertGreater(int(endpoint_defs_count["total"]), 0)

    def test_lifespan_fails_fast_when_migrations_fail(self) -> None:
        with mock.patch(
            "backend.services.automation_execution.run_migrations",
            side_effect=RuntimeError("migration bootstrap failed"),
        ):
            with self.assertRaises(RuntimeError) as error:
                with TestClient(app):
                    pass

        self.assertIn("migration bootstrap failed", str(error.exception))

    def test_run_migrations_preserves_existing_uvicorn_loggers(self) -> None:
        uvicorn_logger = logging.getLogger("uvicorn.error")
        previous_disabled = uvicorn_logger.disabled
        uvicorn_logger.disabled = False

        try:
            automation_execution.run_migrations(database_url=self.database_url)
            self.assertFalse(uvicorn_logger.disabled)
        finally:
            uvicorn_logger.disabled = previous_disabled


if __name__ == "__main__":
    unittest.main()
