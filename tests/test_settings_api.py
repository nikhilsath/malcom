from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect, fetch_all
from backend.main import app
from backend.services.automation_execution import get_settings_payload
from tests.postgres_test_utils import setup_postgres_test_app


class SettingsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        manifest_dir = self.root_dir / "ui" / "scripts"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        self.database_url = setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.skip_ui_build_check = False
        self.tempdir.cleanup()

    def test_get_settings_returns_seeded_defaults(self) -> None:
        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["logging"]["max_stored_entries"], 250)
        self.assertEqual(body["logging"]["max_file_size_mb"], 5)
        self.assertEqual(body["notifications"]["channel"], "email")
        self.assertEqual(body["automation"]["default_tool_retries"], 2)
        self.assertNotIn("connectors", body)
        self.assertEqual([item["value"] for item in body["options"]["notification_channels"]], ["email", "pager"])
        self.assertEqual([item["value"] for item in body["options"]["notification_digests"]], ["realtime", "hourly", "daily"])
        self.assertEqual([item["value"] for item in body["options"]["data_export_windows"]], ["00:00", "02:00", "04:00"])

    def test_get_settings_payload_excludes_connectors_section_for_startup(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            payload = get_settings_payload(connection)
        finally:
            connection.close()

        self.assertEqual(payload["general"]["environment"], "live")
        self.assertNotIn("connectors", payload)
        self.assertEqual([item["value"] for item in payload["options"]["notification_channels"]], ["email", "pager"])

    def test_get_settings_ignores_legacy_connectors_settings_row(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    "connectors",
                    json.dumps({"records": [{"id": "legacy", "provider": "google"}]}),
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("connectors", response.json())

    def test_patch_settings_persists_updates_to_database(self) -> None:
        response = self.client.patch(
            "/api/v1/settings",
            json={
                "general": {
                    "environment": "live",
                    "timezone": "utc",
                },
                "logging": {
                    "max_stored_entries": 500,
                    "max_visible_entries": 100,
                    "max_detail_characters": 6000,
                    "max_file_size_mb": 8,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["logging"]["max_stored_entries"], 500)
        self.assertEqual(body["logging"]["max_file_size_mb"], 8)
        self.assertEqual(body["notifications"]["digest"], "hourly")

        connection = connect(database_url=self.database_url)
        try:
            rows = fetch_all(
                connection,
                """
                SELECT key, value_json
                FROM settings
                ORDER BY key
                """,
            )
        finally:
            connection.close()

        saved_settings = {row["key"]: json.loads(row["value_json"]) for row in rows}
        self.assertEqual(saved_settings["general"]["environment"], "live")
        self.assertEqual(saved_settings["logging"]["max_visible_entries"], 100)
        self.assertEqual(saved_settings["logging"]["max_file_size_mb"], 8)
        self.assertEqual(saved_settings["notifications"]["channel"], "email")

    def test_get_settings_backfills_missing_logging_fields_from_defaults(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    "logging",
                    json.dumps(
                        {
                            "max_stored_entries": 300,
                            "max_visible_entries": 75,
                            "max_detail_characters": 5000,
                        }
                    ),
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["logging"]["max_stored_entries"], 300)
        self.assertEqual(body["logging"]["max_visible_entries"], 75)
        self.assertEqual(body["logging"]["max_detail_characters"], 5000)
        self.assertEqual(body["logging"]["max_file_size_mb"], 5)

    def test_get_settings_falls_back_to_defaults_for_invalid_legacy_values(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                ("general", json.dumps({"environment": "staging", "timezone": "pst"}), now_value, now_value),
            )
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    "notifications",
                    json.dumps({"channel": "teams", "digest": "weekly", "escalate_oncall": True}),
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["general"]["timezone"], "local")
        self.assertEqual(body["notifications"]["channel"], "email")
        self.assertEqual(body["notifications"]["digest"], "hourly")

    def test_create_list_and_restore_backups_with_mocked_services(self) -> None:
        with patch("backend.services.support.create_backup") as mock_create, patch(
            "backend.services.support.list_backups"
        ) as mock_list, patch("backend.services.support.restore_backup") as mock_restore, patch(
            "backend.services.support.get_backup_dir"
        ) as mock_backup_dir:
            mock_create.return_value = {"filename": "backup-2026-04-03.sql", "size_bytes": 1024}
            mock_list.return_value = [
                {"filename": "backup-2026-04-03.sql", "size_bytes": 1024, "created_at": "2026-04-03T00:00:00+00:00"}
            ]
            mock_restore.return_value = {"restored_at": "2026-04-03T00:00:00+00:00"}
            mock_backup_dir.return_value = Path("/tmp/malcom-backups")

            create_resp = self.client.post("/api/v1/settings/data/backups")
            self.assertEqual(create_resp.status_code, 200)
            create_body = create_resp.json()
            self.assertTrue(create_body.get("ok"))
            self.assertIsNotNone(create_body.get("backup"))
            self.assertEqual(create_body["backup"]["filename"], "backup-2026-04-03.sql")

            list_resp = self.client.get("/api/v1/settings/data/backups")
            self.assertEqual(list_resp.status_code, 200)
            list_body = list_resp.json()
            self.assertEqual(list_body["directory"], "/tmp/malcom-backups")
            self.assertIsInstance(list_body.get("backups"), list)
            self.assertEqual(list_body["backups"][0]["filename"], "backup-2026-04-03.sql")

            restore_resp = self.client.post(
                "/api/v1/settings/data/backups/restore", json={"backup_id": "backup-2026-04-03.sql"}
            )
            self.assertEqual(restore_resp.status_code, 200)
            restore_body = restore_resp.json()
            self.assertTrue(restore_body.get("ok"))
            self.assertIsNotNone(restore_body.get("restored_at"))

    def test_backup_service_errors_propagate_gracefully(self) -> None:
        with patch("backend.services.support.create_backup") as mock_create:
            mock_create.side_effect = RuntimeError("pg_dump not available")
            resp = self.client.post("/api/v1/settings/data/backups")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertFalse(body.get("ok"))
            self.assertIn("pg_dump not available", body.get("message", ""))

        with patch("backend.services.support.restore_backup") as mock_restore:
            mock_restore.side_effect = RuntimeError("pg_restore failed")
            resp = self.client.post(
                "/api/v1/settings/data/backups/restore", json={"backup_id": "missing.sql"}
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertFalse(body.get("ok"))
            self.assertIn("pg_restore failed", body.get("message", ""))


if __name__ == "__main__":
    unittest.main()
