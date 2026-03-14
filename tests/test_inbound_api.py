from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.runtime import runtime_event_bus


class InboundApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        app.state.db_path = str(Path(self.tempdir.name) / "malcom-test.db")
        runtime_event_bus.clear()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def create_api(self) -> dict:
        response = self.client.post(
            "/api/v1/inbound",
            json={
                "name": "Orders Webhook",
                "description": "Receives order events.",
                "path_slug": "orders-webhook",
                "enabled": True,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_and_receive_inbound_event(self) -> None:
        created = self.create_api()

        response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": f"Bearer {created['secret']}",
                "Content-Type": "application/json",
            },
            json={"order_id": 42},
        )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["trigger"]["type"], "inbound_api")

        detail = self.client.get(f"/api/v1/inbound/{created['id']}").json()
        self.assertEqual(detail["events"][0]["status"], "accepted")
        self.assertEqual(detail["events"][0]["payload_json"]["order_id"], 42)

        runtime_history = self.client.get("/api/v1/runtime/triggers").json()
        self.assertEqual(len(runtime_history), 1)
        self.assertEqual(runtime_history[0]["api_id"], created["id"])

    def test_rejects_invalid_token(self) -> None:
        created = self.create_api()

        response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": "Bearer wrong-token",
                "Content-Type": "application/json",
            },
            json={"order_id": 42},
        )

        self.assertEqual(response.status_code, 401)
        detail = self.client.get(f"/api/v1/inbound/{created['id']}").json()
        self.assertEqual(detail["events"][0]["status"], "unauthorized")

    def test_rejects_disabled_endpoint(self) -> None:
        created = self.create_api()
        disable_response = self.client.post(f"/api/v1/inbound/{created['id']}/disable")
        self.assertEqual(disable_response.status_code, 200)

        response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": f"Bearer {created['secret']}",
                "Content-Type": "application/json",
            },
            json={"order_id": 42},
        )
        self.assertEqual(response.status_code, 409)

    def test_rejects_invalid_json_and_media_type(self) -> None:
        created = self.create_api()

        media_type_response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={"Authorization": f"Bearer {created['secret']}"},
            content="plain text",
        )
        self.assertEqual(media_type_response.status_code, 415)

        invalid_json_response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": f"Bearer {created['secret']}",
                "Content-Type": "application/json",
            },
            content="{not-valid-json}",
        )
        self.assertEqual(invalid_json_response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
