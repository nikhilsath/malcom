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
        self.db_path = Path(self.tempdir.name) / "malcom-test.db"
        app.state.db_path = str(self.db_path)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_get_settings_returns_seeded_defaults(self) -> None:
        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "staging")
        self.assertEqual(body["logging"]["max_stored_entries"], 250)
        self.assertEqual(body["notifications"]["channel"], "slack")
        self.assertTrue(body["security"]["dual_approval_required"])
        self.assertEqual(body["data"]["audit_retention_days"], 365)

    def test_patch_settings_persists_updates_to_database(self) -> None:
        response = self.client.patch(
            "/api/v1/settings",
            json={
                "general": {
                    "environment": "production",
                    "timezone": "utc",
                    "preview_mode": False,
                },
                "logging": {
                    "max_stored_entries": 500,
                    "max_visible_entries": 100,
                    "max_detail_characters": 6000,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "production")
        self.assertFalse(body["general"]["preview_mode"])
        self.assertEqual(body["logging"]["max_stored_entries"], 500)
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
        self.assertEqual(saved_settings["general"]["environment"], "production")
        self.assertEqual(saved_settings["logging"]["max_visible_entries"], 100)
        self.assertEqual(saved_settings["notifications"]["channel"], "slack")


if __name__ == "__main__":
    unittest.main()
