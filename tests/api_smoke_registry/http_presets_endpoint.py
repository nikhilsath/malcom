"""Smoke test case for HTTP presets endpoint."""

import json

def test_http_presets_endpoint_returns_google_presets():
    """Verify /api/v1/connectors/http-presets returns valid preset definitions."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    response = client.get("/api/v1/connectors/http-presets")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    presets = response.json()
    
    assert isinstance(presets, list), "Presets should be a list"
    assert len(presets) > 0, "Should return at least one preset"
    
    # Check structure of first preset
    first_preset = presets[0]
    required_fields = {"preset_id", "provider_id", "service", "operation", "label", "description",
                      "http_method", "endpoint_path_template", "payload_template", "required_scopes", "input_schema"}
    for field in required_fields:
        assert field in first_preset, f"Preset missing field: {field}"
    
    # Verify some Google presets are present
    preset_ids = {p["preset_id"] for p in presets}
    assert "gmail_list_messages_http" in preset_ids, "Gmail list preset should be present"
    assert "drive_list_files_http" in preset_ids, "Drive list preset should be present"
    
    # Verify payloads are valid JSON
    for preset in presets:
        try:
            json.loads(preset["payload_template"])
        except json.JSONDecodeError as e:
            raise AssertionError(f"Preset {preset['preset_id']} has invalid JSON payload: {e}")
