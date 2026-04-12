from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect, fetch_all
from backend.main import app
from backend.services.automation_execution import get_settings_payload
from backend.services.support import redact_sensitive_payload_sample
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class SettingsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(self.root_dir)
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
        self.assertEqual(body["security"]["session_timeout_minutes"], 60)
        self.assertFalse(body["security"]["dual_approval_required"])
        self.assertEqual(body["security"]["token_rotation_days"], 30)
        self.assertTrue(body["data"]["payload_redaction"])
        self.assertEqual(body["automation"]["default_tool_retries"], 2)
        self.assertEqual(body["proxy"]["domain"], "")
        self.assertEqual(body["proxy"]["http_port"], 80)
        self.assertEqual(body["proxy"]["https_port"], 443)
        self.assertFalse(body["proxy"]["enabled"])
        self.assertNotIn("connectors", body)
        self.assertEqual([item["value"] for item in body["options"]["notification_channels"]], ["email", "pager"])
        self.assertEqual([item["value"] for item in body["options"]["notification_digests"]], ["realtime", "hourly", "daily"])
        # data_export_windows option removed

    def test_get_settings_payload_excludes_connectors_section_for_startup(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            payload = get_settings_payload(connection)
        finally:
            connection.close()

        self.assertEqual(payload["general"]["environment"], "live")
        self.assertNotIn("connectors", payload)
        self.assertTrue(payload["data"]["payload_redaction"])
        self.assertEqual([item["value"] for item in payload["options"]["notification_channels"]], ["email", "pager"])

    def test_redact_sensitive_payload_sample_masks_nested_credentials(self) -> None:
        payload = {
            "event": "webhook.received",
            "authorization": "Bearer example-token",
            "headers": {
                "x-github-event": "push",
                "x-api-key": "super-secret",
            },
            "data": {
                "nested": [
                    {
                        "client_secret": "client-secret-value",
                        "notes": "safe",
                    }
                ],
                "token_count": 3,
            },
        }

        redacted = redact_sensitive_payload_sample(payload, enabled=True)
        self.assertEqual(redacted["event"], "webhook.received")
        self.assertEqual(redacted["authorization"], "[redacted]")
        self.assertEqual(redacted["headers"]["x-github-event"], "push")
        self.assertEqual(redacted["headers"]["x-api-key"], "[redacted]")
        self.assertEqual(redacted["data"]["nested"][0]["client_secret"], "[redacted]")
        self.assertEqual(redacted["data"]["nested"][0]["notes"], "safe")
        self.assertEqual(redacted["data"]["token_count"], "[redacted]")

        self.assertEqual(redact_sensitive_payload_sample(payload, enabled=False), payload)

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
                "security": {
                    "session_timeout_minutes": 120,
                    "dual_approval_required": True,
                    "token_rotation_days": 90,
                },
                "data": {
                    "payload_redaction": False,
                    "export_window_utc": "04:00",
                    "workflow_storage_path": "data/workflows",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["logging"]["max_stored_entries"], 500)
        self.assertEqual(body["logging"]["max_file_size_mb"], 8)
        self.assertEqual(body["notifications"]["digest"], "hourly")
        self.assertEqual(body["security"]["session_timeout_minutes"], 120)
        self.assertTrue(body["security"]["dual_approval_required"])
        self.assertEqual(body["security"]["token_rotation_days"], 90)
        self.assertFalse(body["data"]["payload_redaction"])

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
        self.assertEqual(saved_settings["security"]["session_timeout_minutes"], 120)
        self.assertTrue(saved_settings["security"]["dual_approval_required"])
        self.assertEqual(saved_settings["security"]["token_rotation_days"], 90)
        self.assertFalse(saved_settings["data"]["payload_redaction"])

    def test_patch_proxy_settings_persists_and_syncs(self) -> None:
        with patch("backend.routes.settings.sync_proxy_to_caddy_runtime") as mock_sync:
            response = self.client.patch(
                "/api/v1/settings",
                json={
                    "proxy": {
                        "domain": "tools.example.com",
                        "http_port": 8080,
                        "https_port": 8443,
                        "enabled": True,
                    }
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["proxy"]["domain"], "tools.example.com")
        self.assertEqual(body["proxy"]["http_port"], 8080)
        self.assertEqual(body["proxy"]["https_port"], 8443)
        self.assertTrue(body["proxy"]["enabled"])

        reloaded = self.client.get("/api/v1/settings")
        self.assertEqual(reloaded.status_code, 200)
        reloaded_body = reloaded.json()
        self.assertEqual(reloaded_body["proxy"]["domain"], "tools.example.com")
        self.assertEqual(reloaded_body["proxy"]["http_port"], 8080)
        self.assertEqual(reloaded_body["proxy"]["https_port"], 8443)
        self.assertTrue(reloaded_body["proxy"]["enabled"])

        mock_sync.assert_called_once_with(
            self.root_dir,
            {
                "domain": "tools.example.com",
                "http_port": 8080,
                "https_port": 8443,
                "enabled": True,
            },
        )

        connection = connect(database_url=self.database_url)
        try:
            row = fetch_all(
                connection,
                """
                SELECT value_json
                FROM settings
                WHERE key = 'proxy'
                """,
            )
        finally:
            connection.close()

        self.assertEqual(len(row), 1)
        saved_proxy = json.loads(row[0]["value_json"])
        self.assertEqual(saved_proxy["domain"], "tools.example.com")
        self.assertEqual(saved_proxy["http_port"], 8080)
        self.assertEqual(saved_proxy["https_port"], 8443)
        self.assertTrue(saved_proxy["enabled"])

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

    def test_backup_routes_delegate_to_service_layer_with_mocked_services(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("MALCOM_DATABASE_URL", None)
            with patch("backend.services.support.create_backup") as mock_create, patch(
                "backend.services.support.list_backups"
            ) as mock_list, patch("backend.services.support.restore_backup") as mock_restore, patch(
                "backend.services.support.get_backup_dir"
            ) as mock_backup_dir:
                mock_create.return_value = {
                    "filename": "backup-2026-04-03.dump",
                    "size_bytes": 1024,
                    "path": "/tmp/malcom-backups/backup-2026-04-03.dump",
                }
                mock_list.return_value = [
                    {
                        "filename": "backup-2026-04-03.dump",
                        "size_bytes": 1024,
                        "created_at": "2026-04-03T00:00:00+00:00",
                        "path": "/tmp/malcom-backups/backup-2026-04-03.dump",
                    }
                ]
                mock_restore.return_value = {"restored_at": "2026-04-03T00:00:00+00:00"}
                mock_backup_dir.return_value = Path("/tmp/malcom-backups")

                create_resp = self.client.post("/api/v1/settings/data/backups")
                self.assertEqual(create_resp.status_code, 200)
                create_body = create_resp.json()
                self.assertTrue(create_body.get("ok"))
                self.assertIsNotNone(create_body.get("backup"))
                self.assertEqual(create_body["backup"]["filename"], "backup-2026-04-03.dump")
                mock_create.assert_called_once_with(db_url=self.database_url)

                list_resp = self.client.get("/api/v1/settings/data/backups")
                self.assertEqual(list_resp.status_code, 200)
                list_body = list_resp.json()
                self.assertEqual(list_body["directory"], "/tmp/malcom-backups")
                self.assertIsInstance(list_body.get("backups"), list)
                self.assertEqual(list_body["backups"][0]["filename"], "backup-2026-04-03.dump")

                restore_resp = self.client.post(
                    "/api/v1/settings/data/backups/restore", json={"backup_id": "backup-2026-04-03.dump"}
                )
                self.assertEqual(restore_resp.status_code, 200)
                restore_body = restore_resp.json()
                self.assertTrue(restore_body.get("ok"))
                self.assertIsNotNone(restore_body.get("restored_at"))
                mock_restore.assert_called_once_with("backup-2026-04-03.dump", db_url=self.database_url)

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

    def test_proxy_test_endpoint_returns_service_result(self) -> None:
        payload = {
            "domain": "tools.example.com",
            "http_port": 80,
            "https_port": 443,
            "enabled": True,
        }
        with patch("backend.routes.settings.test_proxy_connection") as mock_test:
            mock_test.return_value = {
                "ok": True,
                "message": "HTTP and HTTPS endpoints are reachable.",
                "checks": [
                    {
                        "scheme": "dns",
                        "target": "tools.example.com",
                        "reachable": True,
                        "status_code": None,
                        "detail": "Resolved to 203.0.113.10",
                    },
                    {
                        "scheme": "https",
                        "target": "tools.example.com:443",
                        "reachable": True,
                        "status_code": 200,
                        "detail": None,
                    },
                ],
            }
            response = self.client.post("/api/v1/settings/proxy/test", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("reachable", body.get("message", ""))
        self.assertEqual(len(body.get("checks", [])), 2)
        mock_test.assert_called_once_with(payload)

    def test_proxy_test_endpoint_handles_runtime_error(self) -> None:
        payload = {
            "domain": "tools.example.com",
            "http_port": 80,
            "https_port": 443,
            "enabled": True,
        }
        with patch("backend.routes.settings.test_proxy_connection") as mock_test:
            mock_test.side_effect = RuntimeError("Proxy test failed")
            response = self.client.post("/api/v1/settings/proxy/test", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("message"), "Proxy test failed")
        self.assertEqual(body.get("checks"), [])


if __name__ == "__main__":
    unittest.main()
