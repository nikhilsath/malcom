from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class PlatformApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        self.database_url = setup_postgres_test_app(app=app, root_dir=self.root_dir, skip_ui_build_check=True)
        self.client = TestClient(app)
        self.client.__enter__()
        self.env_patch = patch.dict(
            os.environ,
            {
                "MALCOM_FRONTEND_BOOTSTRAP_TOKEN": "platform-bootstrap-secret",
                "MALCOM_FRONTEND_HOST_URL": "https://frontend.example.test",
                "MALCOM_FRONTEND_ALLOWED_ORIGINS": "https://frontend.example.test,https://plugins.example.test",
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def _issue_tokens(self) -> dict[str, object]:
        response = self.client.post(
            "/api/v1/platform/auth/tokens",
            json={
                "bootstrap_token": "platform-bootstrap-secret",
                "operator_name": "Platform Operator",
                "client_name": "hosted-frontend",
                "requested_origin": "https://frontend.example.test",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["access_token"])
        self.assertTrue(body["refresh_token"])
        return body

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    def test_issue_bootstrap_refresh_and_revoke_frontend_tokens(self) -> None:
        issued = self._issue_tokens()

        bootstrap_response = self.client.get(
            "/api/v1/platform/bootstrap",
            headers=self._auth_headers(str(issued["access_token"])),
        )
        self.assertEqual(bootstrap_response.status_code, 200, bootstrap_response.text)
        bootstrap_body = bootstrap_response.json()
        self.assertEqual(bootstrap_body["session"]["operator_name"], "Platform Operator")
        self.assertEqual(bootstrap_body["session"]["session_type"], "hosted-frontend")
        self.assertEqual(bootstrap_body["session"]["requested_origin"], "https://frontend.example.test")
        self.assertIn("platform:read", bootstrap_body["session"]["requested_scopes"])
        self.assertTrue(bootstrap_body["capabilities"]["workflow_builder_embed"])
        self.assertEqual(bootstrap_body["frontend"]["frontend_host_url"], "https://frontend.example.test")
        self.assertEqual(bootstrap_body["frontend"]["allowed_origins"], ["https://frontend.example.test", "https://plugins.example.test"])
        self.assertEqual(bootstrap_body["auth"]["session_lifecycle"]["session_mode"], "refreshable")
        self.assertEqual(bootstrap_body["auth"]["session_lifecycle"]["rotation_strategy"], "rolling")
        self.assertEqual(
            bootstrap_body["auth"]["session_lifecycle"]["access_token_ttl_minutes"],
            bootstrap_body["auth"]["access_token_ttl_minutes"],
        )
        self.assertEqual(
            bootstrap_body["auth"]["session_lifecycle"]["refresh_token_ttl_days"],
            bootstrap_body["auth"]["refresh_token_ttl_days"],
        )
        self.assertTrue(bootstrap_body["auth"]["session_lifecycle"]["bootstrap_token_required"])

        refresh_response = self.client.post(
            "/api/v1/platform/auth/refresh",
            json={"refresh_token": issued["refresh_token"], "client_name": "hosted-frontend"},
        )
        self.assertEqual(refresh_response.status_code, 200, refresh_response.text)
        refreshed_body = refresh_response.json()
        self.assertNotEqual(refreshed_body["access_token"], issued["access_token"])
        self.assertNotEqual(refreshed_body["refresh_token"], issued["refresh_token"])

        old_bootstrap = self.client.get(
            "/api/v1/platform/bootstrap",
            headers=self._auth_headers(str(issued["access_token"])),
        )
        self.assertEqual(old_bootstrap.status_code, 401, old_bootstrap.text)

        revoke_response = self.client.post(
            "/api/v1/platform/auth/revoke",
            json={"refresh_token": refreshed_body["refresh_token"]},
        )
        self.assertEqual(revoke_response.status_code, 200, revoke_response.text)
        self.assertEqual(revoke_response.json()["session"]["status"], "revoked")

        revoked_bootstrap = self.client.get(
            "/api/v1/platform/bootstrap",
            headers=self._auth_headers(str(refreshed_body["access_token"])),
        )
        self.assertEqual(revoked_bootstrap.status_code, 401, revoked_bootstrap.text)

    def test_platform_plugins_and_embed_descriptor_are_available_without_ui_source_tree(self) -> None:
        issued = self._issue_tokens()
        self.assertFalse((self.root_dir / "app" / "ui" / "dist").exists())

        plugins_response = self.client.get(
            "/api/v1/platform/plugins",
            headers=self._auth_headers(str(issued["access_token"])),
        )
        self.assertEqual(plugins_response.status_code, 200, plugins_response.text)
        plugins_body = plugins_response.json()
        plugins_by_id = {plugin["id"]: plugin for plugin in plugins_body["plugins"]}
        self.assertEqual(
            set(plugins_by_id),
            {"dashboard", "automations", "apis", "tools", "scripts", "settings", "docs"},
        )

        for plugin_id, plugin in plugins_by_id.items():
            with self.subTest(plugin=plugin_id):
                self.assertEqual(plugin["primary_route_path"], f"/{plugin_id}")
                self.assertGreaterEqual(len(plugin["nav"]), 1)
                self.assertGreaterEqual(len(plugin["routes"]), 1)
                self.assertGreaterEqual(len(plugin["surfaces"]), 1)
                self.assertEqual(plugin["nav"][0]["route_path"], plugin["primary_route_path"])
                self.assertEqual(plugin["mount"]["regions"], ["topnav", "sidenav", "content"])
                self.assertIn(plugin["mount"]["navigation_mode"], {"plugin", "mixed"})

        dashboard_plugin = plugins_by_id["dashboard"]
        self.assertEqual(
            {route["path"] for route in dashboard_plugin["routes"]},
            {"/dashboard", "/dashboard/activity"},
        )
        self.assertEqual(
            {surface["route_path"] for surface in dashboard_plugin["surfaces"]},
            {"/dashboard", "/dashboard/activity"},
        )

        automations_plugin = plugins_by_id["automations"]
        self.assertEqual(automations_plugin["surface_group"], "workspace")
        self.assertEqual(automations_plugin["primary_route_path"], "/automations")
        self.assertEqual(automations_plugin["hosting_model"], "mixed")
        self.assertEqual(automations_plugin["metadata"]["iframe_route_count"], 1)
        self.assertIn("iframe", automations_plugin["metadata"]["route_mount_modes"])
        self.assertEqual(
            {route["path"] for route in automations_plugin["routes"]},
            {"/automations", "/automations/runs", "/automations/library", "/automations/builder"},
        )
        iframe_route = next(route for route in automations_plugin["routes"] if route["path"] == "/automations/builder")
        self.assertEqual(iframe_route["mount_mode"], "iframe")
        self.assertEqual(iframe_route["embed_id"], "workflow-builder")
        self.assertEqual(iframe_route["surface_id"], "automations-builder")

        self.assertEqual(
            {route["path"] for route in plugins_by_id["apis"]["routes"]},
            {"/apis", "/apis/inbound", "/apis/outbound", "/apis/webhooks"},
        )
        self.assertEqual(
            {route["path"] for route in plugins_by_id["tools"]["routes"]},
            {"/tools", "/tools/runtimes"},
        )
        self.assertEqual(
            {route["path"] for route in plugins_by_id["scripts"]["routes"]},
            {"/scripts", "/scripts/executions"},
        )
        self.assertEqual(
            {route["path"] for route in plugins_by_id["settings"]["routes"]},
            {"/settings", "/settings/connectors", "/settings/storage"},
        )
        self.assertEqual(
            {route["path"] for route in plugins_by_id["docs"]["routes"]},
            {"/docs", "/docs/articles"},
        )

        embed_response = self.client.get(
            "/api/v1/platform/embeds/workflow-builder",
            headers=self._auth_headers(str(issued["access_token"])),
        )
        self.assertEqual(embed_response.status_code, 200, embed_response.text)
        embed_body = embed_response.json()
        self.assertEqual(embed_body["id"], "workflow-builder")
        self.assertIn("/automations/builder.html", embed_body["src"])
        self.assertEqual(embed_body["builder_route"], "/automations/builder.html")
        self.assertEqual(embed_body["lifecycle"]["session_binding"], "platform-session")
        self.assertEqual(embed_body["lifecycle"]["compatibility_mode"], "legacy-backend-ui")
        self.assertTrue(embed_body["lifecycle"]["refreshes_session"])
        self.assertEqual(embed_body["metadata"]["compatibility_mode"], "legacy-backend-ui")


if __name__ == "__main__":
    unittest.main()
