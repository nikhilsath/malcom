from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.connector_activities import execute_connector_activity
from tests.postgres_test_utils import setup_postgres_test_app


class ConnectorActivitiesApiTestCase(unittest.TestCase):
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

    def save_connector(self, record: dict) -> None:
        response = self.client.post("/api/v1/connectors", json=record)
        self.assertEqual(response.status_code, 201, response.text)

    def test_activity_catalog_exposes_google_and_github_provider_actions(self) -> None:
        response = self.client.get("/api/v1/connectors/activity-catalog")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        activity_ids = {(item["provider_id"], item["activity_id"]) for item in body}
        self.assertIn(("google", "gmail_list_messages"), activity_ids)
        self.assertIn(("google", "calendar_upcoming_events"), activity_ids)
        self.assertIn(("github", "list_open_pull_requests"), activity_ids)
        self.assertIn(("github", "repo_details"), activity_ids)

    def test_builder_validation_rejects_missing_scopes_for_connector_activity(self) -> None:
        self.save_connector(
            {
                "id": "google-primary",
                "provider": "google",
                "name": "Google",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )

        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Unread email automation",
                "description": "Check unread emails.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "connector_activity",
                        "name": "Unread mail",
                        "config": {
                            "connector_id": "google-primary",
                            "activity_id": "gmail_send_email",
                            "activity_inputs": {},
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("missing required scopes", response.json()["detail"])

    def test_execute_automation_runs_connector_activity_step(self) -> None:
        self.save_connector(
            {
                "id": "github-primary",
                "provider": "github",
                "name": "GitHub",
                "status": "connected",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "ghp_secret_token"},
            }
        )

        create_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Repo details automation",
                "description": "Fetch repo details.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "connector_activity",
                        "name": "Repo details",
                        "config": {
                            "connector_id": "github-primary",
                            "activity_id": "repo_details",
                            "activity_inputs": {"owner": "openai", "repo": "malcom"},
                        },
                    }
                ],
            },
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)
        automation_id = create_response.json()["id"]

        with patch(
            "backend.services.helpers.execute_connector_activity",
            return_value={
                "provider": "github",
                "activity": "repo_details",
                "repository": "openai/malcom",
                "default_branch": "main",
                "visibility": "private",
                "open_issues_count": 2,
                "stars": 5,
            },
        ) as execute_mock:
            execute_response = self.client.post(f"/api/v1/automations/{automation_id}/execute")

        self.assertEqual(execute_response.status_code, 200, execute_response.text)
        body = execute_response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["steps"][0]["status"], "completed")
        self.assertEqual(body["steps"][0]["detail_json"]["activity_output"]["repository"], "openai/malcom")
        execute_mock.assert_called_once()

    def test_google_gmail_list_activity_executes_and_normalizes_output(self) -> None:
        self.save_connector(
            {
                "id": "google-primary",
                "provider": "google",
                "name": "Google",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )
        connection = app.state.connection

        output = execute_connector_activity(
            connection,
            connector_id="google-primary",
            activity_id="gmail_list_messages",
            inputs={"max_results": 2},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: (200, {"messages": [{"id": "m1"}, {"id": "m2"}], "nextPageToken": "next"}),
        )

        self.assertEqual(output["provider"], "google")
        self.assertEqual(output["activity"], "gmail_list_messages")
        self.assertEqual(output["count"], 2)
        self.assertEqual(output["messages"][0]["id"], "m1")

    def test_github_repo_details_activity_executes_and_normalizes_output(self) -> None:
        self.save_connector(
            {
                "id": "github-primary",
                "provider": "github",
                "name": "GitHub",
                "status": "connected",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "ghp_secret_token"},
            }
        )
        connection = app.state.connection

        output = execute_connector_activity(
            connection,
            connector_id="github-primary",
            activity_id="repo_details",
            inputs={"owner": "openai", "repo": "malcom"},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: (
                200,
                {
                    "full_name": "openai/malcom",
                    "default_branch": "main",
                    "visibility": "private",
                    "open_issues_count": 11,
                    "stargazers_count": 42,
                },
            ),
        )

        self.assertEqual(output["provider"], "github")
        self.assertEqual(output["repository"], "openai/malcom")
        self.assertEqual(output["default_branch"], "main")
        self.assertEqual(output["stars"], 42)

    def test_google_sheets_update_range_requires_json_payload(self) -> None:
        self.save_connector(
            {
                "id": "google-sheets",
                "provider": "google",
                "name": "Google",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )

        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Sheets update automation",
                "description": "Update a range.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "connector_activity",
                        "name": "Update sheet",
                        "config": {
                            "connector_id": "google-sheets",
                            "activity_id": "sheets_update_range",
                            "activity_inputs": {
                                "spreadsheet_id": "sheet123",
                                "range": "Sheet1!A1:B2",
                                "values_payload": "not-json"
                            },
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("invalid JSON", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
