from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class ConnectorsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        setup_postgres_test_app(app=app, root_dir=root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_tests_connector_credentials_after_settings_patch(self) -> None:
        patch_response = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "github-primary",
                            "provider": "github",
                            "name": "GitHub",
                            "status": "draft",
                            "auth_type": "bearer",
                            "scopes": ["repo"],
                            "base_url": "https://api.github.com",
                            "owner": "Workspace",
                            "auth_config": {
                                "access_token_input": "ghp_secret_token",
                            },
                        }
                    ]
                }
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        response = self.client.post("/api/v1/connectors/github-primary/test")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["connector"]["status"], "connected")
        self.assertIsNotNone(body["connector"]["last_tested_at"])

    def test_oauth_start_callback_and_refresh_flow(self) -> None:
        start_response = self.client.post(
            "/api/v1/connectors/google_calendar/oauth/start",
            json={
                "connector_id": "google-calendar-primary",
                "name": "Google Calendar",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/google_calendar/oauth/callback",
                "owner": "Workspace",
                "client_id": "calendar-client-id",
                "client_secret_input": "calendar-client-secret",
            },
        )
        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()
        self.assertEqual(start_body["connector"]["status"], "pending_oauth")
        self.assertIn("accounts.google.com", start_body["authorization_url"])

        callback_response = self.client.get(
            f"/api/v1/connectors/google_calendar/oauth/callback?state={start_body['state']}&code=demo"
        )
        self.assertEqual(callback_response.status_code, 200)
        callback_body = callback_response.json()
        self.assertTrue(callback_body["ok"])
        self.assertEqual(callback_body["connector"]["status"], "connected")
        self.assertTrue(callback_body["connector"]["auth_config"]["has_refresh_token"])

        refresh_response = self.client.post("/api/v1/connectors/google-calendar-primary/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        refresh_body = refresh_response.json()
        self.assertTrue(refresh_body["ok"])
        self.assertEqual(refresh_body["connector"]["status"], "connected")
        self.assertIsNotNone(refresh_body["connector"]["last_tested_at"])


if __name__ == "__main__":
    unittest.main()
