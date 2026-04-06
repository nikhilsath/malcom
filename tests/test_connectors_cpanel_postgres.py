from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class CPanelPostgresConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = __import__("tempfile").TemporaryDirectory()
        root_dir = __import__("pathlib").Path(self.tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        setup_postgres_test_app(app=app, root_dir=root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def _create_connector_payload(self, connector_id: str) -> dict:
        return {
            "id": connector_id,
            "provider": "cpanel_postgres",
            "name": "cPanel PG",
            "status": "draft",
            "auth_type": "basic",
            "owner": "Workspace",
            "auth_config": {
                "host": "db.example.com",
                "port": "5432",
                "database": "demo_db",
                "username": "demo_user",
                "password_input": "secret-pass",
            },
        }

    def test_test_endpoint_success_reports_connected(self) -> None:
        payload = self._create_connector_payload("cpanel-pg-1")

        with patch("backend.services.connector_postgres.probe_postgres_connection", return_value=(True, "PostgreSQL connection verified.")):
            create_resp = self.client.post("/api/v1/connectors", json=payload)
            self.assertEqual(create_resp.status_code, 201)

            resp = self.client.post("/api/v1/connectors/cpanel-pg-1/test")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertTrue(body.get("ok"))
            self.assertEqual(body.get("message"), "PostgreSQL connection verified.")
            self.assertEqual(body.get("connector", {}).get("status"), "connected")

    def test_test_endpoint_failure_reports_needs_attention(self) -> None:
        payload = self._create_connector_payload("cpanel-pg-2")

        with patch("backend.services.connector_postgres.probe_postgres_connection", return_value=(False, "PostgreSQL rejected the saved credentials.")):
            create_resp = self.client.post("/api/v1/connectors", json=payload)
            self.assertEqual(create_resp.status_code, 201)

            resp = self.client.post("/api/v1/connectors/cpanel-pg-2/test")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertFalse(body.get("ok"))
            self.assertEqual(body.get("message"), "PostgreSQL rejected the saved credentials.")
            self.assertEqual(body.get("connector", {}).get("status"), "needs_attention")


if __name__ == "__main__":
    unittest.main()
