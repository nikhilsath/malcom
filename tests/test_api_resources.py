from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class ApiResourcesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        app.state.db_path = str(Path(self.tempdir.name) / "malcom-test.db")
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_create_routes_each_type_to_its_table(self) -> None:
        resources = [
            ("incoming", "/api/v1/outgoing/scheduled", "/api/v1/inbound"),
            ("outgoing_scheduled", "/api/v1/outgoing/scheduled", "/api/v1/apis"),
            ("outgoing_continuous", "/api/v1/outgoing/continuous", "/api/v1/apis"),
            ("webhook", "/api/v1/webhooks", "/api/v1/apis"),
        ]

        for resource_type, list_path, create_path in resources:
            response = self.client.post(
                create_path,
                json={
                    "type": resource_type,
                    "name": f"{resource_type} api",
                    "description": "Created during test.",
                    "path_slug": resource_type.replace("_", "-"),
                    "enabled": True,
                } if resource_type != "incoming" else {
                    "name": "incoming api",
                    "description": "Created during test.",
                    "path_slug": "incoming",
                    "enabled": True,
                },
            )
            self.assertEqual(response.status_code, 201)

            if resource_type == "incoming":
                incoming_list = self.client.get("/api/v1/inbound")
                self.assertEqual(incoming_list.status_code, 200)
                self.assertEqual(len(incoming_list.json()), 1)
                continue

            list_response = self.client.get(list_path)
            self.assertEqual(list_response.status_code, 200)
            items = list_response.json()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["type"], resource_type)

    def test_mock_resources_are_visible_only_in_developer_mode(self) -> None:
        scheduled_response = self.client.get("/api/v1/outgoing/scheduled")
        continuous_response = self.client.get("/api/v1/outgoing/continuous")
        webhook_response = self.client.get("/api/v1/webhooks")

        self.assertEqual(scheduled_response.status_code, 200)
        self.assertEqual(continuous_response.status_code, 200)
        self.assertEqual(webhook_response.status_code, 200)
        self.assertEqual(scheduled_response.json(), [])
        self.assertEqual(continuous_response.json(), [])
        self.assertEqual(webhook_response.json(), [])

        developer_headers = {"X-Developer-Mode": "true"}
        scheduled_response = self.client.get("/api/v1/outgoing/scheduled", headers=developer_headers)
        continuous_response = self.client.get("/api/v1/outgoing/continuous", headers=developer_headers)
        webhook_response = self.client.get("/api/v1/webhooks", headers=developer_headers)

        self.assertEqual(scheduled_response.status_code, 200)
        self.assertEqual(continuous_response.status_code, 200)
        self.assertEqual(webhook_response.status_code, 200)
        self.assertEqual(scheduled_response.json()[0]["id"], "scheduled_demo_push")
        self.assertEqual(continuous_response.json()[0]["id"], "continuous_demo_stream")
        self.assertEqual(webhook_response.json()[0]["id"], "webhook_demo_registry")


if __name__ == "__main__":
    unittest.main()
