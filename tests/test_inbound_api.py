from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import INBOUND_SECRET_BYTES, INBOUND_SECRET_PREFIX, app, generate_secret
from backend.runtime import runtime_event_bus
from tests.postgres_test_utils import setup_postgres_test_app


class InboundApiTestCase(unittest.TestCase):
    def wait_for_runtime_history(self, expected_count: int) -> list[dict]:
        deadline = time.time() + 3
        while time.time() < deadline:
            history = self.client.get("/api/v1/runtime/triggers").json()
            if len(history) >= expected_count:
                return history
            time.sleep(0.05)
        self.fail("Timed out waiting for runtime trigger history.")

    def assert_secret_format(self, secret: str) -> None:
        self.assertTrue(secret.startswith(INBOUND_SECRET_PREFIX))
        payload = secret.removeprefix(INBOUND_SECRET_PREFIX)
        self.assertRegex(payload, r"^[A-Za-z0-9_-]+$")
        expected_payload_length = ((INBOUND_SECRET_BYTES + 2) // 3) * 4
        expected_payload_length -= (3 - (INBOUND_SECRET_BYTES % 3)) % 3
        self.assertEqual(len(payload), expected_payload_length)

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        setup_postgres_test_app(app=app, root_dir=root_dir)
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
        self.assert_secret_format(created["secret"])

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
        self.assertNotIn("secret", detail)
        self.assertEqual(detail["events"][0]["status"], "accepted")
        self.assertEqual(detail["events"][0]["payload_json"]["order_id"], 42)

        listed = self.client.get("/api/v1/inbound").json()
        self.assertEqual(len(listed), 1)
        self.assertNotIn("secret", listed[0])

        runtime_history = self.wait_for_runtime_history(1)
        self.assertEqual(len(runtime_history), 1)
        self.assertEqual(runtime_history[0]["api_id"], created["id"])

    def test_rotate_secret_replaces_previous_token(self) -> None:
        created = self.create_api()
        original_secret = created["secret"]

        rotate_response = self.client.post(f"/api/v1/inbound/{created['id']}/rotate-secret")
        self.assertEqual(rotate_response.status_code, 200)
        rotated = rotate_response.json()
        self.assertEqual(rotated["id"], created["id"])
        self.assertNotEqual(rotated["secret"], original_secret)
        self.assert_secret_format(rotated["secret"])

        old_secret_response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": f"Bearer {original_secret}",
                "Content-Type": "application/json",
            },
            json={"order_id": 42},
        )
        self.assertEqual(old_secret_response.status_code, 401)

        new_secret_response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": f"Bearer {rotated['secret']}",
                "Content-Type": "application/json",
            },
            json={"order_id": 84},
        )
        self.assertEqual(new_secret_response.status_code, 202)

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

    def test_generate_secret_uses_expected_format(self) -> None:
        first = generate_secret()
        second = generate_secret()

        self.assert_secret_format(first)
        self.assert_secret_format(second)
        self.assertNotEqual(first, second)

    def test_backend_writes_rotating_log_file_and_applies_size_setting(self) -> None:
        patch_response = self.client.patch(
            "/api/v1/settings",
            json={
                "logging": {
                    "max_stored_entries": 250,
                    "max_visible_entries": 50,
                    "max_detail_characters": 4000,
                    "max_file_size_mb": 7,
                }
            },
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(app.state.log_handler.maxBytes, 7 * 1024 * 1024)

        created = self.create_api()
        response = self.client.post(
            f"/api/v1/inbound/{created['id']}",
            headers={
                "Authorization": f"Bearer {created['secret']}",
                "Content-Type": "application/json",
                "X-Request-Id": "req-test-logging-001",
            },
            json={"order_id": 99},
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.headers.get("x-request-id"), "req-test-logging-001")

        log_path = Path(app.state.log_file_path)
        self.assertTrue(log_path.exists())
        self.wait_for_runtime_history(1)
        contents = log_path.read_text(encoding="utf-8")
        self.assertIn("http_request_completed", contents)
        self.assertIn("runtime_trigger_emitted", contents)
        self.assertIn("inbound_api_event_recorded", contents)
        self.assertIn(f'\"api_id\": \"{created["id"]}\"', contents)
        self.assertIn('\"event\": \"runtime_trigger_emitted\"', contents)
        self.assertIn('\"request_id\": \"req-test-logging-001\"', contents)
        self.assertIn("\"user_agent\": \"testclient\"", contents)


if __name__ == "__main__":
    unittest.main()
