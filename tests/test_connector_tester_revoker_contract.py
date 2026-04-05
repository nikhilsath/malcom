"""Contract tests: route→service boundary for connector test/revoke endpoints.

These tests verify that:
1. The route delegates to the service function (not to provider-specific probes).
2. The route shapes the service return value into a ConnectorActionResponse.
3. No provider-specific logic exists in the route module.
"""
from __future__ import annotations

import importlib
import inspect
import unittest
from unittest.mock import patch

import backend.routes.connectors as routes_module


class TestRouteConnectorBoundary(unittest.TestCase):
    """Structural contract: routes must not import provider-specific functions."""

    def test_route_does_not_import_provider_probe_functions(self) -> None:
        """Provider probe functions must live in services, not imported by routes."""
        probe_names = {
            "_probe_google_access_token",
            "_probe_github_access_token",
            "_probe_notion_access_token",
            "_probe_trello_credentials",
        }
        route_attrs = set(dir(routes_module))
        for probe in probe_names:
            self.assertNotIn(
                probe,
                route_attrs,
                msg=f"Route module must not expose {probe!r}; it belongs in a service.",
            )

    def test_route_does_not_import_upstream_revoke_functions(self) -> None:
        """Provider-specific revoke functions must not be imported by routes."""
        revoke_names = {
            "revoke_google_token",
            "revoke_notion_token",
            "revoke_trello_token",
        }
        route_attrs = set(dir(routes_module))
        for name in revoke_names:
            self.assertNotIn(
                name,
                route_attrs,
                msg=f"Route module must not expose {name!r}; it belongs in connector_revoker.",
            )

    def test_route_imports_service_test_connector(self) -> None:
        """Routes must import service_test_connector as the delegation target."""
        self.assertTrue(
            hasattr(routes_module, "service_test_connector"),
            "routes/connectors.py must expose service_test_connector (imported from connector_tester).",
        )

    def test_route_imports_service_revoke_connector(self) -> None:
        """Routes must import service_revoke_connector as the delegation target."""
        self.assertTrue(
            hasattr(routes_module, "service_revoke_connector"),
            "routes/connectors.py must expose service_revoke_connector (imported from connector_revoker).",
        )


class TestTestConnectorRouteContract(unittest.TestCase):
    """Contract: POST /test delegates entirely to service_test_connector."""

    def test_route_calls_service_once(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                # Create a connector first
                client.post(
                    "/api/v1/connectors",
                    json={
                        "id": "gh-contract-test",
                        "provider": "github",
                        "name": "GitHub",
                        "status": "draft",
                        "auth_type": "bearer",
                        "auth_config": {"access_token_input": "token_fixture"},
                    },
                )

                call_count = 0
                original_service = routes_module.service_test_connector

                def patched_service(**kwargs):
                    nonlocal call_count
                    call_count += 1
                    return original_service(**kwargs)

                with patch.object(routes_module, "service_test_connector", side_effect=patched_service):
                    response = client.post("/api/v1/connectors/gh-contract-test/test")

            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(call_count, 1, "Route must call service_test_connector exactly once per request.")
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()

    def test_route_returns_action_response_shape(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                client.post(
                    "/api/v1/connectors",
                    json={
                        "id": "gh-shape-test",
                        "provider": "github",
                        "name": "GitHub",
                        "status": "draft",
                        "auth_type": "bearer",
                        "auth_config": {"access_token_input": "token_fixture"},
                    },
                )
                response = client.post("/api/v1/connectors/gh-shape-test/test")

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertIn("ok", body)
            self.assertIn("message", body)
            self.assertIn("connector", body)
            self.assertIsInstance(body["ok"], bool)
            self.assertIsInstance(body["message"], str)
            self.assertIsInstance(body["connector"], dict)
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()

    def test_route_returns_404_when_connector_missing(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                response = client.post("/api/v1/connectors/does-not-exist/test")

            self.assertEqual(response.status_code, 404, response.text)
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()


class TestRevokeConnectorRouteContract(unittest.TestCase):
    """Contract: POST /revoke delegates entirely to service_revoke_connector."""

    def test_route_calls_service_once(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                client.post(
                    "/api/v1/connectors",
                    json={
                        "id": "gh-revoke-contract",
                        "provider": "github",
                        "name": "GitHub",
                        "status": "connected",
                        "auth_type": "bearer",
                        "auth_config": {"access_token_input": "token_fixture"},
                    },
                )

                call_count = 0
                original_service = routes_module.service_revoke_connector

                def patched_service(**kwargs):
                    nonlocal call_count
                    call_count += 1
                    return original_service(**kwargs)

                with patch.object(routes_module, "service_revoke_connector", side_effect=patched_service):
                    response = client.post("/api/v1/connectors/gh-revoke-contract/revoke")

            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(call_count, 1, "Route must call service_revoke_connector exactly once per request.")
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()

    def test_route_returns_action_response_shape_with_ok_true(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                client.post(
                    "/api/v1/connectors",
                    json={
                        "id": "gh-revoke-shape",
                        "provider": "github",
                        "name": "GitHub",
                        "status": "connected",
                        "auth_type": "bearer",
                        "auth_config": {"access_token_input": "token_fixture"},
                    },
                )
                response = client.post("/api/v1/connectors/gh-revoke-shape/revoke")

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertIn("ok", body)
            self.assertIn("message", body)
            self.assertIn("connector", body)
            self.assertTrue(body["ok"], "Revoke route must always return ok=True.")
            self.assertIsInstance(body["message"], str)
            self.assertIsInstance(body["connector"], dict)
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()

    def test_route_returns_revoked_status_on_connector(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                client.post(
                    "/api/v1/connectors",
                    json={
                        "id": "gh-revoke-status",
                        "provider": "github",
                        "name": "GitHub",
                        "status": "connected",
                        "auth_type": "bearer",
                        "auth_config": {"access_token_input": "token_fixture"},
                    },
                )
                response = client.post("/api/v1/connectors/gh-revoke-status/revoke")

            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["connector"]["status"], "revoked")
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()

    def test_route_returns_404_when_connector_missing(self) -> None:
        import tempfile
        from pathlib import Path
        from fastapi.testclient import TestClient
        from backend.main import app
        from tests.postgres_test_utils import setup_postgres_test_app

        tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        try:
            setup_postgres_test_app(app=app, root_dir=root_dir)
            client = TestClient(app)
            with client:
                response = client.post("/api/v1/connectors/does-not-exist/revoke")

            self.assertEqual(response.status_code, 404, response.text)
        except unittest.SkipTest:
            raise
        finally:
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
