"""Unit tests for backend.services.network."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.error
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.schemas import OutgoingAuthConfig, OutgoingWebhookSigningConfig
from backend.schemas.apis import OutgoingApiTestRequest
from backend.services.network import (
    build_outgoing_request_headers,
    execute_outgoing_test_delivery,
    header_subset,
    redact_outgoing_request_headers,
)


# ---------------------------------------------------------------------------
# header_subset
# ---------------------------------------------------------------------------

class TestHeaderSubset:
    def test_allows_content_type(self):
        result = header_subset({"Content-Type": "application/json", "X-Secret": "value"})
        assert "content-type" in result
        assert "x-secret" not in result

    def test_allows_user_agent(self):
        result = header_subset({"User-Agent": "test-agent", "Authorization": "Bearer tok"})
        assert "user-agent" in result
        assert "authorization" not in result

    def test_allows_x_request_id(self):
        result = header_subset({"X-Request-Id": "abc-123", "Cookie": "session=x"})
        assert "x-request-id" in result
        assert "cookie" not in result

    def test_returns_lowercase_keys(self):
        result = header_subset({"Content-Type": "text/plain"})
        assert "Content-Type" not in result
        assert "content-type" in result

    def test_empty_headers_returns_empty_dict(self):
        assert header_subset({}) == {}

    def test_no_allowed_headers_returns_empty_dict(self):
        result = header_subset({"Authorization": "Bearer tok", "X-Custom": "val"})
        assert result == {}

    def test_multiple_allowed_headers_all_included(self):
        result = header_subset({
            "Content-Type": "application/json",
            "User-Agent": "agent/1.0",
            "X-Request-Id": "req-99",
            "X-Extra": "ignored",
        })
        assert set(result.keys()) == {"content-type", "user-agent", "x-request-id"}


# ---------------------------------------------------------------------------
# build_outgoing_request_headers
# ---------------------------------------------------------------------------

class TestBuildOutgoingRequestHeaders:
    def test_always_includes_content_type(self):
        headers = build_outgoing_request_headers("none", None)
        assert headers["Content-Type"] == "application/json"

    def test_bearer_auth_adds_authorization_header(self):
        config = OutgoingAuthConfig(token="my-secret-token")
        headers = build_outgoing_request_headers("bearer", config)
        assert headers["Authorization"] == "Bearer my-secret-token"

    def test_bearer_auth_without_token_skips_authorization(self):
        config = OutgoingAuthConfig(token=None)
        headers = build_outgoing_request_headers("bearer", config)
        assert "Authorization" not in headers

    def test_basic_auth_adds_base64_authorization_header(self):
        config = OutgoingAuthConfig(username="user", password="pass")
        headers = build_outgoing_request_headers("basic", config)
        expected = "Basic " + base64.b64encode(b"user:pass").decode("ascii")
        assert headers["Authorization"] == expected

    def test_basic_auth_without_credentials_skips_authorization(self):
        config = OutgoingAuthConfig(username=None, password=None)
        headers = build_outgoing_request_headers("basic", config)
        assert "Authorization" not in headers

    def test_header_auth_adds_custom_header(self):
        config = OutgoingAuthConfig(header_name="X-Api-Key", header_value="abc-123")
        headers = build_outgoing_request_headers("header", config)
        assert headers["X-Api-Key"] == "abc-123"

    def test_header_auth_without_name_skips_custom_header(self):
        config = OutgoingAuthConfig(header_name=None, header_value="abc-123")
        headers = build_outgoing_request_headers("header", config)
        assert "X-Api-Key" not in headers

    def test_none_auth_type_adds_no_authorization(self):
        headers = build_outgoing_request_headers("none", None)
        assert "Authorization" not in headers

    def test_verification_token_added_when_provided(self):
        signing = OutgoingWebhookSigningConfig(verification_token="verif-tok")
        headers = build_outgoing_request_headers("none", None, webhook_signing=signing)
        assert headers["X-Malcom-Verification-Token"] == "verif-tok"

    def test_no_verification_token_when_absent(self):
        signing = OutgoingWebhookSigningConfig()
        headers = build_outgoing_request_headers("none", None, webhook_signing=signing)
        assert "X-Malcom-Verification-Token" not in headers

    def test_hmac_sha256_signing_adds_signature_header(self):
        signing = OutgoingWebhookSigningConfig(
            algorithm="hmac_sha256",
            signing_secret="my-secret",
            signature_header="X-Hub-Signature",
        )
        body = b'{"event":"test"}'
        headers = build_outgoing_request_headers("none", None, webhook_signing=signing, request_body_bytes=body)
        expected_digest = hmac.new(b"my-secret", body, hashlib.sha256).hexdigest()
        assert headers["X-Hub-Signature"] == f"sha256={expected_digest}"

    def test_hmac_signing_with_empty_body(self):
        signing = OutgoingWebhookSigningConfig(
            algorithm="hmac_sha256",
            signing_secret="secret",
            signature_header="X-Sig",
        )
        headers = build_outgoing_request_headers("none", None, webhook_signing=signing, request_body_bytes=b"")
        expected_digest = hmac.new(b"secret", b"", hashlib.sha256).hexdigest()
        assert headers["X-Sig"] == f"sha256={expected_digest}"

    def test_hmac_signing_without_secret_skips_signature(self):
        signing = OutgoingWebhookSigningConfig(
            algorithm="hmac_sha256",
            signing_secret=None,
            signature_header="X-Sig",
        )
        headers = build_outgoing_request_headers("none", None, webhook_signing=signing)
        assert "X-Sig" not in headers

    def test_null_auth_config_defaults_to_empty_config(self):
        # Passing None as auth_config should not raise
        headers = build_outgoing_request_headers("bearer", None)
        assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# redact_outgoing_request_headers
# ---------------------------------------------------------------------------

class TestRedactOutgoingRequestHeaders:
    def test_bearer_authorization_is_redacted(self):
        headers = {"Authorization": "Bearer super-secret-token"}
        redacted = redact_outgoing_request_headers(headers)
        assert redacted["Authorization"] == "Bearer [redacted]"

    def test_basic_authorization_is_redacted(self):
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        redacted = redact_outgoing_request_headers(headers)
        assert redacted["Authorization"] == "Basic [redacted]"

    def test_unknown_authorization_is_fully_redacted(self):
        headers = {"Authorization": "Token abc123"}
        redacted = redact_outgoing_request_headers(headers)
        assert redacted["Authorization"] == "[redacted]"

    def test_content_type_is_preserved(self):
        headers = {"Content-Type": "application/json", "Authorization": "Bearer tok"}
        redacted = redact_outgoing_request_headers(headers)
        assert redacted["Content-Type"] == "application/json"

    def test_custom_header_is_redacted(self):
        headers = {"X-Api-Key": "sensitive-key"}
        redacted = redact_outgoing_request_headers(headers)
        assert redacted["X-Api-Key"] == "[redacted]"

    def test_signature_header_is_redacted(self):
        headers = {"X-Hub-Signature": "sha256=abc123", "Content-Type": "application/json"}
        redacted = redact_outgoing_request_headers(headers)
        assert redacted["X-Hub-Signature"] == "[redacted]"
        assert redacted["Content-Type"] == "application/json"

    def test_empty_headers_returns_empty_dict(self):
        assert redact_outgoing_request_headers({}) == {}

    def test_all_keys_preserved_in_output(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer tok",
            "X-Custom-Header": "value",
        }
        redacted = redact_outgoing_request_headers(headers)
        assert set(redacted.keys()) == set(headers.keys())


# ---------------------------------------------------------------------------
# execute_outgoing_test_delivery
# ---------------------------------------------------------------------------

def _make_test_request(**overrides):
    defaults = dict(
        type="outgoing_scheduled",
        destination_url="https://example.com/hook",
        http_method="POST",
        payload_template='{"key": "value"}',
    )
    defaults.update(overrides)
    return OutgoingApiTestRequest(**defaults)


class _FakeHTTPResponse:
    """Minimal stand-in for urllib response object."""

    def __init__(self, status, body):
        self.status = status
        self._body = body.encode("utf-8") if isinstance(body, str) else body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestExecuteOutgoingTestDelivery:
    def test_invalid_json_payload_raises_422(self):
        request = _make_test_request(payload_template="{not valid json")
        with pytest.raises(HTTPException) as exc_info:
            execute_outgoing_test_delivery(request)
        assert exc_info.value.status_code == 422
        assert "valid JSON" in exc_info.value.detail

    def test_invalid_url_scheme_raises_422(self):
        request = _make_test_request(destination_url="ftp://example.com/hook")
        with pytest.raises(HTTPException) as exc_info:
            execute_outgoing_test_delivery(request)
        assert exc_info.value.status_code == 422
        assert "valid http or https URL" in exc_info.value.detail

    def test_missing_netloc_in_url_raises_422(self):
        request = _make_test_request(destination_url="http://")
        with pytest.raises(HTTPException) as exc_info:
            execute_outgoing_test_delivery(request)
        assert exc_info.value.status_code == 422

    def test_successful_response_returns_ok_true(self):
        fake_response = _FakeHTTPResponse(200, '{"success": true}')
        request = _make_test_request()
        with patch("urllib.request.urlopen", return_value=fake_response):
            result = execute_outgoing_test_delivery(request)
        assert result.ok is True
        assert result.status_code == 200
        assert result.destination_url == "https://example.com/hook"

    def test_successful_response_body_included(self):
        fake_response = _FakeHTTPResponse(201, "created")
        request = _make_test_request()
        with patch("urllib.request.urlopen", return_value=fake_response):
            result = execute_outgoing_test_delivery(request)
        assert result.response_body == "created"

    def test_response_body_truncated_to_2000_chars(self):
        long_body = "x" * 5000
        fake_response = _FakeHTTPResponse(200, long_body)
        request = _make_test_request()
        with patch("urllib.request.urlopen", return_value=fake_response):
            result = execute_outgoing_test_delivery(request)
        assert len(result.response_body) == 2000

    def test_http_error_returns_ok_false(self):
        error_body = b'{"error": "not found"}'
        http_err = urllib.error.HTTPError(
            url="https://example.com/hook",
            code=404,
            msg="Not Found",
            hdrs=None,  # type: ignore[arg-type]
            fp=BytesIO(error_body),
        )
        request = _make_test_request()
        with patch("urllib.request.urlopen", side_effect=http_err):
            result = execute_outgoing_test_delivery(request)
        assert result.ok is False
        assert result.status_code == 404

    def test_http_error_5xx_returns_ok_false(self):
        error_body = b"Internal Server Error"
        http_err = urllib.error.HTTPError(
            url="https://example.com/hook",
            code=500,
            msg="Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=BytesIO(error_body),
        )
        request = _make_test_request()
        with patch("urllib.request.urlopen", side_effect=http_err):
            result = execute_outgoing_test_delivery(request)
        assert result.ok is False
        assert result.status_code == 500

    def test_url_error_raises_502(self):
        url_err = urllib.error.URLError(reason="Connection refused")
        request = _make_test_request()
        with patch("urllib.request.urlopen", side_effect=url_err):
            with pytest.raises(HTTPException) as exc_info:
                execute_outgoing_test_delivery(request)
        assert exc_info.value.status_code == 502
        assert "Unable to reach destination URL" in exc_info.value.detail

    def test_sent_headers_are_redacted_in_response(self):
        fake_response = _FakeHTTPResponse(200, "ok")
        request = _make_test_request(
            auth_type="bearer",
            auth_config=OutgoingAuthConfig(token="super-secret"),
        )
        with patch("urllib.request.urlopen", return_value=fake_response):
            result = execute_outgoing_test_delivery(request)
        assert result.sent_headers.get("Authorization") == "Bearer [redacted]"

    def test_bearer_auth_included_in_request(self):
        captured = []

        def fake_urlopen(request, timeout=None):
            captured.append(request)
            return _FakeHTTPResponse(200, "ok")

        test_request = _make_test_request(
            auth_type="bearer",
            auth_config=OutgoingAuthConfig(token="my-token"),
        )
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            execute_outgoing_test_delivery(test_request)
        assert captured[0].get_header("Authorization") == "Bearer my-token"
