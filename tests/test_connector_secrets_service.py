"""Unit tests for connector_secrets module."""
from __future__ import annotations
import pytest
from backend.services.connector_secrets import (
    CONNECTOR_NONCE_BYTES,
    CONNECTOR_PROTECTION_VERSION,
    CONNECTOR_SECRET_FIELD_INPUTS,
    CONNECTOR_SIGNATURE_BYTES,
    build_connector_keystream,
    derive_connector_protection_key,
    extract_connector_secret_map,
    get_connector_protection_secret,
    mask_connector_secret,
    protect_connector_secret_value,
    unprotect_connector_secret_value,
)


def test_protection_round_trip():
    secret = "test-secret"
    value = "my-api-token"
    protected = protect_connector_secret_value(value, secret)
    assert protected.startswith(f"{CONNECTOR_PROTECTION_VERSION}:")
    recovered = unprotect_connector_secret_value(protected, secret)
    assert recovered == value


def test_protection_produces_different_ciphertext_each_call():
    secret = "test-secret"
    value = "my-api-token"
    p1 = protect_connector_secret_value(value, secret)
    p2 = protect_connector_secret_value(value, secret)
    assert p1 != p2  # different nonces


def test_unprotect_wrong_secret_returns_none():
    protected = protect_connector_secret_value("hello", "correct-secret")
    assert unprotect_connector_secret_value(protected, "wrong-secret") is None


def test_unprotect_none_returns_none():
    assert unprotect_connector_secret_value(None, "any") is None


def test_unprotect_invalid_token_returns_none():
    assert unprotect_connector_secret_value("not-a-token", "any") is None


def test_mask_short_value():
    assert mask_connector_secret("abc") == "••••"


def test_mask_long_value():
    result = mask_connector_secret("1234567890")
    assert result == "1234••••7890"


def test_mask_none_returns_none():
    assert mask_connector_secret(None) is None


def test_mask_empty_returns_none():
    assert mask_connector_secret("") is None


def test_extract_connector_secret_map_empty():
    result = extract_connector_secret_map({}, "secret")
    assert result == {}


def test_extract_connector_secret_map_with_protected_values():
    secret = "workspace-secret"
    auth_config = {
        "protected_secrets": {
            "access_token": protect_connector_secret_value("my-token", secret),
        }
    }
    result = extract_connector_secret_map(auth_config, secret)
    assert result["access_token"] == "my-token"


def test_derive_connector_protection_key_is_bytes():
    key = derive_connector_protection_key("test")
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_build_connector_keystream_length():
    key = derive_connector_protection_key("test")
    nonce = b"\x00" * CONNECTOR_NONCE_BYTES
    stream = build_connector_keystream(key, nonce, 64)
    assert len(stream) == 64


def test_get_connector_protection_secret_from_env(monkeypatch):
    monkeypatch.setenv("MALCOM_CONNECTOR_SECRET", "env-secret-value")
    assert get_connector_protection_secret() == "env-secret-value"


def test_get_connector_protection_secret_fallback(monkeypatch):
    monkeypatch.delenv("MALCOM_CONNECTOR_SECRET", raising=False)
    result = get_connector_protection_secret()
    assert "malcom-connectors" in result


def test_connector_secret_field_inputs_keys():
    expected = {"client_secret", "access_token", "refresh_token", "api_key", "password", "header_value"}
    assert set(CONNECTOR_SECRET_FIELD_INPUTS.keys()) == expected
