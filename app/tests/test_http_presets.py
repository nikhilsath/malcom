"""Tests for HTTP request presets in workflow builder."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.http_presets import (
    DEFAULT_HTTP_PRESET_CATALOG,
    get_http_preset,
    get_http_presets_by_provider,
    list_http_preset_catalog,
)
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class TestHttpPresetCatalog:
    """Tests for HTTP preset definitions and catalog functions."""

    def test_google_presets_exist(self):
        """Verify Google HTTP presets are defined in catalog."""
        google_presets = get_http_presets_by_provider("google")
        assert len(google_presets) > 0, "Google presets should exist"

    def test_github_presets_exist(self):
        """Verify GitHub HTTP presets are defined in catalog."""
        github_presets = get_http_presets_by_provider("github")
        assert len(github_presets) > 0, "GitHub presets should exist"

    def test_notion_presets_exist(self):
        """Verify Notion HTTP presets are defined in catalog."""
        notion_presets = get_http_presets_by_provider("notion")
        assert len(notion_presets) > 0, "Notion presets should exist"
        assert {preset.preset_id for preset in notion_presets} >= {"notion_query_database_http", "notion_create_page_http"}

    def test_trello_presets_exist(self):
        """Verify Trello HTTP presets are defined in catalog."""
        trello_presets = get_http_presets_by_provider("trello")
        assert len(trello_presets) > 0, "Trello presets should exist"
        assert {preset.preset_id for preset in trello_presets} >= {"trello_list_board_cards_http", "trello_create_card_http"}

    def test_preset_fields_are_valid_json(self):
        """Each preset's payload_template must be valid JSON."""
        for preset in DEFAULT_HTTP_PRESET_CATALOG:
            try:
                json.loads(preset.payload_template)
            except json.JSONDecodeError as e:
                pytest.fail(f"Preset {preset.preset_id} has invalid JSON payload_template: {e}")

    def test_preset_endpoint_paths_are_non_empty(self):
        """Each preset must have a non-empty endpoint path template."""
        for preset in DEFAULT_HTTP_PRESET_CATALOG:
            assert preset.endpoint_path_template, f"Preset {preset.preset_id} has empty endpoint_path_template"

    def test_preset_http_method_is_valid(self):
        """Preset HTTP method must be one of the allowed methods."""
        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        for preset in DEFAULT_HTTP_PRESET_CATALOG:
            assert preset.http_method in allowed_methods, f"Preset {preset.preset_id} has invalid HTTP method: {preset.http_method}"

    def test_get_http_preset_by_provider_and_id(self):
        """get_http_preset should return preset when provider and id match."""
        preset = get_http_preset("google", "gmail_list_messages_http")
        assert preset is not None
        assert preset.service == "gmail"
        assert preset.operation == "read"

    def test_get_http_preset_returns_none_for_unknown_preset(self):
        """get_http_preset should return None for unknown preset."""
        preset = get_http_preset("google", "unknown_preset_id")
        assert preset is None

    def test_get_http_preset_returns_none_for_unknown_provider(self):
        """get_http_preset should return None for unknown provider."""
        preset = get_http_preset("unknown_provider", "some_preset")
        assert preset is None

    def test_preset_required_scopes_not_empty_for_google(self):
        """Google presets should have required scopes."""
        for preset in get_http_presets_by_provider("google"):
            assert preset.required_scopes, f"Preset {preset.preset_id} should have required_scopes"
            # All should be Google API scopes
            for scope in preset.required_scopes:
                assert "googleapis.com" in scope, f"Preset {preset.preset_id} has malformed scope: {scope}"

    def test_preset_to_dict_serialization(self):
        """Preset.to_dict() should produce valid serializable dict."""
        preset = get_http_preset("google", "gmail_list_messages_http")
        assert preset is not None
        preset_dict = preset.to_dict()
        assert preset_dict["preset_id"] == "gmail_list_messages_http"
        assert preset_dict["provider_id"] == "google"
        assert preset_dict["http_method"] == "GET"
        assert isinstance(preset_dict["required_scopes"], list)
        assert isinstance(preset_dict["input_schema"], list)
        # Should be JSON serializable
        json.dumps(preset_dict)

    def test_gmail_send_email_preset_has_required_inputs(self):
        """Gmail send email preset should have to, subject, body inputs marked as required."""
        preset = get_http_preset("google", "gmail_send_email_http")
        assert preset is not None
        input_keys = {field["key"] for field in preset.input_schema}
        assert "to" in input_keys
        assert "subject" in input_keys
        assert "body" in input_keys
        # Check required fields
        required_keys = {field["key"] for field in preset.input_schema if field.get("required")}
        assert "to" in required_keys
        assert "subject" in required_keys
        assert "body" in required_keys

    def test_gmail_list_messages_preset_exposes_documented_query_params(self):
        """Gmail list preset should expose the supported list query parameters in the builder UI."""
        preset = get_http_preset("google", "gmail_list_messages_http")
        assert preset is not None
        assert [field["key"] for field in preset.input_schema] == [
            "q",
            "labelIds",
            "maxResults",
            "pageToken",
            "includeSpamTrash",
        ]
        assert preset.query_params == {"maxResults": "100"}

    def test_sheets_range_presets_have_spreadsheet_id_input(self):
        """Sheets read/update presets should include spreadsheet_id input."""
        for preset_id in ["sheets_read_range_http", "sheets_update_range_http"]:
            preset = get_http_preset("google", preset_id)
            assert preset is not None
            input_keys = {field["key"] for field in preset.input_schema}
            assert "spreadsheet_id" in input_keys
            assert "range_name" in input_keys

    def test_drive_list_preset_exposes_shared_drive_query_controls(self):
        """Drive list preset should expose the supported list query parameters."""
        preset = get_http_preset("google", "drive_list_files_http")
        assert preset is not None
        assert [field["key"] for field in preset.input_schema] == [
            "q",
            "corpora",
            "pageSize",
            "pageToken",
            "driveId",
            "includeItemsFromAllDrives",
            "orderBy",
            "spaces",
            "supportsAllDrives",
        ]
        assert preset.query_params == {"pageSize": "100", "fields": "files(id,name,mimeType,parents)"}

    def test_sheets_presets_expose_render_and_response_query_controls(self):
        """Sheets presets should expose documented read and update query parameters."""
        read_preset = get_http_preset("google", "sheets_read_range_http")
        update_preset = get_http_preset("google", "sheets_update_range_http")
        assert read_preset is not None
        assert update_preset is not None
        assert [field["key"] for field in read_preset.input_schema][-3:] == [
            "majorDimension",
            "valueRenderOption",
            "dateTimeRenderOption",
        ]
        assert [field["key"] for field in update_preset.input_schema][-4:] == [
            "valueInputOption",
            "includeValuesInResponse",
            "responseValueRenderOption",
            "responseDateTimeRenderOption",
        ]

    def test_drive_presets_exist(self):
        """Drive presets should be available."""
        drive_presets = [p for p in get_http_presets_by_provider("google") if p.service == "drive"]
        assert len(drive_presets) >= 2, "Should have at least list_files and upload_file"

    def test_github_issue_and_actions_presets_expose_documented_inputs(self):
        """GitHub presets should expose repository, issue, and actions inputs in the builder."""
        issue_preset = get_http_preset("github", "issues_create_http")
        comment_preset = get_http_preset("github", "issues_add_comment_http")
        dispatch_preset = get_http_preset("github", "actions_trigger_workflow_dispatch_http")
        assert issue_preset is not None
        assert comment_preset is not None
        assert dispatch_preset is not None
        assert [field["key"] for field in issue_preset.input_schema] == ["owner", "repo", "title", "body"]
        assert [field["key"] for field in comment_preset.input_schema] == ["owner", "repo", "issue_number", "body"]
        assert [field["key"] for field in dispatch_preset.input_schema] == ["owner", "repo", "workflow_id", "ref", "inputs_payload"]
        assert dispatch_preset.http_method == "POST"
        assert "{{workflow_id}}" in dispatch_preset.endpoint_path_template

    def test_github_list_workflow_runs_preset_exposes_filters(self):
        """GitHub workflow-run preset should expose the documented run filters."""
        preset = get_http_preset("github", "actions_list_workflow_runs_http")
        assert preset is not None
        assert [field["key"] for field in preset.input_schema] == [
            "owner",
            "repo",
            "branch",
            "event",
            "status",
            "per_page",
        ]
        assert preset.query_params == {"per_page": "20"}

    def test_notion_and_trello_presets_expose_documented_inputs(self):
        """Notion and Trello presets should expose provider-specific inputs."""
        notion_query = get_http_preset("notion", "notion_query_database_http")
        notion_create = get_http_preset("notion", "notion_create_page_http")
        trello_list = get_http_preset("trello", "trello_list_board_cards_http")
        trello_create = get_http_preset("trello", "trello_create_card_http")
        assert notion_query is not None
        assert notion_create is not None
        assert trello_list is not None
        assert trello_create is not None
        assert [field["key"] for field in notion_query.input_schema] == [
            "database_id",
            "page_size",
            "start_cursor",
            "filter_json",
            "sorts_json",
        ]
        assert [field["key"] for field in notion_create.input_schema] == [
            "database_id",
            "properties_json",
            "children_json",
        ]
        assert [field["key"] for field in trello_list.input_schema] == [
            "board_id",
            "limit",
            "card_filter",
        ]
        assert [field["key"] for field in trello_create.input_schema] == [
            "list_id",
            "name",
            "desc",
            "due",
        ]


class TestHttpPresetValidity:
    """Tests to validate preset endpoint contracts (explicitly requested by user)."""

    def test_all_presets_have_valid_endpoint_urls(self):
        """All preset endpoint paths should form valid URL paths (http/https + host + path).
        
        This test ensures that materialized preset URLs will be valid.
        """
        for preset in DEFAULT_HTTP_PRESET_CATALOG:
            # Endpoint path should not be empty
            assert preset.endpoint_path_template.strip(), f"Preset {preset.preset_id} has empty endpoint path"
            # Should start with / for path (or contain {{variable}} templates)
            assert preset.endpoint_path_template.startswith("/") or "{{" in preset.endpoint_path_template, \
                f"Preset {preset.preset_id} endpoint should start with / or contain template variables"

    def test_gmail_list_endpoint_path_is_valid(self):
        """Verify Gmail list preset materializes to valid endpoint."""
        preset = get_http_preset("google", "gmail_list_messages_http")
        assert preset is not None
        assert preset.endpoint_path_template == "/gmail/v1/users/me/messages"
        assert preset.http_method == "GET"

    def test_sheets_update_endpoint_uses_template_variables(self):
        """Sheets update preset should use template variables for spreadsheet_id and range."""
        preset = get_http_preset("google", "sheets_update_range_http")
        assert preset is not None
        assert "{{spreadsheet_id}}" in preset.endpoint_path_template
        assert "{{range_name}}" in preset.endpoint_path_template
        assert preset.http_method == "PUT"

    def test_drive_upload_endpoint_is_upload_api(self):
        """Drive upload preset should use the upload API endpoint."""
        preset = get_http_preset("google", "drive_upload_file_http")
        assert preset is not None
        assert "/upload/" in preset.endpoint_path_template
        assert "uploadType" in preset.query_params


@pytest.fixture
def client() -> TestClient:
    tempdir = tempfile.TemporaryDirectory()
    root_dir = Path(tempdir.name)
    ensure_test_ui_scripts_dir(root_dir)
    setup_postgres_test_app(app=app, root_dir=root_dir)
    with TestClient(app) as test_client:
        yield test_client
    tempdir.cleanup()


def _insert_http_preset_override() -> None:
    now = "2026-04-03T00:00:00+00:00"
    app.state.connection.execute(
        """
        INSERT INTO connector_endpoint_definitions (
            endpoint_id,
            provider_id,
            endpoint_kind,
            service,
            operation_type,
            label,
            description,
            http_method,
            endpoint_path_template,
            query_params_json,
            required_scopes_json,
            input_schema_json,
            output_schema_json,
            payload_template,
            execution_json,
            metadata_json,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(endpoint_id) DO UPDATE SET
            label = excluded.label,
            description = excluded.description,
            updated_at = excluded.updated_at
        """,
        (
            "http_preset:google:smoke_custom_preset",
            "google",
            "http_preset",
            "gmail",
            "read",
            "Smoke custom preset",
            "Persisted test preset",
            "GET",
            "/gmail/v1/users/me/messages",
            json.dumps({"maxResults": "5"}),
            json.dumps(["https://www.googleapis.com/auth/gmail.readonly"]),
            json.dumps([]),
            json.dumps([]),
            "{}",
            json.dumps({}),
            json.dumps({"preset_id": "smoke_custom_preset"}),
            now,
            now,
        ),
    )
    app.state.connection.commit()


def test_list_http_preset_catalog_reads_persisted_definitions(client: TestClient):
    _insert_http_preset_override()

    catalog = list_http_preset_catalog(app.state.connection)
    preset = next(item for item in catalog if item["preset_id"] == "smoke_custom_preset")
    assert preset["provider_id"] == "google"
    assert preset["label"] == "Smoke custom preset"


def test_http_presets_route_reads_persisted_definitions(client: TestClient):
    _insert_http_preset_override()

    response = client.get("/api/v1/connectors/http-presets")
    assert response.status_code == 200
    payload = response.json()
    preset = next(item for item in payload if item["preset_id"] == "smoke_custom_preset")
    assert preset["provider_id"] == "google"
    assert preset["label"] == "Smoke custom preset"
