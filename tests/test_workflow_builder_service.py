"""Unit tests for backend.services.workflow_builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.services.workflow_builder import list_workflow_builder_connectors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_connection():
    return MagicMock()


def _patch_builder(records=None, catalog=None):
    """Return a context-manager triple that patches the three helpers used by
    list_workflow_builder_connectors."""
    record_list = records or []
    catalog_list = catalog or []

    list_records = patch(
        "backend.services.workflow_builder.list_stored_connector_records",
        return_value=record_list,
    )
    build_catalog = patch(
        "backend.services.workflow_builder.build_connector_catalog",
        return_value=catalog_list,
    )
    canonicalize = patch(
        "backend.services.workflow_builder.canonicalize_connector_provider",
        side_effect=lambda p: (p or "").lower(),
    )
    return list_records, build_catalog, canonicalize


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListWorkflowBuilderConnectors:
    def test_empty_records_returns_empty_list(self):
        lr, build_c, canon = _patch_builder()
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result == []

    def test_non_dict_records_are_skipped(self):
        lr, build_c, canon = _patch_builder(records=["not-a-dict", 42, None])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result == []

    def test_records_without_id_are_skipped(self):
        record = {"name": "No ID Connector", "provider": "github", "status": "active"}
        lr, build_c, canon = _patch_builder(records=[record])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result == []

    def test_records_with_blank_id_are_skipped(self):
        record = {"id": "   ", "name": "Blank ID", "provider": "github", "status": "active"}
        lr, build_c, canon = _patch_builder(records=[record])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result == []

    def test_valid_record_produces_normalized_option(self):
        record = {
            "id": "conn-abc",
            "name": "My GitHub",
            "provider": "github",
            "status": "active",
            "auth_type": "oauth2",
            "scopes": ["repo", "read:user"],
            "owner": "org",
            "base_url": "https://api.github.com",
            "docs_url": "https://docs.github.com",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "last_tested_at": "2024-01-03T00:00:00Z",
        }
        catalog = [{"id": "github", "name": "GitHub"}]
        lr, build_c, canon = _patch_builder(records=[record], catalog=catalog)
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert len(result) == 1
        opt = result[0]
        assert opt["id"] == "conn-abc"
        assert opt["name"] == "My GitHub"
        assert opt["provider"] == "github"
        assert opt["provider_name"] == "GitHub"
        assert opt["status"] == "active"
        assert opt["auth_type"] == "oauth2"
        assert opt["scopes"] == ["repo", "read:user"]
        assert opt["owner"] == "org"
        assert opt["base_url"] == "https://api.github.com"
        assert opt["docs_url"] == "https://docs.github.com"
        assert opt["source_path"] == "connectors"

    def test_missing_name_falls_back_to_id(self):
        record = {"id": "conn-xyz", "provider": "slack", "status": "active"}
        lr, build_c, canon = _patch_builder(records=[record])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result[0]["name"] == "conn-xyz"

    def test_missing_status_defaults_to_draft(self):
        # Records with no explicit status pass the inactive filter (treated as "")
        # and the output field falls back to "draft".
        record = {"id": "conn-1", "provider": "slack"}
        lr, build_c, canon = _patch_builder(records=[record])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result[0]["status"] == "draft"

    def test_inactive_status_records_are_filtered(self):
        # draft/expired/revoked statuses are excluded from builder options
        records = [
            {"id": "c1", "provider": "slack", "status": "draft"},
            {"id": "c2", "provider": "slack", "status": "expired"},
            {"id": "c3", "provider": "slack", "status": "revoked"},
        ]
        lr, build_c, canon = _patch_builder(records=records)
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result == []

    def test_non_string_scopes_are_filtered_out(self):
        record = {"id": "conn-1", "provider": "github", "status": "active", "scopes": ["valid", 42, None, "also-valid"]}
        lr, build_c, canon = _patch_builder(records=[record])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result[0]["scopes"] == ["valid", "also-valid"]

    def test_unknown_provider_uses_canonical_as_provider_name(self):
        record = {"id": "conn-1", "provider": "UnknownProvider", "status": "active"}
        lr, build_c, canon = _patch_builder(records=[record], catalog=[])
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        # canonicalize_connector_provider lowercases in the mock, catalog has no entry
        assert result[0]["provider_name"] == "unknownprovider"

    def test_results_sorted_by_name_then_id(self):
        records = [
            {"id": "c3", "name": "Zebra", "provider": "p", "status": "active"},
            {"id": "c1", "name": "Apple", "provider": "p", "status": "active"},
            {"id": "c2", "name": "apple", "provider": "p", "status": "active"},
        ]
        lr, build_c, canon = _patch_builder(records=records)
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        names = [r["name"] for r in result]
        # Case-insensitive sort: "Apple"/"apple" before "Zebra"
        assert names.index("Zebra") > names.index("Apple")

    def test_results_secondary_sort_by_id(self):
        records = [
            {"id": "c2", "name": "Same Name", "provider": "p", "status": "active"},
            {"id": "c1", "name": "Same Name", "provider": "p", "status": "active"},
        ]
        lr, build_c, canon = _patch_builder(records=records)
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result[0]["id"] == "c1"
        assert result[1]["id"] == "c2"

    def test_multiple_valid_records_all_returned(self):
        records = [
            {"id": "c1", "name": "First", "provider": "github", "status": "active"},
            {"id": "c2", "name": "Second", "provider": "slack", "status": "active"},
        ]
        lr, build_c, canon = _patch_builder(records=records)
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert len(result) == 2

    def test_provider_catalog_lookup_used_for_provider_name(self):
        record = {"id": "c1", "name": "My Slack", "provider": "slack", "status": "active"}
        catalog = [{"id": "slack", "name": "Slack"}]
        lr, build_c, canon = _patch_builder(records=[record], catalog=catalog)
        with lr, build_c, canon:
            result = list_workflow_builder_connectors(_mock_connection())
        assert result[0]["provider_name"] == "Slack"

