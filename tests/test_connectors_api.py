from __future__ import annotations

import tempfile
import unittest
import urllib.error
from pathlib import Path
from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.connectors import _probe_google_access_token
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

    def test_connector_crud_and_auth_policy_routes(self) -> None:
        create_response = self.client.post(
            "/api/v1/connectors",
            json={
                "id": "github-primary",
                "provider": "github",
                "name": "GitHub",
                "status": "draft",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {
                    "access_token_input": "token_secret_test_value",
                },
            },
        )
        self.assertEqual(create_response.status_code, 201)

        patch_response = self.client.patch(
            "/api/v1/connectors/github-primary",
            json={
                "name": "GitHub Updated",
                "status": "connected",
            },
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["name"], "GitHub Updated")
        self.assertEqual(patch_response.json()["status"], "connected")

        policy_response = self.client.patch(
            "/api/v1/connectors/auth-policy",
            json={
                "auth_policy": {
                    "rotation_interval_days": 60,
                    "reconnect_requires_approval": True,
                    "credential_visibility": "admin_only",
                }
            },
        )
        self.assertEqual(policy_response.status_code, 200)
        self.assertEqual(policy_response.json()["auth_policy"]["rotation_interval_days"], 60)

        delete_response = self.client.delete("/api/v1/connectors/github-primary")
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["ok"])

    def test_tests_connector_credentials_after_direct_create(self) -> None:
        create_response = self.client.post(
            "/api/v1/connectors",
            json={
                "id": "github-primary",
                "provider": "github",
                "name": "GitHub",
                "status": "draft",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {
                    "access_token_input": "token_secret_test_value",
                },
            },
        )
        self.assertEqual(create_response.status_code, 201)

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

        test_response = self.client.post("/api/v1/connectors/google-primary/test")
        self.assertEqual(test_response.status_code, 200)
        test_body = test_response.json()
        self.assertTrue(test_body["ok"])
        self.assertEqual(test_body["message"], "Google connection verified.")
        self.assertEqual(test_body["connector"]["status"], "connected")

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

        test_response = self.client.post("/api/v1/connectors/google-workspace-primary/test")
        self.assertEqual(test_response.status_code, 200)
        self.assertTrue(test_response.json()["ok"])

        refresh_response = self.client.post("/api/v1/connectors/google-workspace-primary/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        refresh_body = refresh_response.json()
        self.assertTrue(refresh_body["ok"])
        self.assertEqual(refresh_body["connector"]["status"], "connected")

    def test_google_probe_returns_actionable_invalid_token_message(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/tokeninfo?access_token=demo",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":"invalid_token"}'),
        )

        with patch("backend.routes.connectors.urllib.request.urlopen", side_effect=http_error):
            ok, message = _probe_google_access_token(access_token="demo-access-token")

        self.assertFalse(ok)
        self.assertEqual(
            message,
            "Google rejected the saved access token as invalid or revoked. Reconnect Google and try again.",
        )

    def test_google_oauth_start_requires_client_id(self) -> None:
        with patch.dict("os.environ", {"MALCOM_GOOGLE_OAUTH_CLIENT_ID": ""}, clear=False):
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
        self.assertEqual(
            response.json()["detail"],
            "Google OAuth client_id is required. Configure connector client_id, or set MALCOM_GOOGLE_OAUTH_CLIENT_ID.",
        )

    def test_google_oauth_start_uses_environment_client_id(self) -> None:
        with patch.dict("os.environ", {"MALCOM_GOOGLE_OAUTH_CLIENT_ID": "google-env-client-id"}, clear=False):
            response = self.client.post(
                "/api/v1/connectors/google/oauth/start",
                json={
                    "connector_id": "google-env-client",
                    "name": "Google Env Client",
                    "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                    "owner": "Workspace",
                    "client_id": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["connector"]["auth_config"]["client_id"], "google-env-client-id")
        self.assertIn("client_id=google-env-client-id", body["authorization_url"])

    def test_google_oauth_ui_callback_redirects_to_connectors_page(self) -> None:
        start_response = self.client.post(
            "/api/v1/connectors/google/oauth/start",
            json={
                "connector_id": "google-ui-callback",
                "name": "Google UI Callback",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                "owner": "Workspace",
                "client_id": "google-client-id",
                "client_secret_input": "google-client-secret",
            },
        )
        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()

        callback_response = self.client.get(
            f"/api/v1/connectors/google/oauth/callback?state={start_body['state']}&code=demo",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )

        self.assertEqual(callback_response.status_code, 303)
        location = callback_response.headers.get("location", "")
        self.assertTrue(location.startswith("/settings/connectors.html?"))
        self.assertIn("oauth_status=success", location)
        self.assertIn("connector_id=google-ui-callback", location)

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

    def test_connector_metadata_exposes_first_party_provider_onboarding_contracts(self) -> None:
        response = self.client.get("/api/v1/connectors")
        self.assertEqual(response.status_code, 200)
        metadata = response.json()["metadata"]["providers"]
        providers = {item["id"]: item for item in metadata}

        self.assertEqual(set(providers), {"google", "github", "notion", "trello"})
        self.assertTrue(providers["github"]["oauth_supported"])
        self.assertTrue(providers["notion"]["oauth_supported"])
        self.assertFalse(providers["trello"]["oauth_supported"])
        self.assertEqual(providers["github"]["default_redirect_path"], "/api/v1/connectors/github/oauth/callback")
        self.assertIn("client_secret", providers["github"]["required_fields"])
        self.assertIn("api_key", providers["trello"]["required_fields"])

    def test_github_oauth_start_callback_refresh_and_revoke_flow(self) -> None:
        start_response = self.client.post(
            "/api/v1/connectors/github/oauth/start",
            json={
                "connector_id": "github-primary",
                "name": "GitHub Primary",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/github/oauth/callback",
                "owner": "Workspace",
                "client_id": "github-client-id",
                "client_secret_input": "github-client-secret",
                "scopes": ["repo", "read:user"],
            },
        )
        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()
        self.assertEqual(start_body["connector"]["status"], "pending_oauth")
        self.assertIn("github.com/login/oauth/authorize", start_body["authorization_url"])

        callback_response = self.client.get(
            f"/api/v1/connectors/github/oauth/callback?state={start_body['state']}&code=demo-github"
        )
        self.assertEqual(callback_response.status_code, 200)
        callback_body = callback_response.json()
        self.assertTrue(callback_body["ok"])
        self.assertEqual(callback_body["message"], "GitHub connector authorized successfully.")
        self.assertEqual(callback_body["connector"]["status"], "connected")
        self.assertTrue(callback_body["connector"]["auth_config"]["has_refresh_token"])

        test_response = self.client.post("/api/v1/connectors/github-primary/test")
        self.assertEqual(test_response.status_code, 200)
        self.assertTrue(test_response.json()["ok"])
        self.assertEqual(test_response.json()["message"], "GitHub connection verified.")

        refresh_response = self.client.post("/api/v1/connectors/github-primary/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        self.assertTrue(refresh_response.json()["ok"])
        self.assertEqual(refresh_response.json()["message"], "GitHub token refreshed.")

        revoke_response = self.client.post("/api/v1/connectors/github-primary/revoke")
        self.assertEqual(revoke_response.status_code, 200)
        self.assertTrue(revoke_response.json()["ok"])
        self.assertEqual(revoke_response.json()["message"], "GitHub connector revoked and credentials cleared.")
        self.assertEqual(revoke_response.json()["connector"]["status"], "revoked")

    def test_github_oauth_start_requires_client_secret(self) -> None:
        response = self.client.post(
            "/api/v1/connectors/github/oauth/start",
            json={
                "connector_id": "github-missing-secret",
                "name": "GitHub Missing Secret",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/github/oauth/callback",
                "owner": "Workspace",
                "client_id": "github-client-id",
                "client_secret_input": "",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "GitHub OAuth client_secret is required.")

    def test_notion_oauth_start_callback_and_refresh_flow(self) -> None:
        start_response = self.client.post(
            "/api/v1/connectors/notion/oauth/start",
            json={
                "connector_id": "notion-primary",
                "name": "Notion Primary",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/notion/oauth/callback",
                "owner": "Workspace",
                "client_id": "notion-client-id",
                "client_secret_input": "notion-client-secret",
            },
        )
        self.assertEqual(start_response.status_code, 200)
        start_body = start_response.json()
        self.assertEqual(start_body["connector"]["status"], "pending_oauth")
        self.assertIn("api.notion.com/v1/oauth/authorize", start_body["authorization_url"])

        callback_response = self.client.get(
            f"/api/v1/connectors/notion/oauth/callback?state={start_body['state']}&code=demo-notion"
        )
        self.assertEqual(callback_response.status_code, 200)
        callback_body = callback_response.json()
        self.assertTrue(callback_body["ok"])
        self.assertEqual(callback_body["message"], "Notion connector authorized successfully.")
        self.assertEqual(callback_body["connector"]["status"], "connected")
        self.assertTrue(callback_body["connector"]["auth_config"]["has_refresh_token"])

        test_response = self.client.post("/api/v1/connectors/notion-primary/test")
        self.assertEqual(test_response.status_code, 200)
        self.assertTrue(test_response.json()["ok"])
        self.assertEqual(test_response.json()["message"], "Notion connection verified.")

        refresh_response = self.client.post("/api/v1/connectors/notion-primary/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        self.assertTrue(refresh_response.json()["ok"])
        self.assertEqual(refresh_response.json()["message"], "Notion token refreshed.")

    def test_trello_oauth_start_returns_provider_conflict(self) -> None:
        response = self.client.post(
            "/api/v1/connectors/trello/oauth/start",
            json={
                "connector_id": "trello-primary",
                "name": "Trello Primary",
                "redirect_uri": "http://localhost:8000/api/v1/connectors/trello/oauth/callback",
                "owner": "Workspace",
                "client_id": "",
                "client_secret_input": "",
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Trello uses saved credentials and does not support OAuth browser setup.",
        )

    def test_trello_credentials_test_and_revoke_flow(self) -> None:
        create_response = self.client.post(
            "/api/v1/connectors",
            json={
                "id": "trello-primary",
                "provider": "trello",
                "name": "Trello Primary",
                "status": "draft",
                "auth_type": "api_key",
                "scopes": [],
                "base_url": "https://api.trello.com/1",
                "owner": "Workspace",
                "auth_config": {
                    "api_key_input": "trello_key_demo",
                    "access_token_input": "trello_token_demo",
                },
            },
        )
        self.assertEqual(create_response.status_code, 201)

        test_response = self.client.post("/api/v1/connectors/trello-primary/test")
        self.assertEqual(test_response.status_code, 200)
        test_body = test_response.json()
        self.assertTrue(test_body["ok"])
        self.assertEqual(test_body["message"], "Trello connection verified.")
        self.assertEqual(test_body["connector"]["status"], "connected")

        refresh_response = self.client.post("/api/v1/connectors/trello-primary/refresh")
        self.assertEqual(refresh_response.status_code, 409)
        self.assertEqual(refresh_response.json()["detail"], "Trello does not support token refresh.")

        revoke_response = self.client.post("/api/v1/connectors/trello-primary/revoke")
        self.assertEqual(revoke_response.status_code, 200)
        revoke_body = revoke_response.json()
        self.assertTrue(revoke_body["ok"])
        self.assertEqual(revoke_body["message"], "Trello credentials cleared from this workspace.")
        self.assertEqual(revoke_body["connector"]["status"], "revoked")


if __name__ == "__main__":
    unittest.main()
