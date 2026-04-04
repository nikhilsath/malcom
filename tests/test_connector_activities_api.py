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
        self.assertIn(("github", "list_repository_issues"), activity_ids)
        self.assertIn(("github", "create_issue"), activity_ids)
        self.assertIn(("github", "list_workflow_runs"), activity_ids)
        self.assertIn(("github", "trigger_workflow_dispatch"), activity_ids)
        self.assertIn(("github", "download_repo_archive"), activity_ids)

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
        captured_request: dict[str, str] = {}

        output = execute_connector_activity(
            connection,
            connector_id="google-primary",
            activity_id="gmail_list_messages",
            inputs={"max_results": 2, "page_token": "page-2", "include_spam_trash": True},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: captured_request.update({"url": url, "method": method}) or (
                200,
                {"messages": [{"id": "m1"}, {"id": "m2"}], "nextPageToken": "next", "resultSizeEstimate": 42},
            ),
        )

        self.assertEqual(output["provider"], "google")
        self.assertEqual(output["activity"], "gmail_list_messages")
        self.assertEqual(output["messages"][0]["id"], "m1")
        self.assertEqual(output["next_page_token"], "next")
        self.assertEqual(output["result_size_estimate"], 42)
        self.assertEqual(captured_request["method"], "GET")
        self.assertIn("maxResults=2", captured_request["url"])
        self.assertIn("pageToken=page-2", captured_request["url"])
        self.assertIn("includeSpamTrash=true", captured_request["url"])

    def test_google_gmail_get_message_and_thread_support_metadata_headers(self) -> None:
        self.save_connector(
            {
                "id": "google-primary",
                "provider": "google",
                "name": "Google",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )
        connection = app.state.connection
        captured_urls: list[str] = []

        execute_connector_activity(
            connection,
            connector_id="google-primary",
            activity_id="gmail_get_message",
            inputs={"message_id": "msg-123", "format": "metadata", "metadata_headers": "Subject,From"},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: captured_urls.append(url) or (200, {"id": "msg-123"}),
        )
        execute_connector_activity(
            connection,
            connector_id="google-primary",
            activity_id="gmail_get_thread",
            inputs={"thread_id": "thr-123", "format": "metadata", "metadata_headers": "Subject,From"},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: captured_urls.append(url) or (200, {"id": "thr-123"}),
        )

        self.assertIn("format=metadata", captured_urls[0])
        self.assertIn("metadataHeaders=Subject", captured_urls[0])
        self.assertIn("metadataHeaders=From", captured_urls[0])
        self.assertIn("format=metadata", captured_urls[1])
        self.assertIn("metadataHeaders=Subject", captured_urls[1])
        self.assertIn("metadataHeaders=From", captured_urls[1])

    def test_google_drive_list_activity_supports_documented_query_params_and_outputs(self) -> None:
        self.save_connector(
            {
                "id": "google-drive",
                "provider": "google",
                "name": "Google Drive",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/drive.metadata.readonly"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )
        connection = app.state.connection
        captured_request: dict[str, str] = {}

        output = execute_connector_activity(
            connection,
            connector_id="google-drive",
            activity_id="drive_list_files",
            inputs={
                "parent_id": "folder-1",
                "max_results": 15,
                "page_token": "drive-page-2",
                "corpora": "drive",
                "drive_id": "drive-123",
                "include_items_from_all_drives": True,
                "order_by": "modifiedTime desc",
                "spaces": "drive",
                "supports_all_drives": True,
            },
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: captured_request.update({"url": url, "method": method}) or (
                200,
                {"files": [{"id": "file-1"}], "nextPageToken": "drive-next", "incompleteSearch": True},
            ),
        )

        self.assertEqual(output["next_page_token"], "drive-next")
        self.assertEqual(output["incomplete_search"], True)
        self.assertEqual(captured_request["method"], "GET")
        self.assertIn("pageSize=15", captured_request["url"])
        self.assertIn("pageToken=drive-page-2", captured_request["url"])
        self.assertIn("corpora=drive", captured_request["url"])
        self.assertIn("driveId=drive-123", captured_request["url"])
        self.assertIn("includeItemsFromAllDrives=true", captured_request["url"])
        self.assertIn("orderBy=modifiedTime+desc", captured_request["url"])
        self.assertIn("supportsAllDrives=true", captured_request["url"])

    def test_google_calendar_activity_supports_documented_query_params_and_outputs(self) -> None:
        self.save_connector(
            {
                "id": "google-calendar",
                "provider": "google",
                "name": "Google Calendar",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )
        connection = app.state.connection
        captured_request: dict[str, str] = {}

        output = execute_connector_activity(
            connection,
            connector_id="google-calendar",
            activity_id="calendar_upcoming_events",
            inputs={
                "calendar_id": "primary",
                "limit": 5,
                "page_token": "calendar-page-2",
                "search_query": "office",
                "show_deleted": True,
                "time_max": "2026-04-03T12:00:00Z",
                "updated_min": "2026-04-03T08:00:00Z",
            },
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: captured_request.update({"url": url, "method": method}) or (
                200,
                {"items": [{"id": "evt-1", "summary": "Office"}], "nextPageToken": "calendar-next", "nextSyncToken": "calendar-sync"},
            ),
        )

        self.assertEqual(output["next_page_token"], "calendar-next")
        self.assertEqual(output["next_sync_token"], "calendar-sync")
        self.assertIn("maxResults=5", captured_request["url"])
        self.assertIn("pageToken=calendar-page-2", captured_request["url"])
        self.assertIn("q=office", captured_request["url"])
        self.assertIn("showDeleted=true", captured_request["url"])
        self.assertIn("timeMax=2026-04-03T12%3A00%3A00Z", captured_request["url"])
        self.assertIn("updatedMin=2026-04-03T08%3A00%3A00Z", captured_request["url"])

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

    def test_github_issue_and_actions_activities_execute_and_normalize_output(self) -> None:
        self.save_connector(
            {
                "id": "github-ops",
                "provider": "github",
                "name": "GitHub Ops",
                "status": "connected",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "ghp_secret_token"},
            }
        )
        connection = app.state.connection

        issue_output = execute_connector_activity(
            connection,
            connector_id="github-ops",
            activity_id="list_repository_issues",
            inputs={"owner": "openai", "repo": "malcom", "state": "open", "labels": "bug,triage", "limit": 2},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: (
                200,
                [
                    {
                        "number": 17,
                        "title": "Fix connector drift",
                        "state": "open",
                        "labels": [{"name": "bug"}, {"name": "triage"}],
                        "assignees": [{"login": "ava"}],
                        "html_url": "https://github.com/openai/malcom/issues/17",
                        "user": {"login": "ava"},
                    }
                ],
            ),
        )
        self.assertEqual(issue_output["repository"], "openai/malcom")
        self.assertEqual(issue_output["count"], 1)
        self.assertEqual(issue_output["issues"][0]["labels"], ["bug", "triage"])
        self.assertEqual(issue_output["issues"][0]["assignees"], ["ava"])

        actions_output = execute_connector_activity(
            connection,
            connector_id="github-ops",
            activity_id="list_workflow_runs",
            inputs={"owner": "openai", "repo": "malcom", "workflow_id": "ci.yml", "branch": "main", "status": "completed", "limit": 1},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: (
                200,
                {
                    "workflow_runs": [
                        {
                            "id": 99,
                            "name": "CI",
                            "display_title": "CI on main",
                            "status": "completed",
                            "conclusion": "success",
                            "event": "push",
                            "head_branch": "main",
                            "html_url": "https://github.com/openai/malcom/actions/runs/99",
                            "created_at": "2026-04-03T08:00:00Z",
                            "updated_at": "2026-04-03T08:05:00Z",
                        }
                    ]
                },
            ),
        )
        self.assertEqual(actions_output["count"], 1)
        self.assertEqual(actions_output["workflow_runs"][0]["branch"], "main")
        self.assertEqual(actions_output["workflow_runs"][0]["conclusion"], "success")

    def test_github_write_activities_execute_and_normalize_output(self) -> None:
        self.save_connector(
            {
                "id": "github-write",
                "provider": "github",
                "name": "GitHub Write",
                "status": "connected",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "ghp_secret_token"},
            }
        )
        connection = app.state.connection

        created_issue = execute_connector_activity(
            connection,
            connector_id="github-write",
            activity_id="create_issue",
            inputs={"owner": "openai", "repo": "malcom", "title": "Ship GitHub presets", "body": "Please ship it.", "labels": "automation"},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers, body=None: (
                201,
                {
                    "number": 24,
                    "title": "Ship GitHub presets",
                    "state": "open",
                    "labels": [{"name": "automation"}],
                    "assignees": [],
                    "html_url": "https://github.com/openai/malcom/issues/24",
                    "user": {"login": "ava"},
                },
            ),
        )
        self.assertEqual(created_issue["issue"]["number"], 24)
        self.assertEqual(created_issue["issue"]["labels"], ["automation"])

        created_comment = execute_connector_activity(
            connection,
            connector_id="github-write",
            activity_id="add_issue_comment",
            inputs={"owner": "openai", "repo": "malcom", "issue_number": 24, "body": "On it."},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers, body=None: (
                201,
                {
                    "id": 301,
                    "body": "On it.",
                    "html_url": "https://github.com/openai/malcom/issues/24#issuecomment-301",
                    "user": {"login": "ava"},
                },
            ),
        )
        self.assertEqual(created_comment["issue_number"], 24)
        self.assertEqual(created_comment["comment"]["author"], "ava")

        dispatch_result = execute_connector_activity(
            connection,
            connector_id="github-write",
            activity_id="trigger_workflow_dispatch",
            inputs={"owner": "openai", "repo": "malcom", "workflow_id": "ci.yml", "ref": "main", "inputs_payload": {"target": "prod"}},
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers, body=None: (204, None),
        )
        self.assertTrue(dispatch_result["dispatched"])
        self.assertEqual(dispatch_result["workflow_id"], "ci.yml")

    def test_github_download_repo_archive_activity_saves_archive_to_workflow_storage(self) -> None:
        self.save_connector(
            {
                "id": "github-archive",
                "provider": "github",
                "name": "GitHub Archive",
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
            connector_id="github-archive",
            activity_id="download_repo_archive",
            inputs={
                "owner": "openai",
                "repo": "malcom",
                "download_location": "workflow_storage",
                "ref": "main",
                "archive_format": "zipball",
                "output_prefix": "malcom-main",
            },
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers, body=None: (
                200,
                {
                    "_raw_bytes_b64": "UEsDBAoAAAAAAA==",
                    "_raw_content_type": "application/zip",
                },
            ),
        )

        archive_path = Path(output["archive_path"])
        self.assertTrue(archive_path.exists())
        self.assertEqual(output["archive_format"], "zipball")
        self.assertEqual(output["repository"], "openai/malcom")
        self.assertEqual(output["download_location"], "workflow_storage")
        self.assertEqual(output["content_type"], "application/zip")
        self.assertEqual(output["bytes_written"], archive_path.stat().st_size)

    def test_google_sheets_range_actions_support_documented_query_controls(self) -> None:
        self.save_connector(
            {
                "id": "google-sheets",
                "provider": "google",
                "name": "Google Sheets",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "google-access-token"},
            }
        )
        connection = app.state.connection
        captured_urls: list[str] = []

        read_output = execute_connector_activity(
            connection,
            connector_id="google-sheets",
            activity_id="sheets_read_range",
            inputs={
                "spreadsheet_id": "sheet-1",
                "range": "Sheet1!A1:B2",
                "major_dimension": "COLUMNS",
                "value_render_option": "UNFORMATTED_VALUE",
                "date_time_render_option": "FORMATTED_STRING",
            },
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers: captured_urls.append(url) or (200, {"range": "Sheet1!A1:B2", "majorDimension": "COLUMNS", "values": [[1, 2]]}),
        )
        update_output = execute_connector_activity(
            connection,
            connector_id="google-sheets",
            activity_id="sheets_update_range",
            inputs={
                "spreadsheet_id": "sheet-1",
                "range": "Sheet1!A1:B2",
                "values_payload": [[1, 2]],
                "value_input_option": "RAW",
                "include_values_in_response": True,
                "response_value_render_option": "UNFORMATTED_VALUE",
                "response_date_time_render_option": "FORMATTED_STRING",
            },
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers, body=None: captured_urls.append(url) or (
                200,
                {"spreadsheetId": "sheet-1", "updatedRange": "Sheet1!A1:B2", "updatedRows": 1, "updatedColumns": 2, "updatedCells": 2, "updatedData": {"values": [[1, 2]]}},
            ),
        )
        append_output = execute_connector_activity(
            connection,
            connector_id="google-sheets",
            activity_id="sheets_append_rows",
            inputs={
                "spreadsheet_id": "sheet-1",
                "range": "Sheet1!A:B",
                "values_payload": [[1, 2]],
                "value_input_option": "RAW",
                "insert_data_option": "OVERWRITE",
                "include_values_in_response": True,
                "response_value_render_option": "UNFORMATTED_VALUE",
                "response_date_time_render_option": "FORMATTED_STRING",
            },
            root_dir=Path(app.state.root_dir),
            request_executor=lambda url, method, headers, body=None: captured_urls.append(url) or (
                200,
                {"spreadsheetId": "sheet-1", "tableRange": "Sheet1!A1:B1", "updates": {"updatedRows": 1}},
            ),
        )

        self.assertEqual(read_output["major_dimension"], "COLUMNS")
        self.assertEqual(update_output["spreadsheet_id"], "sheet-1")
        self.assertEqual(update_output["updated_data"]["values"][0][0], 1)
        self.assertEqual(append_output["spreadsheet_id"], "sheet-1")
        self.assertIn("majorDimension=COLUMNS", captured_urls[0])
        self.assertIn("valueRenderOption=UNFORMATTED_VALUE", captured_urls[0])
        self.assertIn("dateTimeRenderOption=FORMATTED_STRING", captured_urls[0])
        self.assertIn("valueInputOption=RAW", captured_urls[1])
        self.assertIn("includeValuesInResponse=true", captured_urls[1])
        self.assertIn("responseValueRenderOption=UNFORMATTED_VALUE", captured_urls[1])
        self.assertIn("responseDateTimeRenderOption=FORMATTED_STRING", captured_urls[1])
        self.assertIn("insertDataOption=OVERWRITE", captured_urls[2])
        self.assertIn("includeValuesInResponse=true", captured_urls[2])

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
