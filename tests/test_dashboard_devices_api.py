from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.runtime import RuntimeTrigger, runtime_event_bus
from tests.postgres_test_utils import setup_postgres_test_app


class DashboardDevicesApiTestCase(unittest.TestCase):
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

    def test_dashboard_devices_returns_host_telemetry(self) -> None:
        fake_psutil = SimpleNamespace(
            virtual_memory=lambda: SimpleNamespace(
                total=16_000,
                used=6_000,
                available=10_000,
                percent=37.5,
            ),
            disk_usage=lambda path: SimpleNamespace(
                total=1_000_000,
                used=400_000,
                free=600_000,
                percent=40.0,
            ),
        )

        with patch.dict(sys.modules, {"psutil": fake_psutil}):
            response = self.client.get("/api/v1/dashboard/devices")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("host", payload)
        self.assertIn("devices", payload)
        self.assertIsInstance(payload["devices"], list)
        self.assertGreaterEqual(len(payload["devices"]), 1)

        host = payload["host"]
        self.assertEqual(host["status"], "healthy")
        self.assertEqual(host["memory_total_bytes"], 16_000)
        self.assertEqual(host["memory_used_bytes"], 6_000)
        self.assertEqual(host["memory_available_bytes"], 10_000)
        self.assertEqual(host["memory_usage_percent"], 37.5)
        self.assertEqual(host["storage_total_bytes"], 1_000_000)
        self.assertEqual(host["storage_used_bytes"], 400_000)
        self.assertEqual(host["storage_free_bytes"], 600_000)
        self.assertEqual(host["storage_usage_percent"], 40.0)
        self.assertEqual(host["memory_used_bytes"] + host["memory_available_bytes"], host["memory_total_bytes"])
        self.assertEqual(host["storage_used_bytes"] + host["storage_free_bytes"], host["storage_total_bytes"])

    def test_dashboard_devices_includes_registered_workers(self) -> None:
        register_response = self.client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "worker_lan_02",
                "name": "Office Mac mini",
                "hostname": "office-mac-mini.local",
                "address": "192.168.1.55",
                "capabilities": ["runtime-trigger-execution"],
            },
        )
        self.assertEqual(register_response.status_code, 200)

        response = self.client.get("/api/v1/dashboard/devices")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        device_ids = {device["id"] for device in payload["devices"]}
        self.assertIn("worker-worker_lan_02", device_ids)

    def test_dashboard_queue_returns_empty_when_no_jobs_are_emitted(self) -> None:
        response = self.client.get("/api/v1/dashboard/queue")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "running")
        self.assertFalse(payload["is_paused"])
        self.assertIsInstance(payload["status_updated_at"], str)
        self.assertEqual(payload["total_jobs"], 0)
        self.assertEqual(payload["pending_jobs"], 0)
        self.assertEqual(payload["claimed_jobs"], 0)
        self.assertEqual(payload["jobs"], [])

    def test_dashboard_queue_includes_pending_runtime_jobs(self) -> None:
        runtime_event_bus.emit(
            RuntimeTrigger(
                type="inbound_api",
                api_id="orders-webhook",
                event_id="evt_123",
                payload={"order_id": "A100"},
                received_at="2026-03-20T09:00:00.000Z",
            ),
            job_id="job_123",
            run_id="run_123",
            step_id="step_123",
        )

        response = self.client.get("/api/v1/dashboard/queue")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["status"], "running")
        self.assertFalse(payload["is_paused"])
        self.assertEqual(payload["total_jobs"], 1)
        self.assertEqual(payload["pending_jobs"], 1)
        self.assertEqual(payload["claimed_jobs"], 0)
        self.assertEqual(payload["jobs"][0]["job_id"], "job_123")
        self.assertEqual(payload["jobs"][0]["status"], "pending")
        self.assertEqual(payload["jobs"][0]["api_id"], "orders-webhook")

    def test_dashboard_queue_pause_and_unpause_endpoints_toggle_claiming(self) -> None:
        register_response = self.client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "worker_pause_test",
                "name": "Queue worker",
                "hostname": "queue-worker.local",
                "address": "127.0.0.1",
                "capabilities": ["runtime-trigger-execution"],
            },
        )
        self.assertEqual(register_response.status_code, 200)

        runtime_event_bus.emit(
            RuntimeTrigger(
                type="inbound_api",
                api_id="orders-webhook",
                event_id="evt_pause_1",
                payload={"order_id": "A200"},
                received_at="2026-03-20T09:10:00.000Z",
            ),
            job_id="job_pause_1",
            run_id="run_pause_1",
            step_id="step_pause_1",
        )

        pause_response = self.client.post("/api/v1/dashboard/queue/pause")
        self.assertEqual(pause_response.status_code, 200)
        self.assertTrue(pause_response.json()["is_paused"])
        self.assertEqual(pause_response.json()["status"], "paused")

        claim_while_paused = self.client.post(
            "/api/v1/workers/claim-trigger",
            json={"worker_id": "worker_pause_test"},
        )
        self.assertEqual(claim_while_paused.status_code, 200)
        self.assertIsNone(claim_while_paused.json()["job"])

        unpause_response = self.client.post("/api/v1/dashboard/queue/unpause")
        self.assertEqual(unpause_response.status_code, 200)
        self.assertFalse(unpause_response.json()["is_paused"])
        self.assertEqual(unpause_response.json()["status"], "running")

        claim_after_unpause = self.client.post(
            "/api/v1/workers/claim-trigger",
            json={"worker_id": "worker_pause_test"},
        )
        self.assertEqual(claim_after_unpause.status_code, 200)
        self.assertIsNotNone(claim_after_unpause.json()["job"])
        self.assertEqual(claim_after_unpause.json()["job"]["job_id"], "job_pause_1")


if __name__ == "__main__":
    unittest.main()
