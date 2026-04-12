"""Tests for the connector OAuth service module."""
from __future__ import annotations

import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend.services.connector_oauth import (
    start_connector_oauth,
    complete_connector_oauth,
    refresh_oauth_token,
)
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app
from backend.main import app


class ConnectorOAuthServiceTestCase(unittest.TestCase):
    """Service-level tests for OAuth orchestration without HTTP route dispatch."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(root_dir)
        database_url = setup_postgres_test_app(app=app, root_dir=root_dir)
        self._test_app = app
        self.root_dir = str(root_dir)
        # Get a test database connection from the app
        from backend.database import connect
        self.connection = connect(database_url=database_url)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_start_connector_oauth_creates_oauth_state(self) -> None:
        """Test that starting OAuth flow creates state and pending connector record."""
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        response = start_connector_oauth(
            provider="google",
            connector_id="google-test",
            name="Test Google",
            owner="TestUser",
            client_id="test-client-id",
            client_secret_input="test-client-secret",
            redirect_uri="http://localhost/callback",
            scopes=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Verify response structure
        self.assertIsNotNone(response.state)
        self.assertIsNotNone(response.authorization_url)
        self.assertIn("accounts.google.com", response.authorization_url)
        self.assertEqual(response.connector.status, "pending_oauth")
        self.assertEqual(response.code_challenge_method, "S256")

        # Verify state was stored
        self.assertIn(response.state, oauth_states_dict)
        state_payload = oauth_states_dict[response.state]
        self.assertEqual(state_payload["provider"], "google")
        self.assertEqual(state_payload["connector_id"], "google-test")
        self.assertIn("code_verifier", state_payload)
        self.assertIn("expires_at", state_payload)

    def test_start_connector_oauth_requires_client_id(self) -> None:
        """Test that OAuth start requires a client ID (env or provided)."""
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        with patch.dict("os.environ", {"MALCOM_GOOGLE_OAUTH_CLIENT_ID": ""}, clear=False):
            with self.assertRaises(HTTPException) as ctx:
                start_connector_oauth(
                    provider="google",
                    connector_id="google-test",
                    name="Test Google",
                    owner="TestUser",
                    client_id=None,  # No client ID provided
                    client_secret_input="test-client-secret",
                    redirect_uri="http://localhost/callback",
                    scopes=None,
                    connection=self.connection,
                    root_dir=self.root_dir,
                    protection_secret=protection_secret,
                    oauth_states_dict=oauth_states_dict,
                )
            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("client_id is required", ctx.exception.detail)

    def test_start_connector_oauth_rejects_github_for_pat_contract(self) -> None:
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        with self.assertRaises(HTTPException) as ctx:
            start_connector_oauth(
                provider="github",
                connector_id="github-env-test",
                name="Test GitHub",
                owner="TestUser",
                client_id=None,
                client_secret_input="",
                redirect_uri="http://localhost/callback",
                scopes=["repo", "read:user"],
                connection=self.connection,
                root_dir=self.root_dir,
                protection_secret=protection_secret,
                oauth_states_dict=oauth_states_dict,
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(
            ctx.exception.detail,
            "GitHub uses saved credentials and does not support OAuth browser setup.",
        )

    def test_complete_trello_oauth_with_demo_code_and_refresh(self) -> None:
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        start_response = start_connector_oauth(
            provider="trello",
            connector_id="trello-test",
            name="Test Trello",
            owner="TestUser",
            client_id="trello-client-id",
            client_secret_input="trello-client-secret",
            redirect_uri="http://localhost/callback",
            scopes=["read", "write"],
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        self.assertEqual(start_response.connector.status, "pending_oauth")
        self.assertIn("auth.atlassian.com/authorize", start_response.authorization_url)
        self.assertIn("response_type=code", start_response.authorization_url)

        callback_response = complete_connector_oauth(
            provider="trello",
            state=start_response.state,
            code="demo-trello",
            error=None,
            scope=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        self.assertTrue(callback_response.ok)
        self.assertEqual(callback_response.connector.status, "connected")
        self.assertTrue(callback_response.connector.auth_config.has_refresh_token)

        success, message, sanitized = refresh_oauth_token(
            connector_id="trello-test",
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
        )

        self.assertTrue(success)
        self.assertIn("token refreshed", message)
        self.assertEqual(sanitized["status"], "connected")
        self.assertTrue(sanitized["auth_config"]["has_refresh_token"])

    def test_complete_connector_oauth_with_code_exchange(self) -> None:
        """Test completing OAuth flow with demo code exchange."""
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        # First, start the flow
        start_response = start_connector_oauth(
            provider="google",
            connector_id="google-test",
            name="Test Google",
            owner="TestUser",
            client_id="test-client-id",
            client_secret_input="test-client-secret",
            redirect_uri="http://localhost/callback",
            scopes=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Then complete the callback
        callback_response = complete_connector_oauth(
            provider="google",
            state=start_response.state,
            code="demo",  # Demo code for testing
            error=None,
            scope=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Verify response
        self.assertTrue(callback_response.ok)
        self.assertEqual(callback_response.connector.status, "connected")
        self.assertIn("authorized successfully", callback_response.message)

        # Verify state was cleaned up
        self.assertNotIn(start_response.state, oauth_states_dict)

    def test_complete_connector_oauth_with_error(self) -> None:
        """Test completing OAuth flow when authorization is denied."""
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        # Start the flow
        start_response = start_connector_oauth(
            provider="google",
            connector_id="google-test",
            name="Test Google",
            owner="TestUser",
            client_id="test-client-id",
            client_secret_input="test-client-secret",
            redirect_uri="http://localhost/callback",
            scopes=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Callback with error
        callback_response = complete_connector_oauth(
            provider="google",
            state=start_response.state,
            code=None,
            error="access_denied",
            scope=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Verify response indicates failure
        self.assertFalse(callback_response.ok)
        self.assertIn("authorization failed", callback_response.message)
        self.assertEqual(callback_response.connector.status, "needs_attention")

    def test_complete_connector_oauth_invalid_state(self) -> None:
        """Test that invalid OAuth state is rejected."""
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        with self.assertRaises(HTTPException) as ctx:
            complete_connector_oauth(
                provider="google",
                state="invalid-state",
                code="demo",
                error=None,
                scope=None,
                connection=self.connection,
                root_dir=self.root_dir,
                protection_secret=protection_secret,
                oauth_states_dict=oauth_states_dict,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid OAuth state", ctx.exception.detail)

    def test_refresh_oauth_token_with_google(self) -> None:
        """Test refreshing a Google OAuth token."""
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        oauth_states_dict = {}

        # First, complete an OAuth flow to create a connected connector
        start_response = start_connector_oauth(
            provider="google",
            connector_id="google-refresh-test",
            name="Test Google Refresh",
            owner="TestUser",
            client_id="test-client-id",
            client_secret_input="test-client-secret",
            redirect_uri="http://localhost/callback",
            scopes=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        complete_connector_oauth(
            provider="google",
            state=start_response.state,
            code="demo",
            error=None,
            scope=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Now test refresh
        success, message, sanitized = refresh_oauth_token(
            connector_id="google-refresh-test",
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
        )

        self.assertTrue(success)
        self.assertIn("token refreshed", message)
        self.assertEqual(sanitized["status"], "connected")

    def test_refresh_oauth_token_nonexistent_connector(self) -> None:
        """Test that refreshing a nonexistent connector raises error."""
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        with self.assertRaises(HTTPException) as ctx:
            refresh_oauth_token(
                connector_id="nonexistent-id",
                connection=self.connection,
                root_dir=self.root_dir,
                protection_secret=protection_secret,
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_google_token_exchange_failure_propagation(self) -> None:
        """Test that Google token exchange errors propagate from service."""
        oauth_states_dict = {}
        from backend.services.support import get_connector_protection_secret
        protection_secret = get_connector_protection_secret(root_dir=self.root_dir, db_path=":memory:")

        start_response = start_connector_oauth(
            provider="google",
            connector_id="google-failure-test",
            name="Test Google Failure",
            owner="TestUser",
            client_id="test-client-id",
            client_secret_input="test-client-secret",
            redirect_uri="http://localhost/callback",
            scopes=None,
            connection=self.connection,
            root_dir=self.root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )

        # Mock a token exchange failure
        mock_http_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/token",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=BytesIO(b'{"error":"invalid_grant"}'),
        )

        with patch("backend.services.connector_google_oauth_client.urllib.request.urlopen", side_effect=mock_http_error):
            with self.assertRaises(HTTPException) as ctx:
                complete_connector_oauth(
                    provider="google",
                    state=start_response.state,
                    code="invalid_code",
                    error=None,
                    scope=None,
                    connection=self.connection,
                    root_dir=self.root_dir,
                    protection_secret=protection_secret,
                    oauth_states_dict=oauth_states_dict,
                )
            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("token exchange failed", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
