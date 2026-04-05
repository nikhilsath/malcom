"""Unit tests for connector_revoker service module."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from fastapi import HTTPException

from backend.services.connector_revoker import revoke_connector


def _make_record(
    *,
    connector_id: str = "test-connector",
    provider: str = "github",
    status: str = "connected",
    auth_config: dict | None = None,
) -> dict:
    return {
        "id": connector_id,
        "provider": provider,
        "status": status,
        "auth_config": auth_config or {},
        "name": f"{provider.title()} connector",
    }


def _make_mock_connection() -> MagicMock:
    return MagicMock()


class TestRevokeConnectorNotFound(unittest.TestCase):
    def test_raises_404_when_not_found(self) -> None:
        with patch("backend.services.connector_revoker.find_stored_connector_record", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                revoke_connector(
                    connection=_make_mock_connection(),
                    connector_id="missing",
                    protection_secret="secret",
                )
        self.assertEqual(ctx.exception.status_code, 404)


class TestRevokeConnectorGoogle(unittest.TestCase):
    def test_revokes_upstream_token_when_present(self) -> None:
        record = _make_record(provider="google")
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "ya29.real_token"}),
            patch("backend.services.connector_revoker.revoke_google_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            message, sanitized = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_called_once_with(token="ya29.real_token")
        self.assertIn("revoked", message.lower())

    def test_skips_upstream_revoke_when_token_missing(self) -> None:
        record = _make_record(provider="google")
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_revoker.revoke_google_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_not_called()

    def test_uses_refresh_token_when_access_token_absent(self) -> None:
        record = _make_record(provider="google")
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"refresh_token": "1//refresh_token"}),
            patch("backend.services.connector_revoker.revoke_google_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_called_once_with(token="1//refresh_token")


class TestRevokeConnectorGitHub(unittest.TestCase):
    def test_returns_local_clear_message(self) -> None:
        record = _make_record(provider="github")
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "ghp_token"}),
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            message, _ = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertIn("cleared locally", message)
        self.assertIn("personal access token", message)


class TestRevokeConnectorNotion(unittest.TestCase):
    def test_revokes_upstream_when_all_credentials_present(self) -> None:
        record = _make_record(
            provider="notion",
            auth_config={"client_id": "client-123"},
        )
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "ntn_token", "client_secret": "secret_abc"}),
            patch("backend.services.connector_revoker.revoke_notion_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            message, _ = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_called_once_with(token="ntn_token", client_id="client-123", client_secret="secret_abc")
        self.assertIn("revoked", message.lower())

    def test_local_only_when_missing_client_secret(self) -> None:
        record = _make_record(
            provider="notion",
            auth_config={"client_id": "client-123"},
        )
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "ntn_token"}),
            patch("backend.services.connector_revoker.revoke_notion_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            message, _ = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_not_called()
        self.assertIn("cleared locally", message)


class TestRevokeConnectorTrello(unittest.TestCase):
    def test_revokes_upstream_when_all_credentials_present(self) -> None:
        record = _make_record(
            provider="trello",
            auth_config={"client_id": "trello_key_123"},
        )
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "trello_token_abc"}),
            patch("backend.services.connector_revoker.revoke_trello_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            message, _ = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_called_once_with(token="trello_token_abc", client_id="trello_key_123")
        self.assertIn("revoked", message.lower())

    def test_local_only_when_missing_client_id(self) -> None:
        record = _make_record(provider="trello", auth_config={})
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "trello_token_abc"}),
            patch("backend.services.connector_revoker.revoke_trello_token") as mock_revoke,
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            message, _ = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        mock_revoke.assert_not_called()
        self.assertIn("cleared locally", message)


class TestRevokeConnectorCredentialClearing(unittest.TestCase):
    def test_credential_fields_are_cleared_before_save(self) -> None:
        record = _make_record(
            provider="github",
            auth_config={"client_id": "app-id"},
        )

        captured_record: dict = {}

        def capture_save(conn, rec, *, protection_secret):
            captured_record.update(rec)
            return rec

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={"access_token": "token"}),
            patch("backend.services.connector_revoker.save_connector_record", side_effect=capture_save),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        auth_config = captured_record.get("auth_config", {})
        self.assertIsNone(auth_config.get("access_token_input"))
        self.assertIsNone(auth_config.get("refresh_token_input"))
        self.assertIsNone(auth_config.get("client_secret_input"))
        self.assertIsNone(auth_config.get("api_key_input"))
        self.assertIsNone(auth_config.get("password_input"))
        self.assertIsNone(auth_config.get("header_value_input"))
        self.assertFalse(auth_config.get("has_refresh_token"))
        self.assertTrue(auth_config.get("clear_credentials"))

    def test_record_status_set_to_revoked_before_save(self) -> None:
        record = _make_record(provider="github", status="connected")

        captured_record: dict = {}

        def capture_save(conn, rec, *, protection_secret):
            captured_record.update(rec)
            return rec

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_revoker.save_connector_record", side_effect=capture_save),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertEqual(captured_record.get("status"), "revoked")

    def test_existing_auth_config_fields_are_preserved(self) -> None:
        """Non-credential fields (e.g. client_id) should survive the merge."""
        record = _make_record(
            provider="github",
            auth_config={"client_id": "app-id", "redirect_uri": "https://example.com/cb"},
        )

        captured_record: dict = {}

        def capture_save(conn, rec, *, protection_secret):
            captured_record.update(rec)
            return rec

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_revoker.save_connector_record", side_effect=capture_save),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector"}),
        ):
            revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        auth_config = captured_record.get("auth_config", {})
        self.assertEqual(auth_config.get("client_id"), "app-id")
        self.assertEqual(auth_config.get("redirect_uri"), "https://example.com/cb")


class TestRevokeConnectorReturnValue(unittest.TestCase):
    def test_returns_message_and_sanitized_dict(self) -> None:
        record = _make_record(provider="github")
        saved = {**record}

        with (
            patch("backend.services.connector_revoker.find_stored_connector_record", return_value=record),
            patch("backend.services.connector_revoker.extract_connector_secret_map", return_value={}),
            patch("backend.services.connector_revoker.save_connector_record", return_value=saved),
            patch("backend.services.connector_revoker.sanitize_connector_record_for_response", return_value={"id": "test-connector", "status": "revoked"}),
        ):
            result = revoke_connector(
                connection=_make_mock_connection(),
                connector_id="test-connector",
                protection_secret="secret",
            )

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        message, sanitized = result
        self.assertIsInstance(message, str)
        self.assertIsInstance(sanitized, dict)
        self.assertEqual(sanitized["id"], "test-connector")


if __name__ == "__main__":
    unittest.main()
