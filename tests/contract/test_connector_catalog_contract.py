"""Contract tests for connector_catalog module."""
from __future__ import annotations
import pytest
import backend.services.connector_catalog as catalog_module

EXPECTED_EXPORTS = {
    "DEFAULT_CONNECTOR_CATALOG",
    "DEFAULT_CONNECTOR_PROVIDER_METADATA",
    "SUPPORTED_CONNECTOR_PROVIDERS",
    "SUPPORTED_CONNECTOR_AUTH_TYPES",
    "SUPPORTED_CONNECTOR_STATUSES",
    "canonicalize_connector_provider",
    "build_connector_catalog",
    "get_connector_preset",
    "get_connector_provider_metadata",
    "get_default_connector_settings",
    "normalize_connector_auth_policy",
    "normalize_connector_request_auth_type",
    "build_connector_response_metadata",
}


def test_all_expected_exports_present():
    for name in EXPECTED_EXPORTS:
        assert hasattr(catalog_module, name), f"Missing export: {name}"


def test_no_connector_service_imports():
    """connector_catalog must not import from connector_secrets or connectors."""
    import inspect
    src = inspect.getsource(catalog_module)
    assert "from backend.services.connectors" not in src
    assert "from backend.services.connector_secrets" not in src
    assert "from backend.services.connector_migrations" not in src


def test_default_catalog_structure():
    from backend.services.connector_catalog import DEFAULT_CONNECTOR_CATALOG
    required_fields = {"id", "name", "description", "category", "auth_types", "docs_url", "base_url"}
    for entry in DEFAULT_CONNECTOR_CATALOG:
        assert required_fields.issubset(set(entry.keys())), f"Missing fields in {entry['id']}"


def test_normalize_auth_policy_idempotent():
    from backend.services.connector_catalog import normalize_connector_auth_policy
    policy = {"rotation_interval_days": 60, "reconnect_requires_approval": False, "credential_visibility": "admin_only"}
    once = normalize_connector_auth_policy(policy)
    twice = normalize_connector_auth_policy(once)
    assert once == twice


def test_build_connector_catalog_no_connection_returns_list():
    from backend.services.connector_catalog import build_connector_catalog
    result = build_connector_catalog(None)
    assert isinstance(result, list)
    assert len(result) > 0
