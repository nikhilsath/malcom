"""Unit tests for connector_catalog module."""
from __future__ import annotations
import pytest
from backend.services.connector_catalog import (
    DEFAULT_CONNECTOR_CATALOG,
    SUPPORTED_CONNECTOR_AUTH_TYPES,
    SUPPORTED_CONNECTOR_STATUSES,
    CONNECTOR_PROVIDER_CANONICAL_MAP,
    build_connector_response_metadata,
    canonicalize_connector_provider,
    get_connector_provider_metadata,
    normalize_connector_auth_policy,
    normalize_connector_request_auth_type,
    build_connector_catalog,
    get_default_connector_settings,
)


def test_default_catalog_is_list():
    assert isinstance(DEFAULT_CONNECTOR_CATALOG, list)
    assert len(DEFAULT_CONNECTOR_CATALOG) >= 4


def test_default_catalog_has_expected_ids():
    ids = {item["id"] for item in DEFAULT_CONNECTOR_CATALOG}
    assert {"google", "github", "notion", "trello"}.issubset(ids)


def test_canonicalize_legacy_google_providers():
    assert canonicalize_connector_provider("google_calendar") == "google"
    assert canonicalize_connector_provider("google_gmail") == "google"
    assert canonicalize_connector_provider("google_sheets") == "google"


def test_canonicalize_unknown_returns_as_is():
    assert canonicalize_connector_provider("github") == "github"
    assert canonicalize_connector_provider("trello") == "trello"


def test_canonicalize_none_returns_none():
    assert canonicalize_connector_provider(None) is None


def test_normalize_connector_auth_policy_defaults():
    result = normalize_connector_auth_policy(None)
    assert result["rotation_interval_days"] == 90
    assert result["reconnect_requires_approval"] is True
    assert result["credential_visibility"] == "masked"


def test_normalize_connector_auth_policy_invalid_interval_resets():
    result = normalize_connector_auth_policy({"rotation_interval_days": 999})
    assert result["rotation_interval_days"] == 90


def test_normalize_connector_auth_policy_valid_interval():
    result = normalize_connector_auth_policy({"rotation_interval_days": 30})
    assert result["rotation_interval_days"] == 30


def test_normalize_connector_request_auth_type_oauth2():
    assert normalize_connector_request_auth_type("oauth2") == "bearer"


def test_normalize_connector_request_auth_type_api_key():
    assert normalize_connector_request_auth_type("api_key") == "header"


def test_normalize_connector_request_auth_type_unknown():
    assert normalize_connector_request_auth_type("unknown") == "none"


def test_get_connector_provider_metadata_google():
    meta = get_connector_provider_metadata("google")
    assert meta is not None
    assert meta["id"] == "google"
    assert meta["oauth_supported"] is True


def test_get_connector_provider_metadata_none():
    assert get_connector_provider_metadata(None) is None


def test_build_connector_catalog_no_connection():
    catalog = build_connector_catalog(None)
    assert isinstance(catalog, list)
    assert len(catalog) >= 4


def test_get_default_connector_settings():
    settings = get_default_connector_settings()
    assert "catalog" in settings
    assert "records" in settings
    assert "auth_policy" in settings


def test_build_connector_response_metadata():
    meta = build_connector_response_metadata()
    assert "statuses" in meta
    assert "providers" in meta
    assert "auth_policy" in meta


def test_supported_connector_auth_types():
    assert "oauth2" in SUPPORTED_CONNECTOR_AUTH_TYPES
    assert "bearer" in SUPPORTED_CONNECTOR_AUTH_TYPES
    assert "api_key" in SUPPORTED_CONNECTOR_AUTH_TYPES


def test_supported_connector_statuses():
    assert "connected" in SUPPORTED_CONNECTOR_STATUSES
    assert "draft" in SUPPORTED_CONNECTOR_STATUSES
