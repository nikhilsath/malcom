from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect, fetch_all
from backend.main import app


class SettingsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        self.db_path = self.root_dir / "backend" / "data" / "malcom-test.db"
        manifest_dir = self.root_dir / "ui" / "scripts"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        app.state.root_dir = self.root_dir
        app.state.db_path = str(self.db_path)
        app.state.skip_ui_build_check = True
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
        self.assertEqual(body["notifications"]["channel"], "slack")
        self.assertTrue(body["security"]["dual_approval_required"])
        self.assertEqual(body["data"]["audit_retention_days"], 365)
        self.assertEqual(body["connectors"]["records"], [])
        self.assertEqual(body["connectors"]["auth_policy"]["rotation_interval_days"], 90)

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

        connection = connect(self.db_path)
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
        self.assertEqual(saved_settings["notifications"]["channel"], "slack")

    def test_patch_connectors_masks_secret_values_and_stores_protected_payload(self) -> None:
        response = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "google-calendar-primary",
                            "provider": "google_calendar",
                            "name": "Google Calendar",
                            "status": "draft",
                            "auth_type": "oauth2",
                            "scopes": ["https://www.googleapis.com/auth/calendar"],
                            "base_url": "https://www.googleapis.com/calendar/v3",
                            "owner": "Workspace",
                            "auth_config": {
                                "client_id": "calendar-client-id",
                                "client_secret_input": "calendar-client-secret",
                                "access_token_input": "calendar-access-token",
                                "redirect_uri": "http://localhost:8000/api/v1/connectors/google_calendar/oauth/callback",
                            },
                        }
                    ]
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        record = body["connectors"]["records"][0]
        self.assertEqual(record["provider"], "google_calendar")
        self.assertIsNotNone(record["auth_config"]["client_secret_masked"])
        self.assertIsNotNone(record["auth_config"]["access_token_masked"])
        self.assertNotIn("calendar-client-secret", json.dumps(body))
        self.assertNotIn("calendar-access-token", json.dumps(body))

        connection = connect(self.db_path)
        try:
            row = fetch_all(
                connection,
                """
                SELECT value_json
                FROM settings
                WHERE key = 'connectors'
                """,
            )[0]
        finally:
            connection.close()

        stored_value = row["value_json"]
        self.assertNotIn("calendar-client-secret", stored_value)
        self.assertNotIn("calendar-access-token", stored_value)

    def test_oauth_callback_rejects_invalid_state(self) -> None:
        response = self.client.get("/api/v1/connectors/google_calendar/oauth/callback?state=invalid&code=demo")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid OAuth state.")

    def test_get_settings_backfills_missing_logging_fields_from_defaults(self) -> None:
        connection = connect(self.db_path)
        try:
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, datetime('now'), datetime('now'))
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
        connection = connect(self.db_path)
        try:
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                ("general", json.dumps({"environment": "staging", "timezone": "pst"})),
            )
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                ("notifications", json.dumps({"channel": "teams", "digest": "weekly", "escalate_oncall": True})),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["general"]["timezone"], "local")
        self.assertEqual(body["notifications"]["channel"], "slack")
        self.assertEqual(body["notifications"]["digest"], "hourly")


if __name__ == "__main__":
    unittest.main()
