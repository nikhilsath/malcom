"""Service-level unit tests for connector health probe helpers."""
from __future__ import annotations

import json
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import Mock, patch

from fastapi import HTTPException

from backend.services.connector_health import (
    _google_probe_failure_message,
    _inspect_github_scopes_from_payload,
    _probe_github_access_token,
    _probe_google_access_token,
    _probe_notion_access_token,
    _probe_trello_credentials,
)


class GoogleProbeFailureMessageTest(unittest.TestCase):
    def test_invalid_token_message(self) -> None:
        msg = _google_probe_failure_message("invalid_token: token has been revoked")
        self.assertIn("invalid or revoked", msg)

    def test_expired_message(self) -> None:
        msg = _google_probe_failure_message("token expired")
        self.assertIn("expired", msg)

    def test_scope_message(self) -> None:
        msg = _google_probe_failure_message("insufficient scope")
        self.assertIn("scopes", msg)

    def test_generic_message(self) -> None:
        msg = _google_probe_failure_message("Something went wrong.")
        self.assertIn("Reconnect Google", msg)
        self.assertIn("Something went wrong.", msg)


class ProbeGoogleAccessTokenTest(unittest.TestCase):
    def test_token_prefix_skips_network(self) -> None:
        ok, message = _probe_google_access_token(access_token="token_test_value")
        self.assertTrue(ok)
        self.assertEqual(message, "Google connection verified.")

    def test_valid_token_returns_verified(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"aud": "client-id-123"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message = _probe_google_access_token(access_token="ya29.real_token")

        self.assertTrue(ok)
        self.assertEqual(message, "Google connection verified.")

    def test_http_error_invalid_token(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/tokeninfo?access_token=x",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":"invalid_token"}'),
        )

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=http_error):
            ok, message = _probe_google_access_token(access_token="bad-token")

        self.assertFalse(ok)
        self.assertIn("invalid or revoked", message)

    def test_http_error_expired_token(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/tokeninfo?access_token=x",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":"expired token"}'),
        )

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=http_error):
            ok, message = _probe_google_access_token(access_token="expired-token")

        self.assertFalse(ok)
        self.assertIn("expired", message)

    def test_url_error_raises_http_exception(self) -> None:
        url_error = urllib.error.URLError(reason="Name or service not known")

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=url_error):
            with self.assertRaises(HTTPException) as ctx:
                _probe_google_access_token(access_token="some-token")

        self.assertEqual(ctx.exception.status_code, 502)

    def test_invalid_aud_returns_failure(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"something": "else"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message = _probe_google_access_token(access_token="ya29.bad_payload")

        self.assertFalse(ok)
        self.assertIn("expected connector details", message)


class ProbeGithubAccessTokenTest(unittest.TestCase):
    def test_gho_prefix_skips_network(self) -> None:
        ok, message, scopes = _probe_github_access_token(access_token="gho_oauth_token")
        self.assertTrue(ok)
        self.assertEqual(message, "GitHub connection verified.")
        self.assertEqual(scopes, [])

    def test_token_prefix_skips_network_with_repo_scope(self) -> None:
        ok, message, scopes = _probe_github_access_token(access_token="token_fixture")
        self.assertTrue(ok)
        self.assertEqual(message, "GitHub connection verified.")
        self.assertEqual(scopes, ["repo"])

    def test_valid_token_detects_scopes(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"login": "octocat"}).encode("utf-8")
        mock_response.headers = {"X-OAuth-Scopes": "repo, workflow, read:user"}
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message, scopes = _probe_github_access_token(access_token="ghp_real_token")

        self.assertTrue(ok)
        self.assertEqual(message, "GitHub connection verified.")
        self.assertEqual(scopes, ["read:user", "repo", "workflow"])

    def test_http_error_bad_credentials(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://api.github.com/user",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"message":"Bad credentials"}'),
        )

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=http_error):
            ok, message, scopes = _probe_github_access_token(access_token="bad-token")

        self.assertFalse(ok)
        self.assertIn("invalid or revoked", message)
        self.assertEqual(scopes, [])

    def test_url_error_raises_http_exception(self) -> None:
        url_error = urllib.error.URLError(reason="Connection refused")

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=url_error):
            with self.assertRaises(HTTPException) as ctx:
                _probe_github_access_token(access_token="ghp_some_token")

        self.assertEqual(ctx.exception.status_code, 502)

    def test_invalid_login_field_returns_failure(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"id": 123}).encode("utf-8")
        mock_response.headers = {"X-OAuth-Scopes": ""}
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message, scopes = _probe_github_access_token(access_token="ghp_bad_payload")

        self.assertFalse(ok)
        self.assertIn("expected account details", message)


class InspectGithubScopesFromPayloadTest(unittest.TestCase):
    def test_non_github_provider_passthrough(self) -> None:
        changes = {"name": "Google"}
        result = _inspect_github_scopes_from_payload(provider="google", changes=changes)
        self.assertIs(result, changes)

    def test_no_auth_config_passthrough(self) -> None:
        changes = {"provider": "github", "name": "GitHub"}
        result = _inspect_github_scopes_from_payload(provider="github", changes=changes)
        self.assertEqual(result, changes)

    def test_no_access_token_input_passthrough(self) -> None:
        changes = {"provider": "github", "auth_config": {}}
        result = _inspect_github_scopes_from_payload(provider="github", changes=changes)
        self.assertEqual(result, changes)

    def test_token_prefix_sets_scopes_and_status(self) -> None:
        changes = {
            "auth_config": {"access_token_input": "token_fixture"},
            "scopes": ["admin:org"],
        }
        result = _inspect_github_scopes_from_payload(provider="github", changes=changes)
        self.assertEqual(result["scopes"], ["repo"])
        self.assertEqual(result["status"], "connected")

    def test_offline_http_exception_allows_saving(self) -> None:
        url_error = urllib.error.URLError(reason="Network unreachable")

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=url_error):
            changes = {
                "auth_config": {"access_token_input": "ghp_offline_token"},
                "scopes": ["repo"],
            }
            result = _inspect_github_scopes_from_payload(provider="github", changes=changes)

        # Should return original changes (saving is allowed offline)
        self.assertNotIn("status", result)


class ProbeNotionAccessTokenTest(unittest.TestCase):
    def test_ntn_prefix_skips_network(self) -> None:
        ok, message = _probe_notion_access_token(access_token="ntn_abc123")
        self.assertTrue(ok)
        self.assertEqual(message, "Notion connection verified.")

    def test_secret_prefix_skips_network(self) -> None:
        ok, message = _probe_notion_access_token(access_token="secret_abc123")
        self.assertTrue(ok)
        self.assertEqual(message, "Notion connection verified.")

    def test_valid_token_returns_verified(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"object": "user", "id": "user-id"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message = _probe_notion_access_token(access_token="real_notion_token")

        self.assertTrue(ok)
        self.assertEqual(message, "Notion connection verified.")

    def test_http_error_unauthorized(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://api.notion.com/v1/users/me",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"object":"error","status":401,"code":"unauthorized","message":"API token is invalid."}'),
        )

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=http_error):
            ok, message = _probe_notion_access_token(access_token="bad-notion-token")

        self.assertFalse(ok)
        self.assertIn("invalid or revoked", message)

    def test_url_error_raises_http_exception(self) -> None:
        url_error = urllib.error.URLError(reason="Network unreachable")

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=url_error):
            with self.assertRaises(HTTPException) as ctx:
                _probe_notion_access_token(access_token="some-token")

        self.assertEqual(ctx.exception.status_code, 502)

    def test_unexpected_payload_returns_failure(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"object": "workspace"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message = _probe_notion_access_token(access_token="bad-payload-token")

        self.assertFalse(ok)
        self.assertIn("expected workspace details", message)


class ProbeTrelloCredentialsTest(unittest.TestCase):
    def test_trello_key_prefix_skips_network(self) -> None:
        ok, message = _probe_trello_credentials(api_key="trello_key_123", token="some_token")
        self.assertTrue(ok)
        self.assertEqual(message, "Trello connection verified.")

    def test_trello_token_prefix_skips_network(self) -> None:
        ok, message = _probe_trello_credentials(api_key="real_key", token="trello_token_123")
        self.assertTrue(ok)
        self.assertEqual(message, "Trello connection verified.")

    def test_token_prefix_skips_network(self) -> None:
        ok, message = _probe_trello_credentials(api_key="real_key", token="token_fixture")
        self.assertTrue(ok)
        self.assertEqual(message, "Trello connection verified.")

    def test_valid_credentials_return_verified(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"id": "member-id", "username": "user"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message = _probe_trello_credentials(api_key="real_key", token="real_token")

        self.assertTrue(ok)
        self.assertEqual(message, "Trello connection verified.")

    def test_http_error_invalid_credentials(self) -> None:
        http_error = urllib.error.HTTPError(
            url="https://api.trello.com/1/members/me",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b"invalid key"),
        )

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=http_error):
            ok, message = _probe_trello_credentials(api_key="bad_key", token="bad_token")

        self.assertFalse(ok)
        self.assertIn("Save new Trello credentials", message)

    def test_url_error_raises_http_exception(self) -> None:
        url_error = urllib.error.URLError(reason="Network unreachable")

        with patch("backend.services.connector_health.urllib.request.urlopen", side_effect=url_error):
            with self.assertRaises(HTTPException) as ctx:
                _probe_trello_credentials(api_key="real_key", token="real_token")

        self.assertEqual(ctx.exception.status_code, 502)

    def test_missing_id_in_payload_returns_failure(self) -> None:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"username": "user"}).encode("utf-8")
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=mock_response)
        ctx.__exit__ = Mock(return_value=False)

        with patch("backend.services.connector_health.urllib.request.urlopen", return_value=ctx):
            ok, message = _probe_trello_credentials(api_key="real_key", token="real_token")

        self.assertFalse(ok)
        self.assertIn("expected member details", message)


if __name__ == "__main__":
    unittest.main()
