from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect
from backend.main import app
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, get_test_database_url, setup_postgres_test_app


class ConnectorsForBuilderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(self.root_dir)
        self.previous_root_dir = app.state.root_dir
        self.previous_db_path = app.state.db_path
        self.previous_database_url = app.state.database_url
        self.previous_skip_ui_build_check = getattr(app.state, "skip_ui_build_check", False)
        setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.root_dir = self.previous_root_dir
        app.state.db_path = self.previous_db_path
        app.state.database_url = self.previous_database_url
        app.state.skip_ui_build_check = self.previous_skip_ui_build_check
        self.tempdir.cleanup()

    def _create_connector(self, payload: dict) -> None:
        response = self.client.post("/api/v1/connectors", json=payload)
        self.assertEqual(response.status_code, 201, response.text)

    def test_get_connectors_returns_empty_list_when_none(self) -> None:
        resp = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_filters_inactive_status_and_normalizes_fields(self) -> None:
        self._create_connector(
            {
                "id": "active-1",
                "provider": "google",
                "name": "Active One",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["gmail.send"],
                "owner": "workspace_1",
            }
        )
        self._create_connector(
            {
                "id": "revoked-1",
                "provider": "google",
                "name": "Revoked One",
                "status": "revoked",
                "auth_type": "oauth2",
                "scopes": ["gmail.read"],
                "owner": "workspace_1",
            }
        )

        resp = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        # Only active connector should be present
        self.assertTrue(any(item["id"] == "active-1" for item in items))
        self.assertFalse(any(item["id"] == "revoked-1" for item in items))
        active = next(item for item in items if item["id"] == "active-1")
        self.assertIn("provider", active)
        self.assertIn("scopes", active)
        self.assertIsInstance(active["scopes"], list)

    def test_returns_empty_list_when_all_inactive(self) -> None:
        self._create_connector(
            {
                "id": "only-draft",
                "provider": "github",
                "status": "draft",
                "name": "Draft",
                "auth_type": "bearer",
                "scopes": [],
            }
        )

        resp = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_prefers_connectors_table_over_legacy_settings_payload(self) -> None:
        connection = connect(database_url=get_test_database_url())
        try:
            connection.execute(
                """
                INSERT INTO connectors (id, provider, name, status, auth_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "table-connector",
                    "google",
                    "Table Connector",
                    "connected",
                    "oauth2",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "connectors",
                    '{"records":[{"id":"settings-connector","provider":"github","name":"Settings Connector","status":"connected","auth_type":"oauth2"}]}',
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ),
            )
            connection.commit()

            response = self.client.get("/api/v1/automations/workflow-connectors")
            self.assertEqual(response.status_code, 200)
            ids = [item["id"] for item in response.json()]
            self.assertIn("table-connector", ids)
            self.assertNotIn("settings-connector", ids)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
