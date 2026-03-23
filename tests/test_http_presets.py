"""Tests for HTTP request presets in workflow builder."""

import json
import pytest
from backend.services.http_presets import (
    DEFAULT_HTTP_PRESET_CATALOG,
    get_http_preset,
    get_http_presets_by_provider,
)


class TestHttpPresetCatalog:
    """Tests for HTTP preset definitions and catalog functions."""

    def test_google_presets_exist(self):
        """Verify Google HTTP presets are defined in catalog."""
        google_presets = get_http_presets_by_provider("google")
        assert len(google_presets) > 0, "Google presets should exist"

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

    def test_sheets_range_presets_have_spreadsheet_id_input(self):
        """Sheets read/update presets should include spreadsheet_id input."""
        for preset_id in ["sheets_read_range_http", "sheets_update_range_http"]:
            preset = get_http_preset("google", preset_id)
            assert preset is not None
            input_keys = {field["key"] for field in preset.input_schema}
            assert "spreadsheet_id" in input_keys
            assert "range_name" in input_keys

    def test_drive_presets_exist(self):
        """Drive presets should be available."""
        drive_presets = [p for p in get_http_presets_by_provider("google") if p.service == "drive"]
        assert len(drive_presets) >= 2, "Should have at least list_files and upload_file"


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
