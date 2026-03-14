from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class AutomationRunsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        app.state.db_path = str(Path(self.tempdir.name) / "malcom-test.db")
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

        all_runs_response = self.client.get("/api/v1/runs")
        self.assertEqual(all_runs_response.status_code, 200)
        all_runs = all_runs_response.json()
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

        runs_response = self.client.get("/api/v1/runs")
        self.assertEqual(runs_response.status_code, 200)
        run = runs_response.json()[0]

        detail_response = self.client.get(f"/api/v1/runs/{run['run_id']}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()

        self.assertEqual(detail["run_id"], run["run_id"])
        self.assertEqual(detail["automation_id"], api["id"])
        self.assertEqual(detail["trigger_type"], "inbound_api")
        self.assertEqual(detail["status"], "completed")
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

    def test_get_run_detail_404_for_unknown_run(self) -> None:
        response = self.client.get("/api/v1/runs/run_missing")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
