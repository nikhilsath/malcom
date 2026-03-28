from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect, fetch_all
from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class SettingsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        manifest_dir = self.root_dir / "ui" / "scripts"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        self.database_url = setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.skip_ui_build_check = False
        self.tempdir.cleanup()

    def test_get_settings_returns_seeded_defaults(self) -> None:
        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["logging"]["max_stored_entries"], 250)
        self.assertEqual(body["logging"]["max_file_size_mb"], 5)
        self.assertEqual(body["notifications"]["channel"], "email")
        self.assertEqual(body["automation"]["default_tool_retries"], 2)
        self.assertEqual(body["connectors"]["records"], [])
        self.assertEqual(body["connectors"]["auth_policy"]["rotation_interval_days"], 90)
        provider_ids = {item["id"] for item in body["connectors"]["catalog"]}
        self.assertIn("google", provider_ids)
        self.assertIn("github", provider_ids)

    def test_get_settings_reads_connector_catalog_from_connectors_table(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO connectors (
                    id,
                    integration_type,
                    provider,
                    name,
                    description,
                    category,
                    auth_types_json,
                    default_scopes_json,
                    docs_url,
                    base_url,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    provider = excluded.provider,
                    name = excluded.name,
                    description = excluded.description,
                    category = excluded.category,
                    auth_types_json = excluded.auth_types_json,
                    default_scopes_json = excluded.default_scopes_json,
                    docs_url = excluded.docs_url,
                    base_url = excluded.base_url,
                    updated_at = excluded.updated_at
                """,
                (
                    "provider_mailchimp",
                    "connector_provider",
                    "mailchimp",
                    "Mailchimp",
                    "Sync campaigns and audiences.",
                    "marketing",
                    json.dumps(["bearer"]),
                    json.dumps([]),
                    "https://mailchimp.com/developer/marketing/api/",
                    "https://us1.api.mailchimp.com/3.0",
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        provider_ids = {item["id"] for item in response.json()["connectors"]["catalog"]}
        self.assertIn("mailchimp", provider_ids)

    def test_patch_settings_persists_updates_to_database(self) -> None:
        response = self.client.patch(
            "/api/v1/settings",
            json={
                "general": {
                    "environment": "live",
                    "timezone": "utc",
                },
                "logging": {
                    "max_stored_entries": 500,
                    "max_visible_entries": 100,
                    "max_detail_characters": 6000,
                    "max_file_size_mb": 8,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["logging"]["max_stored_entries"], 500)
        self.assertEqual(body["logging"]["max_file_size_mb"], 8)
        self.assertEqual(body["notifications"]["digest"], "hourly")

        connection = connect(database_url=self.database_url)
        try:
            rows = fetch_all(
                connection,
                """
                SELECT key, value_json
                FROM settings
                ORDER BY key
                """,
            )
        finally:
            connection.close()

        saved_settings = {row["key"]: json.loads(row["value_json"]) for row in rows}
        self.assertEqual(saved_settings["general"]["environment"], "live")
        self.assertEqual(saved_settings["logging"]["max_visible_entries"], 100)
        self.assertEqual(saved_settings["logging"]["max_file_size_mb"], 8)
        self.assertEqual(saved_settings["notifications"]["channel"], "email")

    def test_patch_connectors_masks_secret_values_and_stores_protected_payload(self) -> None:
        response = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "google-calendar-primary",
                            "provider": "google_calendar",
                            "name": "Google Calendar",
                            "status": "draft",
                            "auth_type": "oauth2",
                            "scopes": ["https://www.googleapis.com/auth/calendar"],
                            "base_url": "https://www.googleapis.com/calendar/v3",
                            "owner": "Workspace",
                            "auth_config": {
                                "client_id": "calendar-client-id",
                                "client_secret_input": "calendar-client-secret",
                                "access_token_input": "calendar-access-token",
                                "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                            },
                        }
                    ]
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        record = body["connectors"]["records"][0]
        self.assertEqual(record["provider"], "google")
        self.assertIsNotNone(record["auth_config"]["client_secret_masked"])
        self.assertIsNotNone(record["auth_config"]["access_token_masked"])
        self.assertNotIn("calendar-client-secret", json.dumps(body))
        self.assertNotIn("calendar-access-token", json.dumps(body))
        provider_ids = {item["id"] for item in body["connectors"]["catalog"]}
        self.assertIn("google", provider_ids)
        self.assertIn("github", provider_ids)

        connection = connect(database_url=self.database_url)
        try:
            row = fetch_all(
                connection,
                """
                SELECT auth_config_json
                FROM connectors
                WHERE integration_type = 'saved_connector' AND id = 'google-calendar-primary'
                """,
            )[0]
            settings_row = fetch_all(
                connection,
                """
                SELECT value_json
                FROM settings
                WHERE key = 'connectors'
                """,
            )[0]
        finally:
            connection.close()

        stored_value = row["auth_config_json"]
        self.assertNotIn("calendar-client-secret", stored_value)
        self.assertNotIn("calendar-access-token", stored_value)
        self.assertEqual(json.loads(settings_row["value_json"]), {"auth_policy": body["connectors"]["auth_policy"]})

    def test_list_connectors_reads_saved_records_from_connectors_table(self) -> None:
        patch_response = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "github-primary",
                            "provider": "github",
                            "name": "GitHub Primary",
                            "status": "enabled",
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

        response = self.client.get("/api/v1/connectors")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], "github-primary")
        self.assertEqual(body[0]["name"], "GitHub Primary")
        self.assertEqual(body[0]["status"], "enabled")
        self.assertNotIn("ghp_secret_token", json.dumps(body))

    def test_get_settings_tolerates_malformed_protected_connector_secret(self) -> None:
        patch_response = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "google-calendar-primary",
                            "provider": "google_calendar",
                            "name": "Google Calendar",
                            "status": "draft",
                            "auth_type": "oauth2",
                            "scopes": ["https://www.googleapis.com/auth/calendar"],
                            "base_url": "https://www.googleapis.com/calendar/v3",
                            "owner": "Workspace",
                            "auth_config": {
                                "client_id": "calendar-client-id",
                                "client_secret_input": "calendar-client-secret",
                                "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                            },
                        }
                    ]
                }
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        connection = connect(database_url=self.database_url)
        try:
            row = fetch_all(
                connection,
                """
                SELECT auth_config_json
                FROM connectors
                WHERE integration_type = 'saved_connector' AND id = 'google-calendar-primary'
                """,
            )[0]
            auth_config = json.loads(row["auth_config_json"])
            protected_secrets = auth_config.setdefault("protected_secrets", {})
            protected_secrets["client_secret"] = "enc_v1:not-base64"
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                UPDATE connectors
                SET auth_config_json = ?, updated_at = ?
                WHERE integration_type = 'saved_connector' AND id = 'google-calendar-primary'
                """,
                (json.dumps(auth_config), now_value),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")
        self.assertEqual(response.status_code, 200)
        record = response.json()["connectors"]["records"][0]
        self.assertIsNone(record["auth_config"].get("client_secret_masked"))
        self.assertNotIn("calendar-client-secret", json.dumps(response.json()))

    def test_oauth_callback_rejects_invalid_state(self) -> None:
        response = self.client.get("/api/v1/connectors/google/oauth/callback?state=invalid&code=demo")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid OAuth state.")

    def test_oauth_callback_redirects_browser_requests_to_connectors_settings(self) -> None:
        settings_response = self.client.get("/api/v1/settings")
        self.assertEqual(settings_response.status_code, 200)
        settings = settings_response.json()
        google_preset = next((item for item in settings["connectors"]["catalog"] if item["id"] == "google"), None)
        self.assertIsNotNone(google_preset)

        patch_response = self.client.patch(
            "/api/v1/settings",
            json={
                "connectors": {
                    "records": [
                        {
                            "id": "google",
                            "provider": "google",
                            "name": google_preset["name"],
                            "status": "draft",
                            "auth_type": "oauth2",
                            "scopes": [],
                            "base_url": google_preset["base_url"],
                            "owner": "Workspace",
                            "docs_url": google_preset["docs_url"],
                            "credential_ref": "connector/google",
                            "created_at": "2026-03-20T00:00:00+00:00",
                            "updated_at": "2026-03-20T00:00:00+00:00",
                            "auth_config": {
                                "client_id": "demo-client-id.apps.googleusercontent.com",
                                "redirect_uri": "http://127.0.0.1:8000/api/v1/connectors/google/oauth/callback",
                                "scope_preset": "google",
                                "has_refresh_token": False,
                            },
                        }
                    ],
                    "auth_policy": settings["connectors"]["auth_policy"],
                }
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        start_response = self.client.post(
            "/api/v1/connectors/google/oauth/start",
            json={
                "connector_id": "google",
                "name": google_preset["name"],
                "redirect_uri": "http://127.0.0.1:8000/api/v1/connectors/google/oauth/callback",
                "owner": "Workspace",
                "scopes": [],
                "client_id": "demo-client-id.apps.googleusercontent.com",
            },
        )
        self.assertEqual(start_response.status_code, 200)
        state = start_response.json()["state"]

        callback_response = self.client.get(
            f"/api/v1/connectors/google/oauth/callback?state={state}&code=demo-authorized",
            headers={"accept": "text/html"},
            follow_redirects=False,
        )

        self.assertEqual(callback_response.status_code, 303)
        location = callback_response.headers.get("location", "")
        self.assertIn("/settings/connectors.html", location)
        self.assertIn("oauth_status=success", location)
        self.assertIn("connector_id=google", location)

    def test_get_settings_backfills_missing_logging_fields_from_defaults(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    "logging",
                    json.dumps(
                        {
                            "max_stored_entries": 300,
                            "max_visible_entries": 75,
                            "max_detail_characters": 5000,
                        }
                    ),
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["logging"]["max_stored_entries"], 300)
        self.assertEqual(body["logging"]["max_visible_entries"], 75)
        self.assertEqual(body["logging"]["max_detail_characters"], 5000)
        self.assertEqual(body["logging"]["max_file_size_mb"], 5)

    def test_get_settings_falls_back_to_defaults_for_invalid_legacy_values(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-03-20T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                ("general", json.dumps({"environment": "staging", "timezone": "pst"}), now_value, now_value),
            )
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    "notifications",
                    json.dumps({"channel": "teams", "digest": "weekly", "escalate_oncall": True}),
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["general"]["environment"], "live")
        self.assertEqual(body["general"]["timezone"], "local")
        self.assertEqual(body["notifications"]["channel"], "email")
        self.assertEqual(body["notifications"]["digest"], "hourly")


if __name__ == "__main__":
    unittest.main()
