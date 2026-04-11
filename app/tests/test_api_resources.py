from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.support import run_scheduler_tick
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class ApiResourcesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(root_dir)
        setup_postgres_test_app(app=app, root_dir=root_dir)
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
                    "destination_url": "https://example.com/hooks/test",
                    "http_method": "POST",
                    "auth_type": "bearer",
                    "auth_config": {"token": "secret-token"},
                    "payload_template": "{\"hello\":\"world\"}",
                    "scheduled_time": "09:30",
                } if resource_type not in {"incoming", "webhook"} else {
                    "name": "incoming api",
                    "description": "Created during test.",
                    "path_slug": "incoming",
                    "enabled": True,
                } if resource_type == "incoming" else {
                    "type": "webhook",
                    "name": "webhook api",
                    "description": "Created during test.",
                    "path_slug": "webhook",
                    "enabled": True,
                    "callback_path": "/hooks/webhook",
                    "verification_token": "verify-token",
                    "signing_secret": "signing-secret",
                    "signature_header": "X-Signature",
                    "event_filter": "order.created",
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

            if resource_type.startswith("outgoing_"):
                self.assertEqual(items[0]["destination_url"], "https://example.com/hooks/test")
                self.assertEqual(items[0]["http_method"], "POST")
                self.assertEqual(items[0]["auth_type"], "bearer")
                self.assertFalse(items[0]["repeat_enabled"])

            if resource_type == "outgoing_scheduled":
                self.assertEqual(items[0]["status"], "active")
                self.assertEqual(items[0]["scheduled_time"], "09:30")
                self.assertEqual(items[0]["schedule_expression"], "30 9 * * *")
                self.assertIsNone(items[0]["repeat_interval_minutes"])

    def test_test_delivery_endpoint_sends_payload_and_auth(self) -> None:
        captured_request = {}

        class FakeResponse:
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return b'{"received":true}'

        def fake_urlopen(request, timeout=10):
            del timeout
            captured_request["authorization"] = request.headers.get("Authorization", "")
            captured_request["content_type"] = request.headers.get("Content-type", "")
            captured_request["body"] = request.data.decode("utf-8")
            captured_request["url"] = request.full_url
            return FakeResponse()

        with patch("backend.routes.apis.urllib.request.urlopen", side_effect=fake_urlopen):
            response = self.client.post(
                "/api/v1/apis/test-delivery",
                json={
                    "type": "outgoing_scheduled",
                    "destination_url": "https://example.com/deliver",
                    "http_method": "POST",
                    "auth_type": "bearer",
                    "auth_config": {"token": "live-test-token"},
                    "payload_template": "{\"ping\":\"pong\"}",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["status_code"], 200)
        self.assertEqual(captured_request["authorization"], "Bearer live-test-token")
        self.assertEqual(captured_request["content_type"], "application/json")
        self.assertEqual(captured_request["body"], "{\"ping\": \"pong\"}")
        self.assertEqual(captured_request["url"], "https://example.com/deliver")

    def test_scheduled_api_status_defaults_from_enabled_state(self) -> None:
        response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_scheduled",
                "name": "paused scheduled api",
                "description": "Created disabled during test.",
                "path_slug": "paused-scheduled-api",
                "enabled": False,
                "destination_url": "https://example.com/hooks/test",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": "{\"hello\":\"world\"}",
                "scheduled_time": "11:15",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "paused")

        list_response = self.client.get("/api/v1/outgoing/scheduled")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["status"], "paused")

    def test_outgoing_repeat_configuration_is_persisted(self) -> None:
        scheduled_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_scheduled",
                "name": "daily scheduled api",
                "description": "Repeats every day.",
                "path_slug": "daily-scheduled-api",
                "enabled": True,
                "repeat_enabled": True,
                "destination_url": "https://example.com/hooks/scheduled",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": "{\"hello\":\"world\"}",
                "scheduled_time": "08:00",
            },
        )
        self.assertEqual(scheduled_response.status_code, 201)
        self.assertTrue(scheduled_response.json()["repeat_enabled"])

        continuous_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_continuous",
                "name": "repeating continuous api",
                "description": "Repeats every 15 minutes.",
                "path_slug": "repeating-continuous-api",
                "enabled": True,
                "repeat_enabled": True,
                "repeat_interval_minutes": 15,
                "destination_url": "https://example.com/hooks/continuous",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": "{\"hello\":\"world\"}",
            },
        )
        self.assertEqual(continuous_response.status_code, 201)
        self.assertTrue(continuous_response.json()["repeat_enabled"])
        self.assertEqual(continuous_response.json()["repeat_interval_minutes"], 15)

        continuous_list = self.client.get("/api/v1/outgoing/continuous")
        self.assertEqual(continuous_list.status_code, 200)
        self.assertEqual(continuous_list.json()[0]["repeat_interval_minutes"], 15)

    def test_outgoing_detail_includes_auth_config(self) -> None:
        create_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_scheduled",
                "name": "detail target",
                "description": "Created during test.",
                "path_slug": "detail-target",
                "enabled": True,
                "repeat_enabled": True,
                "destination_url": "https://example.com/hooks/detail",
                "http_method": "POST",
                "auth_type": "header",
                "auth_config": {
                    "header_name": "X-API-Key",
                    "header_value": "secret-value",
                },
                "payload_template": "{\"hello\":\"world\"}",
                "scheduled_time": "08:15",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created_id = create_response.json()["id"]

        detail_response = self.client.get(f"/api/v1/outgoing/{created_id}", params={"api_type": "outgoing_scheduled"})
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["id"], created_id)
        self.assertEqual(detail["auth_type"], "header")
        self.assertEqual(detail["auth_config"]["header_name"], "X-API-Key")
        self.assertEqual(detail["auth_config"]["header_value"], "secret-value")

    def test_create_outgoing_api_from_gmail_connector_hydrates_auth(self) -> None:
        create_connector_response = self.client.post(
            "/api/v1/connectors",
            json={
                "id": "gmail-primary",
                "provider": "google",
                "name": "Google",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/gmail.send"],
                "base_url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                "owner": "Workspace",
                "auth_config": {
                    "client_id": "gmail-client-id",
                    "access_token_input": "gmail-access-token",
                    "refresh_token_input": "gmail-refresh-token",
                    "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
                    "has_refresh_token": True,
                }
            },
        )
        self.assertEqual(create_connector_response.status_code, 201)

        create_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_scheduled",
                "name": "gmail send",
                "description": "Send through Gmail connector.",
                "path_slug": "gmail-send",
                "enabled": True,
                "repeat_enabled": False,
                "destination_url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": '{"raw":"encoded-message"}',
                "scheduled_time": "09:30",
                "connector_id": "gmail-primary",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertEqual(created["connector_id"], "gmail-primary")
        self.assertEqual(created["destination_url"], "https://gmail.googleapis.com/gmail/v1/users/me/messages/send")
        self.assertEqual(created["auth_type"], "bearer")

        detail_response = self.client.get(
            f"/api/v1/outgoing/{created['id']}",
            params={"api_type": "outgoing_scheduled"},
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["destination_url"], "https://gmail.googleapis.com/gmail/v1/users/me/messages/send")
        self.assertEqual(detail["auth_type"], "bearer")
        self.assertEqual(detail["auth_config"]["token"], "gmail-access-token")

    def test_outgoing_patch_updates_record(self) -> None:
        create_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_continuous",
                "name": "patch target",
                "description": "Created during test.",
                "path_slug": "patch-target",
                "enabled": True,
                "repeat_enabled": True,
                "repeat_interval_minutes": 15,
                "destination_url": "https://example.com/hooks/continuous",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": "{\"hello\":\"world\"}",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created_id = create_response.json()["id"]

        update_response = self.client.patch(
            f"/api/v1/outgoing/{created_id}",
            json={
                "type": "outgoing_continuous",
                "name": "patched target",
                "description": "Updated during test.",
                "enabled": False,
                "repeat_enabled": False,
                "destination_url": "https://example.com/hooks/updated",
                "http_method": "PUT",
                "auth_type": "bearer",
                "auth_config": {
                    "token": "updated-token",
                },
                "payload_template": "{\"updated\":true}",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["name"], "patched target")
        self.assertEqual(updated["description"], "Updated during test.")
        self.assertFalse(updated["enabled"])
        self.assertFalse(updated["repeat_enabled"])
        self.assertIsNone(updated["repeat_interval_minutes"])
        self.assertEqual(updated["destination_url"], "https://example.com/hooks/updated")
        self.assertEqual(updated["http_method"], "PUT")
        self.assertEqual(updated["auth_type"], "bearer")
        self.assertEqual(updated["auth_config"]["token"], "updated-token")

    def test_continuous_repeat_requires_interval(self) -> None:
        response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_continuous",
                "name": "invalid continuous api",
                "description": "Missing repeat interval.",
                "path_slug": "invalid-continuous-api",
                "enabled": True,
                "repeat_enabled": True,
                "destination_url": "https://example.com/hooks/continuous",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": "{\"hello\":\"world\"}",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("require an interval", response.json()["detail"])

    def test_webhook_callback_records_history_and_triggers_matching_automation(self) -> None:
        webhook_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "webhook",
                "name": "orders webhook",
                "description": "Receives order updates.",
                "path_slug": "orders-webhook",
                "enabled": True,
                "callback_path": "/hooks/orders",
                "verification_token": "verify-orders",
                "signing_secret": "orders-secret",
                "signature_header": "X-Orders-Signature",
                "event_filter": "order.created",
            },
        )
        self.assertEqual(webhook_response.status_code, 201)
        webhook = webhook_response.json()

        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Webhook automation",
                "description": "Runs when webhook arrives.",
                "enabled": True,
                "trigger_type": "inbound_api",
                "trigger_config": {"inbound_api_id": webhook["id"]},
                "steps": [
                    {
                        "type": "log",
                        "name": "Record webhook",
                        "config": {"message": "Webhook event received"},
                    }
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)

        body = json.dumps({"event": "order.created", "order_id": "ord_123"})
        signature = hmac.new(b"orders-secret", body.encode("utf-8"), hashlib.sha256).hexdigest()
        callback_response = self.client.post(
            "/api/v1/webhooks/callback/hooks/orders?verification_token=verify-orders",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Orders-Signature": f"sha256={signature}",
                "X-Event-Name": "order.created",
            },
        )
        self.assertEqual(callback_response.status_code, 202)
        self.assertEqual(callback_response.json()["status"], "accepted")

        detail_response = self.client.get(f"/api/v1/webhooks/{webhook['id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["events_count"], 1)
        self.assertEqual(detail["last_delivery_status"], "accepted")
        self.assertEqual(detail["recent_events"][0]["event_name"], "order.created")
        self.assertTrue(detail["recent_events"][0]["verification_ok"])
        self.assertTrue(detail["recent_events"][0]["signature_ok"])
        self.assertEqual(detail["recent_events"][0]["triggered_automation_count"], 1)

        runs_response = self.client.get("/api/v1/runs")
        self.assertEqual(runs_response.status_code, 200)
        run = next((item for item in runs_response.json() if item["automation_id"] == automation_response.json()["id"]), None)
        self.assertIsNotNone(run)
        self.assertEqual(run["trigger_type"], "inbound_api")

    def test_continuous_runtime_updates_next_run_and_delivery_history(self) -> None:
        create_response = self.client.post(
            "/api/v1/apis",
            json={
                "type": "outgoing_continuous",
                "name": "continuous heartbeat",
                "description": "Repeats every five minutes.",
                "path_slug": "continuous-heartbeat",
                "enabled": True,
                "repeat_enabled": True,
                "repeat_interval_minutes": 5,
                "destination_url": "https://example.com/hooks/continuous",
                "http_method": "POST",
                "auth_type": "none",
                "payload_template": "{\"event\":\"heartbeat\"}",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        app.state.connection.execute(
            "UPDATE outgoing_continuous_apis SET next_run_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", created["id"]),
        )
        app.state.connection.commit()

        class FakeDeliveryResult:
            ok = True
            status_code = 202
            response_body = "{\"accepted\":true}"
            destination_url = "https://example.com/hooks/continuous"
            sent_headers = {"Content-Type": "application/json"}

            def model_dump(self) -> dict[str, object]:
                return {
                    "ok": self.ok,
                    "status_code": self.status_code,
                    "response_body": self.response_body,
                    "destination_url": self.destination_url,
                    "sent_headers": self.sent_headers,
                }

        with patch(
            "backend.services.helpers.execute_outgoing_test_delivery",
            return_value=FakeDeliveryResult(),
        ):
            run_scheduler_tick(app)

        detail_response = self.client.get(f"/api/v1/outgoing/{created['id']}", params={"api_type": "outgoing_continuous"})
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertIsNotNone(detail["last_run_at"])
        self.assertIsNotNone(detail["next_run_at"])
        self.assertIsNone(detail["last_error"])
        self.assertEqual(len(detail["recent_deliveries"]), 1)
        self.assertEqual(detail["recent_deliveries"][0]["resource_type"], "outgoing_continuous")
        self.assertEqual(detail["recent_deliveries"][0]["http_status_code"], 202)


if __name__ == "__main__":
    unittest.main()
