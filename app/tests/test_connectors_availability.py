from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.database import connect
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, get_test_database_url, setup_postgres_test_app


class ConnectorsAvailabilityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(root_dir)
        setup_postgres_test_app(app=app, root_dir=root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_connectors_endpoint_structure(self) -> None:
        """GET /api/v1/connectors should return a connectors payload with records and catalog."""
        response = self.client.get("/api/v1/connectors")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        # Expect top-level connectors payload shape used by the UI
        self.assertIsInstance(body, dict)
        self.assertIn("records", body)
        self.assertIn("catalog", body)
        self.assertIsInstance(body["records"], list)
        self.assertIsInstance(body["catalog"], list)

    def test_connectors_endpoint_prefers_connectors_table(self) -> None:
        """Ensure GET /api/v1/connectors returns connectors from the connectors table and not from settings."""
        # Insert a connector record directly into the connectors table
        database_url = get_test_database_url()
        connection = connect(database_url=database_url)
        try:
            connection.execute(
                "INSERT INTO connectors (id, provider, name, status, auth_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("test-conn-1", "google", "Test Connector", "connected", "oauth2", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
            # Also insert a settings-backed connectors payload that should be ignored by the connectors endpoint
            connection.execute(
                "INSERT INTO settings (key, value_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (
                    "connectors",
                    '[{"id":"settings-connector","name":"Settings Connector"}]',
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ),
            )
            connection.commit()

            response = self.client.get("/api/v1/connectors")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            ids = [r.get("id") for r in body.get("records", [])]
            self.assertIn("test-conn-1", ids)
            self.assertNotIn("settings-connector", ids)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
