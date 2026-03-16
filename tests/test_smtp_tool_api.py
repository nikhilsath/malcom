from __future__ import annotations

import smtplib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app, get_local_worker_id


class SmtpToolApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)

        self.previous_root_dir = app.state.root_dir
        self.previous_db_path = app.state.db_path
        self.previous_skip_ui_build_check = getattr(app.state, "skip_ui_build_check", False)
        app.state.root_dir = self.root_dir
        app.state.db_path = str(self.root_dir / "backend" / "data" / "malcom-test.db")
        app.state.skip_ui_build_check = True
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.root_dir = self.previous_root_dir
        app.state.db_path = self.previous_db_path
        app.state.skip_ui_build_check = self.previous_skip_ui_build_check
        self.tempdir.cleanup()

    def test_start_local_smtp_server_and_accept_message(self) -> None:
        local_worker_id = get_local_worker_id()

        patch_response = self.client.patch(
            "/api/v1/tools/smtp",
            json={
                "target_worker_id": local_worker_id,
                "bind_host": "127.0.0.1",
                "port": 0,
                "recipient_email": "recipient@example.com",
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        start_response = self.client.post("/api/v1/tools/smtp/start")
        self.assertEqual(start_response.status_code, 200)
        started_payload = start_response.json()
        if started_payload["runtime"]["status"] == "error" and "Operation not permitted" in (started_payload["runtime"]["last_error"] or ""):
            self.skipTest("SMTP listener binding is not permitted in the current sandbox.")
        self.assertEqual(started_payload["runtime"]["status"], "running")
        self.assertEqual(started_payload["runtime"]["selected_machine_id"], local_worker_id)

        listening_port = started_payload["runtime"]["listening_port"]
        self.assertIsInstance(listening_port, int)
        self.assertGreater(listening_port, 0)

        with smtplib.SMTP("127.0.0.1", listening_port, timeout=3) as client:
            client.sendmail(
                "sender@example.com",
                ["recipient@example.com"],
                "Subject: Test message\r\n\r\nhello from smtp test",
            )

        state_response = self.client.get("/api/v1/tools/smtp")
        self.assertEqual(state_response.status_code, 200)
        state_payload = state_response.json()
        self.assertEqual(state_payload["config"]["recipient_email"], "recipient@example.com")
        self.assertEqual(state_payload["inbound_identity"]["display_address"], "recipient@example.com")
        self.assertFalse(state_payload["inbound_identity"]["accepts_any_recipient"])
        self.assertEqual(state_payload["runtime"]["message_count"], 1)
        self.assertGreaterEqual(state_payload["runtime"]["session_count"], 1)
        self.assertEqual(state_payload["runtime"]["last_mail_from"], "sender@example.com")
        self.assertEqual(state_payload["runtime"]["last_recipient"], "recipient@example.com")
        self.assertEqual(len(state_payload["runtime"]["recent_messages"]), 1)
        self.assertEqual(state_payload["runtime"]["recent_messages"][0]["recipients"], ["recipient@example.com"])
        self.assertEqual(state_payload["runtime"]["recent_messages"][0]["subject"], "Test message")
        self.assertEqual(state_payload["runtime"]["recent_messages"][0]["body"], "hello from smtp test")
        self.assertIn("Subject: Test message", state_payload["runtime"]["recent_messages"][0]["raw_message"])

        stop_response = self.client.post("/api/v1/tools/smtp/stop")
        self.assertEqual(stop_response.status_code, 200)
        stopped_payload = stop_response.json()
        self.assertEqual(stopped_payload["runtime"]["status"], "stopped")
        self.assertIsNone(stopped_payload["runtime"]["listening_port"])

    def test_remote_machine_assignment_is_persisted_without_local_listener(self) -> None:
        register_response = self.client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "worker_lan_01",
                "name": "Desk iMac",
                "hostname": "desk-imac.local",
                "address": "192.168.1.44",
                "capabilities": ["runtime-trigger-execution"],
            },
        )
        self.assertEqual(register_response.status_code, 200)

        patch_response = self.client.patch(
            "/api/v1/tools/smtp",
            json={
                "target_worker_id": "worker_lan_01",
                "bind_host": "0.0.0.0",
                "port": 2525,
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        start_response = self.client.post("/api/v1/tools/smtp/start")
        self.assertEqual(start_response.status_code, 200)
        payload = start_response.json()
        self.assertEqual(payload["config"]["target_worker_id"], "worker_lan_01")
        self.assertTrue(payload["config"]["enabled"])
        self.assertEqual(payload["runtime"]["status"], "assigned")
        self.assertEqual(payload["runtime"]["selected_machine_id"], "worker_lan_01")
        self.assertIsNone(payload["runtime"]["listening_port"])
        self.assertIn("Remote SMTP execution is not wired yet.", payload["runtime"]["message"])

        directory_response = self.client.get("/api/v1/tools")
        self.assertEqual(directory_response.status_code, 200)
        directory_entry = next((item for item in directory_response.json() if item["id"] == "smtp"), None)
        self.assertIsNotNone(directory_entry)
        self.assertEqual(directory_entry["id"], "smtp")
        self.assertTrue(directory_entry["enabled"])
        self.assertEqual(directory_entry["page_href"], "/tools/smtp.html")

    def test_rejects_unconfigured_recipient(self) -> None:
        local_worker_id = get_local_worker_id()

        patch_response = self.client.patch(
            "/api/v1/tools/smtp",
            json={
                "target_worker_id": local_worker_id,
                "bind_host": "127.0.0.1",
                "port": 0,
                "recipient_email": "allowed@example.com",
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        start_response = self.client.post("/api/v1/tools/smtp/start")
        self.assertEqual(start_response.status_code, 200)
        started_payload = start_response.json()
        if started_payload["runtime"]["status"] == "error" and "Operation not permitted" in (started_payload["runtime"]["last_error"] or ""):
            self.skipTest("SMTP listener binding is not permitted in the current sandbox.")

        listening_port = started_payload["runtime"]["listening_port"]
        self.assertIsInstance(listening_port, int)

        with self.assertRaises(smtplib.SMTPRecipientsRefused):
            with smtplib.SMTP("127.0.0.1", listening_port, timeout=3) as client:
                client.sendmail(
                    "sender@example.com",
                    ["blocked@example.com"],
                    "Subject: Rejected message\r\n\r\nthis should not be accepted",
                )

        state_response = self.client.get("/api/v1/tools/smtp")
        self.assertEqual(state_response.status_code, 200)
        state_payload = state_response.json()
        self.assertEqual(state_payload["runtime"]["message_count"], 0)
        self.assertEqual(state_payload["inbound_identity"]["display_address"], "allowed@example.com")

    def test_local_test_send_endpoint_round_trips_into_runtime_mailbox(self) -> None:
        local_worker_id = get_local_worker_id()

        self.client.patch(
            "/api/v1/tools/smtp",
            json={
                "target_worker_id": local_worker_id,
                "bind_host": "127.0.0.1",
                "port": 0,
                "recipient_email": "loopback@example.com",
            },
        )

        start_response = self.client.post("/api/v1/tools/smtp/start")
        started_payload = start_response.json()
        if started_payload["runtime"]["status"] == "error" and "Operation not permitted" in (started_payload["runtime"]["last_error"] or ""):
            self.skipTest("SMTP listener binding is not permitted in the current sandbox.")

        send_response = self.client.post(
            "/api/v1/tools/smtp/send-test",
            json={
                "mail_from": "smtp-test@example.com",
                "recipients": ["loopback@example.com"],
                "subject": "Loopback",
                "body": "hello loopback",
            },
        )
        self.assertEqual(send_response.status_code, 200)
        send_payload = send_response.json()
        self.assertTrue(send_payload["ok"])
        self.assertIsNotNone(send_payload["message_id"])

        state_payload = self.client.get("/api/v1/tools/smtp").json()
        self.assertEqual(state_payload["runtime"]["message_count"], 1)
        self.assertEqual(state_payload["runtime"]["recent_messages"][0]["subject"], "Loopback")
        self.assertEqual(state_payload["runtime"]["recent_messages"][0]["body"], "hello loopback")

    def test_external_relay_endpoint_maps_success_and_failure_states(self) -> None:
        with mock.patch("backend.routes.tools.send_smtp_relay_message") as send_mock:
            success_response = self.client.post(
                "/api/v1/tools/smtp/send-relay",
                json={
                    "host": "smtp.example.com",
                    "port": 587,
                    "security": "starttls",
                    "auth_mode": "password",
                    "username": "demo",
                    "password": "secret",
                    "mail_from": "sender@example.com",
                    "recipients": ["recipient@example.com"],
                    "subject": "Relay",
                    "body": "relay body",
                },
            )
            self.assertEqual(success_response.status_code, 200)
            self.assertTrue(success_response.json()["ok"])
            self.assertEqual(success_response.json()["status"], "sent")
            send_mock.assert_called_once()

        with mock.patch("backend.routes.tools.send_smtp_relay_message", side_effect=Exception("should not be used")):
            invalid_response = self.client.post(
                "/api/v1/tools/smtp/send-relay",
                json={
                    "host": "",
                    "port": 587,
                    "security": "starttls",
                    "auth_mode": "none",
                    "mail_from": "sender@example.com",
                    "recipients": ["recipient@example.com"],
                    "subject": "Relay",
                    "body": "relay body",
                },
            )
            self.assertEqual(invalid_response.status_code, 422)

        with mock.patch("backend.routes.tools.send_smtp_relay_message", side_effect=HTTPException(status_code=502, detail="SMTP authentication failed: bad credentials")):
            auth_failed_response = self.client.post(
                "/api/v1/tools/smtp/send-relay",
                json={
                    "host": "smtp.example.com",
                    "port": 587,
                    "security": "starttls",
                    "auth_mode": "password",
                    "username": "demo",
                    "password": "wrong",
                    "mail_from": "sender@example.com",
                    "recipients": ["recipient@example.com"],
                    "subject": "Relay",
                    "body": "relay body",
                },
            )
            self.assertEqual(auth_failed_response.status_code, 200)
            self.assertFalse(auth_failed_response.json()["ok"])
            self.assertEqual(auth_failed_response.json()["status"], "auth_failed")


if __name__ == "__main__":
    unittest.main()
