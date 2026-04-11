from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class AutomationRunsApiTestCase(unittest.TestCase):
    def wait_for_completed_runs(self, expected_count: int) -> list[dict]:
        deadline = time.time() + 3
        while time.time() < deadline:
            response = self.client.get("/api/v1/runs")
            self.assertEqual(response.status_code, 200)
            runs = response.json()
            completed = [run for run in runs if run["status"] == "completed"]
            if len(completed) >= expected_count:
                return runs
            time.sleep(0.05)
        self.fail("Timed out waiting for automation runs to complete.")

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

    def create_inbound_api(self, slug: str) -> dict:
        response = self.client.post(
            "/api/v1/inbound",
            json={
                "name": f"{slug} webhook",
                "description": "Receives events.",
                "path_slug": slug,
                "enabled": True,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def emit_run(self, api: dict, payload: dict) -> None:
        response = self.client.post(
            f"/api/v1/inbound/{api['id']}",
            headers={
                "Authorization": f"Bearer {api['secret']}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        self.assertEqual(response.status_code, 202)

    def test_list_runs_ordering_and_filters(self) -> None:
        first_api = self.create_inbound_api("first-run-source")
        second_api = self.create_inbound_api("second-run-source")

        self.emit_run(first_api, {"id": 1})
        self.emit_run(second_api, {"id": 2})

        all_runs = self.wait_for_completed_runs(2)
        self.assertEqual(len(all_runs), 2)

        self.assertGreaterEqual(all_runs[0]["started_at"], all_runs[1]["started_at"])

        status_filtered = self.client.get("/api/v1/runs", params={"status": "completed"})
        self.assertEqual(status_filtered.status_code, 200)
        self.assertEqual(len(status_filtered.json()), 2)

        automation_filtered = self.client.get(
            "/api/v1/runs",
            params={"automation_id": first_api["id"]},
        )
        self.assertEqual(automation_filtered.status_code, 200)
        self.assertEqual(len(automation_filtered.json()), 1)
        self.assertEqual(automation_filtered.json()[0]["automation_id"], first_api["id"])

        started_before = all_runs[0]["started_at"]
        time_filtered = self.client.get(
            "/api/v1/runs",
            params={"started_before": started_before},
        )
        self.assertEqual(time_filtered.status_code, 200)
        self.assertGreaterEqual(len(time_filtered.json()), 1)

        none_filtered = self.client.get(
            "/api/v1/runs",
            params={"started_after": "9999-01-01T00:00:00+00:00"},
        )
        self.assertEqual(none_filtered.status_code, 200)
        self.assertEqual(none_filtered.json(), [])

    def test_get_run_detail_response_contract(self) -> None:
        api = self.create_inbound_api("detail-run-source")
        self.emit_run(api, {"id": 123})

        run = self.wait_for_completed_runs(1)[0]

        detail_response = self.client.get(f"/api/v1/runs/{run['run_id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()

        self.assertEqual(detail["run_id"], run["run_id"])
        self.assertEqual(detail["automation_id"], api["id"])
        self.assertEqual(detail["trigger_type"], "inbound_api")
        self.assertEqual(detail["status"], "completed")
        self.assertIsNotNone(detail["worker_id"])
        self.assertIsNotNone(detail["worker_name"])
        self.assertIsInstance(detail["duration_ms"], int)
        self.assertEqual(detail["error_summary"], None)
        self.assertEqual(len(detail["steps"]), 1)

        step = detail["steps"][0]
        self.assertEqual(step["run_id"], detail["run_id"])
        self.assertEqual(step["step_name"], "emit_runtime_trigger")
        self.assertEqual(step["status"], "completed")
        self.assertIn("event_id=", step["request_summary"])
        self.assertEqual(step["response_summary"], "Trigger emitted to runtime event bus.")
        self.assertIsInstance(step["detail_json"], dict)
        self.assertIn("event_id", step["detail_json"])
        self.assertEqual(step["detail_json"]["worker_id"], detail["worker_id"])

    def test_get_run_detail_404_for_unknown_run(self) -> None:
        response = self.client.get("/api/v1/runs/run_missing")
        self.assertEqual(response.status_code, 404)

    def test_registered_worker_can_claim_and_complete_trigger(self) -> None:
        self.client.__exit__(None, None, None)
        self.client = None
        self.tempdir.cleanup()

        self.tempdir = tempfile.TemporaryDirectory()
        root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(root_dir)
        setup_postgres_test_app(app=app, root_dir=Path(__file__).resolve().parents[1])
        with patch.dict("os.environ", {"MALCOM_COORDINATOR_URL": "http://127.0.0.1:9"}):
            self.client = TestClient(app)
            self.client.__enter__()

            api = self.create_inbound_api("remote-worker-source")
            self.emit_run(api, {"id": 999})

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

            claim_response = self.client.post("/api/v1/workers/claim-trigger", json={"worker_id": "worker_lan_01"})
            self.assertEqual(claim_response.status_code, 200)
            job = claim_response.json()["job"]
            self.assertIsNotNone(job)

            complete_response = self.client.post(
                "/api/v1/workers/complete-trigger",
                json={
                    "worker_id": "worker_lan_01",
                    "job_id": job["job_id"],
                    "status": "completed",
                    "response_summary": "Remote worker executed trigger.",
                },
            )
            self.assertEqual(complete_response.status_code, 200)
            detail = complete_response.json()
            self.assertEqual(detail["status"], "completed")
            self.assertEqual(detail["worker_id"], "worker_lan_01")
            self.assertEqual(detail["worker_name"], "Desk iMac")


if __name__ == "__main__":
    unittest.main()
