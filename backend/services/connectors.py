"""Connector secret protection, provider catalog, and auth normalization helpers.

Primary identifiers: connector protection constants, ``DEFAULT_CONNECTOR_CATALOG``,
secret masking/protection helpers, and connector storage/response normalization functions.
"""

from __future__ import annotations

from backend.services.helpers import (
    CONNECTOR_OAUTH_STATE_TTL_SECONDS,
    CONNECTOR_PROTECTION_VERSION,
    CONNECTOR_SECRET_FIELD_INPUTS,
    DEFAULT_CONNECTOR_CATALOG,
    SUPPORTED_CONNECTOR_AUTH_TYPES,
    SUPPORTED_CONNECTOR_PROVIDERS,
    SUPPORTED_CONNECTOR_STATUSES,
    build_connector_catalog,
    build_connector_keystream,
    build_connector_oauth_authorization_url,
    build_outgoing_auth_config_from_connector,
    build_pkce_code_challenge,
    derive_connector_protection_key,
    extract_connector_secret_map,
    find_stored_connector_record,
    get_connector_preset,
    get_connector_protection_secret,
    get_default_connector_settings,
    get_stored_connector_settings,
    hydrate_outgoing_configuration_from_connector,
    mask_connector_secret,
    merge_outgoing_auth_config,
    normalize_connector_auth_config_for_storage,
    normalize_connector_auth_policy,
    normalize_connector_record_for_storage,
    normalize_connector_settings_for_storage,
    protect_connector_secret_value,
    sanitize_connector_auth_config_response,
    sanitize_connector_record_for_response,
    sanitize_connector_settings_for_response,
    unprotect_connector_secret_value,
)

__all__ = [name for name in globals() if not name.startswith("_")]
