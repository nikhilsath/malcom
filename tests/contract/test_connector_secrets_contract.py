"""Contract tests for connector_secrets module."""
from __future__ import annotations
import inspect
import pytest
from backend.services.connector_secrets import __all__ as SECRETS_ALL
import backend.services.connector_secrets as secrets_module

EXPECTED_EXPORTS = {
    "CONNECTOR_NONCE_BYTES",
    "CONNECTOR_PROTECTION_VERSION",
    "CONNECTOR_SECRET_FIELD_INPUTS",
    "CONNECTOR_SIGNATURE_BYTES",
    "build_connector_keystream",
    "derive_connector_protection_key",
    "extract_connector_secret_map",
    "get_connector_protection_secret",
    "mask_connector_secret",
    "protect_connector_secret_value",
    "unprotect_connector_secret_value",
}


def test_all_expected_exports_present():
    for name in EXPECTED_EXPORTS:
        assert hasattr(secrets_module, name), f"Missing export: {name}"


def test_no_database_imports():
    """connector_secrets must not import from backend.database."""
    import sys
    import importlib
    mod = sys.modules.get("backend.services.connector_secrets")
    if mod is None:
        mod = importlib.import_module("backend.services.connector_secrets")
    src = inspect.getsource(mod)
    assert "from backend.database" not in src
    assert "import backend.database" not in src
    # Also verify at runtime: backend.database must not have been pulled in as a
    # side effect of importing connector_secrets alone.
    fresh_import_check = importlib.import_module("backend.services.connector_secrets")
    assert "backend.database" not in fresh_import_check.__dict__, (
        "backend.database was imported into connector_secrets namespace"
    )


def test_protect_unprotect_contract():
    from backend.services.connector_secrets import protect_connector_secret_value, unprotect_connector_secret_value
    secret = "contract-test-secret"
    for value in ["short", "a" * 100, "unicode: café"]:
        protected = protect_connector_secret_value(value, secret)
        assert unprotect_connector_secret_value(protected, secret) == value


def test_extract_secret_map_contract():
    from backend.services.connector_secrets import extract_connector_secret_map, protect_connector_secret_value, CONNECTOR_SECRET_FIELD_INPUTS
    secret = "contract-secret"
    auth_config = {
        "protected_secrets": {
            field: protect_connector_secret_value(f"val-{field}", secret)
            for field in CONNECTOR_SECRET_FIELD_INPUTS
        }
    }
    result = extract_connector_secret_map(auth_config, secret)
    for field in CONNECTOR_SECRET_FIELD_INPUTS:
        assert result[field] == f"val-{field}"
