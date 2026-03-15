from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class DashboardDevicesApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        app.state.db_path = str(Path(self.tempdir.name) / "malcom-test.db")
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


if __name__ == "__main__":
    unittest.main()
