from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from backend.services import automation_execution, helpers, ui_assets


def test_helpers_uses_extracted_ui_asset_helpers() -> None:
    assert helpers.get_ui_dir is ui_assets.get_ui_dir
    assert helpers.ensure_built_ui is ui_assets.ensure_built_ui


def test_outgoing_delivery_mockable_at_automation_execution() -> None:
    sentinel = object()
    with patch("backend.services.automation_execution.execute_outgoing_test_delivery", return_value=sentinel):
        assert automation_execution.execute_outgoing_test_delivery(object()) is sentinel


def test_connector_activity_mockable_at_automation_execution() -> None:
    sentinel = {"ok": True}
    with patch("backend.services.automation_execution.execute_connector_activity", return_value=sentinel):
        assert automation_execution.execute_connector_activity(
            object(),
            connector_id="connector-1",
            activity_id="repo_details",
            inputs={},
            root_dir=Path("."),
        ) is sentinel
