"""Tests for HTTP preset mode in automation steps."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect
from backend.main import app
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, get_test_database_url, setup_postgres_test_app


class HttpPresetAutomationTestCase(unittest.TestCase):
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

    def create_test_connector(
        self,
        connector_id: str,
        provider: str = "google",
        scopes: list[str] | None = None,
    ) -> dict:
        """Create a test connector via the connectors API."""
        response = self.client.post(
            "/api/v1/connectors",
            json={
                "id": connector_id,
                "provider": provider,
                "name": f"Test {provider.upper()} Connector",
                "auth_type": "oauth2",
                "status": "connected",
                "scopes": scopes if scopes is not None else ["https://www.googleapis.com/auth/gmail.readonly"],
            },
        )
        if response.status_code != 201:
            raise RuntimeError(f"Failed to create connector: {response.text}")
        return response.json()

    def test_http_preset_mode_creates_automation(self) -> None:
        """HTTP preset step should be accepted and stored in automation."""
        connector_id = "test-google-1"
        self.create_test_connector(connector_id)

        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Gmail List Preset Test",
                "description": "Test HTTP preset mode",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "List Gmail Messages",
                        "config": {
                            "connector_id": connector_id,
                            "http_preset_id": "gmail_list_messages_http",
                            "wait_for_response": True,
                            "response_mappings": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, f"Failed to create automation: {response.text}")
        automation = response.json()
        self.assertIsNotNone(automation.get("id"))
        self.assertEqual(automation["name"], "Gmail List Preset Test")

    def test_http_preset_mode_rejects_unknown_preset_id(self) -> None:
        """HTTP preset step should reject unknown preset IDs."""
        connector_id = "test-google-2"
        self.create_test_connector(connector_id)

        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Invalid Preset Test",
                "description": "Test with invalid preset ID",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "Invalid Step",
                        "config": {
                            "connector_id": connector_id,
                            "http_preset_id": "nonexistent_preset_id",
                            "wait_for_response": True,
                            "response_mappings": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422, f"Should reject invalid preset. Got: {response.text}")
        detail = response.json().get("detail", "")
        self.assertIn("nonexistent_preset_id", str(detail))

    def test_http_preset_step_requires_connector_id(self) -> None:
        """HTTP preset step must have connector_id specified."""
        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Missing Connector Test",
                "description": "Test preset without connector",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "Bad Preset Step",
                        "config": {
                            "http_preset_id": "gmail_list_messages_http",
                            "wait_for_response": True,
                            "response_mappings": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422, f"Should reject preset without connector. Got: {response.text}")
        detail = response.json().get("detail", "")
        self.assertIn("connector_id", str(detail))

    def test_http_preset_mode_missing_scopes_validation(self) -> None:
        """HTTP preset step should validate required scopes."""
        connector_id = "google-no-scopes"
        connection = connect(database_url=get_test_database_url())
        try:
            connection.execute(
                """
                INSERT INTO connectors (id, provider, name, status, auth_type, scopes_json, created_at, updated_at, auth_config_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    connector_id,
                    "google",
                    "Google Without Scopes",
                    "connected",
                    "oauth2",
                    "[]",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    "{}",
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Missing Scopes Test",
                "description": "Connector without required scopes",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "Gmail List Without Scopes",
                        "config": {
                            "connector_id": connector_id,
                            "http_preset_id": "gmail_list_messages_http",
                            "wait_for_response": True,
                            "response_mappings": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422, f"Should reject missing scopes. Got: {response.text}")
        detail = response.json().get("detail", "")
        self.assertIn("missing required scopes", str(detail).lower())

    def test_http_preset_mode_accepts_notion_and_trello_provider_presets(self) -> None:
        notion_connector = "notion-preset"
        trello_connector = "trello-preset"
        self.client.post(
            "/api/v1/connectors",
            json={
                "id": notion_connector,
                "provider": "notion",
                "name": "Notion Connector",
                "auth_type": "bearer",
                "status": "connected",
                "scopes": [],
            },
        )
        self.client.post(
            "/api/v1/connectors",
            json={
                "id": trello_connector,
                "provider": "trello",
                "name": "Trello Connector",
                "auth_type": "bearer",
                "status": "connected",
                "scopes": [],
            },
        )

        notion_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Notion Preset Test",
                "description": "Test Notion HTTP preset mode",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "Query Notion",
                        "config": {
                            "connector_id": notion_connector,
                            "http_preset_id": "notion_query_database_http",
                            "wait_for_response": True,
                            "response_mappings": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(notion_response.status_code, 201, notion_response.text)

        trello_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Trello Preset Test",
                "description": "Test Trello HTTP preset mode",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "List Trello Cards",
                        "config": {
                            "connector_id": trello_connector,
                            "http_preset_id": "trello_list_board_cards_http",
                            "wait_for_response": True,
                            "response_mappings": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(trello_response.status_code, 201, trello_response.text)


if __name__ == "__main__":
    unittest.main()
