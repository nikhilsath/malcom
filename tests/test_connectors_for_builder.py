from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class ConnectorsForBuilderTestCase(unittest.TestCase):
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

    def test_get_connectors_returns_empty_list_when_none(self) -> None:
        # Ensure connector records are cleared because connectors persist outside settings reset.
        settings_resp = self.client.patch(
            "/api/v1/settings",
            json={"connectors": {"records": []}},
        )
        self.assertEqual(settings_resp.status_code, 200)

        resp = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_filters_inactive_status_and_normalizes_fields(self) -> None:
        # Add two connectors via settings: one active, one revoked
        settings_resp = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "active-1",
                            "provider": "google",
                            "name": "Active One",
                            "status": "connected",
                            "auth_type": "oauth2",
                            "scopes": ["gmail.send"],
                            "owner": "workspace_1",
                        },
                        {
                            "id": "revoked-1",
                            "provider": "google",
                            "name": "Revoked One",
                            "status": "revoked",
                            "auth_type": "oauth2",
                            "scopes": ["gmail.read"],
                            "owner": "workspace_1",
                        },
                    ]
                }
            },
        )
        self.assertEqual(settings_resp.status_code, 200)

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
        settings_resp = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "only-draft",
                            "provider": "github",
                            "status": "draft",
                            "name": "Draft",
                            "auth_type": "oauth2",
                            "scopes": [],
                        }
                    ]
                }
            },
        )
        self.assertEqual(settings_resp.status_code, 200)

        resp = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


if __name__ == "__main__":
    unittest.main()
