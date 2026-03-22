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
            "/api/v1/connectors/google/oauth/start",
            json={
                "connector_id": "google-primary",
                "name": "Google",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                "owner": "Workspace",
                "client_id": "google-client-id",
                "client_secret_input": "google-client-secret",
            },
        )
        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()
        self.assertEqual(start_body["connector"]["status"], "pending_oauth")
        self.assertIn("accounts.google.com", start_body["authorization_url"])

        callback_response = self.client.get(
            f"/api/v1/connectors/google/oauth/callback?state={start_body['state']}&code=demo"
        )
        self.assertEqual(callback_response.status_code, 200)
        callback_body = callback_response.json()
        self.assertTrue(callback_body["ok"])
        self.assertEqual(callback_body["connector"]["status"], "connected")
        self.assertTrue(callback_body["connector"]["auth_config"]["has_refresh_token"])

        refresh_response = self.client.post("/api/v1/connectors/google-primary/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        refresh_body = refresh_response.json()
        self.assertTrue(refresh_body["ok"])
        self.assertEqual(refresh_body["connector"]["status"], "connected")
        self.assertIsNotNone(refresh_body["connector"]["last_tested_at"])

    def test_google_oauth_start_supports_custom_scopes(self) -> None:
        start_response = self.client.post(
            "/api/v1/connectors/google/oauth/start",
            json={
                "connector_id": "google-workspace-primary",
                "name": "Google Workspace",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                "owner": "Workspace",
                "client_id": "google-client-id",
                "client_secret_input": "google-client-secret",
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/calendar",
                ],
            },
        )

        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()
        self.assertEqual(start_body["connector"]["status"], "pending_oauth")
        self.assertEqual(start_body["connector"]["base_url"], "https://www.googleapis.com")
        self.assertEqual(
            start_body["connector"]["scopes"],
            [
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/calendar",
            ],
        )
        self.assertIn("accounts.google.com", start_body["authorization_url"])

        callback_response = self.client.get(
            f"/api/v1/connectors/google/oauth/callback?state={start_body['state']}&code=demo"
        )
        self.assertEqual(callback_response.status_code, 200)
        callback_body = callback_response.json()
        self.assertTrue(callback_body["ok"])
        self.assertEqual(callback_body["connector"]["status"], "connected")
        self.assertTrue(callback_body["connector"]["auth_config"]["has_refresh_token"])

        refresh_response = self.client.post("/api/v1/connectors/google-workspace-primary/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        refresh_body = refresh_response.json()
        self.assertTrue(refresh_body["ok"])
        self.assertEqual(refresh_body["connector"]["status"], "connected")

    def test_google_oauth_start_requires_client_id(self) -> None:
        response = self.client.post(
            "/api/v1/connectors/google/oauth/start",
            json={
                "connector_id": "google-missing-client",
                "name": "Google Missing Client",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                "owner": "Workspace",
                "client_id": "",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Google OAuth requires a client_id.")

    def test_legacy_google_provider_aliases_resolve_to_unified_google(self) -> None:
        start_response = self.client.post(
            "/api/v1/connectors/google_calendar/oauth/start",
            json={
                "connector_id": "legacy-google-primary",
                "name": "Legacy Google Calendar",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/google_calendar/oauth/callback",
                "owner": "Workspace",
                "client_id": "legacy-google-client-id",
                "client_secret_input": "legacy-google-client-secret",
            },
        )

        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()
        self.assertEqual(start_body["connector"]["provider"], "google")


if __name__ == "__main__":
    unittest.main()
