from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class ConnectorsForBuilderExtraTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
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

    def test_returns_connectors_with_owner_field(self) -> None:
        self._create_connector(
            {
                "id": "owned-1",
                "provider": "github",
                "name": "Repo Connector",
                "status": "connected",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "owner": "workspace_42",
            }
        )

        resp = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertTrue(any(item["id"] == "owned-1" for item in items))
        owned = next(item for item in items if item["id"] == "owned-1")
        self.assertIn("owner", owned)
        self.assertEqual(owned["owner"], "workspace_42")

    def test_endpoint_returns_500_on_service_exception(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch(
                "backend.routes.automations.list_workflow_builder_connectors",
                side_effect=RuntimeError("simulated db failure"),
            ):
                resp = client.get("/api/v1/automations/workflow-connectors")
                self.assertEqual(resp.status_code, 500)


if __name__ == "__main__":
    unittest.main()
