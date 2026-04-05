"""Unit tests for connector_tester service module."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend.services.connector_tester import test_connector


def _make_record(
    *,
    connector_id: str = "test-connector",
    provider: str = "github",
    status: str = "draft",
    auth_type: str = "bearer",
    auth_config: dict | None = None,
    scopes: list[str] | None = None,
) -> dict:
    return {
        "id": connector_id,
        "provider": provider,
        "status": status,
        "auth_type": auth_type,
        "auth_config": auth_config or {},
        "scopes": scopes or [],
        "name": f"{provider.title()} connector",
    }


def _make_mock_connection() -> MagicMock:
    return MagicMock()


class TestTestConnectorNotFound(unittest.TestCase):
    def test_raises_404_when_not_found(self) -> None:
        conn = _make_mock_connection()
        with patch("backend.services.connector_tester.find_stored_connector_record", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                test_connector(connection=conn, connector_id="missing", protection_secret="secret")
        self.assertEqual(ctx.exception.status_code, 404)


class TestTestConnectorRevoked(unittest.TestCase):
    def test_revoked_connector_returns_not_ok(self) -> None:
        record = _make_record(status="revoked")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, sanitized = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("revoked", message.lower())


class TestTestConnectorExpired(unittest.TestCase):
    def test_expired_token_returns_not_ok(self) -> None:
        from datetime import UTC, datetime, timedelta
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        record = _make_record(
            provider="google",
            status="connected",
            auth_config={"expires_at": past},
        )
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, sanitized = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("expired", message.lower())


class TestTestConnectorGoogle(unittest.TestCase):
    def test_missing_access_token_returns_needs_attention(self) -> None:
        record = _make_record(provider="google", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, sanitized = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("missing an access token", message)

    def test_valid_access_token_returns_ok(self) -> None:
        record = _make_record(provider="google", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"access_token": "token_test"}),
            patch("backend.services.connector_tester._probe_google_access_token", return_value=(True, "Google connection verified.")),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, sanitized = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertTrue(ok)
        self.assertIn("verified", message)

    def test_probe_failure_returns_not_ok(self) -> None:
        record = _make_record(provider="google", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"access_token": "ya29.bad"}),
            patch("backend.services.connector_tester._probe_google_access_token", return_value=(False, "Google rejected the saved access token.")),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("Google rejected", message)


class TestTestConnectorGithub(unittest.TestCase):
    def test_missing_access_token_returns_needs_attention(self) -> None:
        record = _make_record(provider="github", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("missing an access token", message)

    def test_valid_access_token_returns_ok_and_sets_scopes(self) -> None:
        record = _make_record(provider="github", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"access_token": "token_fixture"}),
            patch("backend.services.connector_tester._probe_github_access_token", return_value=(True, "GitHub connection verified.", ["repo", "workflow"])),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertTrue(ok)
        # scopes should be set on the record before saving
        self.assertEqual(record.get("scopes"), ["repo", "workflow"])

    def test_probe_failure_sets_needs_attention(self) -> None:
        record = _make_record(provider="github", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"access_token": "ghp_bad"}),
            patch("backend.services.connector_tester._probe_github_access_token", return_value=(False, "GitHub rejected the saved access token.", [])),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)


class TestTestConnectorNotion(unittest.TestCase):
    def test_missing_access_token(self) -> None:
        record = _make_record(provider="notion", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("missing an access token", message)

    def test_valid_access_token_returns_ok(self) -> None:
        record = _make_record(provider="notion", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"access_token": "ntn_token"}),
            patch("backend.services.connector_tester._probe_notion_access_token", return_value=(True, "Notion connection verified.")),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertTrue(ok)


class TestTestConnectorTrello(unittest.TestCase):
    def test_missing_credentials(self) -> None:
        record = _make_record(provider="trello", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("client ID or access token", message)

    def test_valid_credentials_return_ok(self) -> None:
        record = _make_record(provider="trello", status="connected")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"api_key": "trello_key_123", "access_token": "trello_token_abc"}),
            patch("backend.services.connector_tester._probe_trello_credentials", return_value=(True, "Trello connection verified.")),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertTrue(ok)
        self.assertIn("verified", message)


class TestTestConnectorGenericFallback(unittest.TestCase):
    def test_generic_with_credentials_returns_ok(self) -> None:
        record = _make_record(provider="custom", status="draft", auth_type="api_key")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={"api_key": "some-key"}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertTrue(ok)
        self.assertIn("look complete", message)

    def test_generic_without_credentials_returns_needs_attention(self) -> None:
        record = _make_record(provider="custom", status="draft")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertFalse(ok)
        self.assertIn("missing credential", message)

    def test_oauth2_auth_type_returns_ok(self) -> None:
        record = _make_record(provider="custom", status="connected", auth_type="oauth2")
        saved = {**record}

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", return_value=saved),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            ok, message, _ = test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertTrue(ok)


class TestTestConnectorTimestamps(unittest.TestCase):
    def test_timestamps_are_updated_before_save(self) -> None:
        record = _make_record(provider="github", status="connected")

        captured_record: dict = {}

        def capture_save(conn, rec, *, protection_secret):
            captured_record.update(rec)
            return rec

        with (
            patch("backend.services.connector_tester.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_tester.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_tester.save_connector_record", side_effect=capture_save),
            patch("backend.services.connector_tester.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            test_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertIn("last_tested_at", captured_record)
        self.assertIn("updated_at", captured_record)
        self.assertEqual(captured_record["last_tested_at"], captured_record["updated_at"])


if __name__ == "__main__":
    unittest.main()
