from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class RuntimeApiTestCase(unittest.TestCase):
    def wait_for_runtime_history(self, expected_count: int) -> list[dict]:
        deadline = time.time() + 3
        while time.time() < deadline:
            triggers = self.client.get("/api/v1/runtime/triggers").json()
            if len(triggers) >= expected_count:
                return triggers
            time.sleep(0.05)
        self.fail("Timed out waiting for runtime trigger history.")

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        (root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        setup_postgres_test_app(app=app, root_dir=root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_healthcheck_and_runtime_status_expose_core_runtime_fields(self) -> None:
        health_response = self.client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

        status_response = self.client.get("/api/v1/runtime/status")
        self.assertEqual(status_response.status_code, 200)
        body = status_response.json()
        self.assertIn("active", body)
        self.assertIn("job_count", body)
        self.assertIn("last_tick_started_at", body)
        self.assertIn("last_tick_finished_at", body)

    def test_scheduler_jobs_defaults_to_empty_and_runtime_triggers_record_inbound_events(self) -> None:
        jobs_response = self.client.get("/api/v1/scheduler/jobs")
        self.assertEqual(jobs_response.status_code, 200)
        self.assertIsInstance(jobs_response.json(), list)

        create_response = self.client.post(
            "/api/v1/inbound",
            json={
                "name": "Runtime trigger source",
                "description": "Receives events.",
                "path_slug": "runtime-trigger-source",
                "enabled": True,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        inbound = create_response.json()

        receive_response = self.client.post(
            f"/api/v1/inbound/{inbound['id']}",
            headers={
                "Authorization": f"Bearer {inbound['secret']}",
                "Content-Type": "application/json",
            },
            json={"id": 42},
        )
        self.assertEqual(receive_response.status_code, 202)

        triggers = self.wait_for_runtime_history(1)
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["api_id"], inbound["id"])
        self.assertEqual(triggers[0]["payload"], {"id": 42})

    def test_dashboard_summary_exposes_performance_sections(self) -> None:
        summary_response = self.client.get("/api/v1/dashboard/summary")
        self.assertEqual(summary_response.status_code, 200)
        body = summary_response.json()

        self.assertIn("health", body)
        self.assertIn("services", body)
        self.assertIn("run_counts", body)
        self.assertIn("recent_runs", body)
        self.assertIn("alerts", body)
        self.assertIn("quick_links", body)
        self.assertIn("runtime_overview", body)
        self.assertIn("worker_health", body)
        self.assertIn("api_performance", body)
        self.assertIn("connector_health", body)

        self.assertIn("scheduler_active", body["runtime_overview"])
        self.assertIn("queue_status", body["runtime_overview"])
        self.assertIn("inbound_total_24h", body["api_performance"])
        self.assertIn("needs_attention", body["connector_health"])


if __name__ == "__main__":
    unittest.main()
