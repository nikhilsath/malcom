from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class AutomationsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        app.state.db_path = str(Path(self.tempdir.name) / "malcom-test.db")
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def create_inbound_api(self) -> dict:
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

    def test_create_validate_execute_and_delete_manual_automation(self) -> None:
        create_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Log automation",
                "description": "Writes a log message.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "log",
                        "name": "Operator log",
                        "config": {
                            "message": "Manual run at {{timestamp}}"
                        },
                    }
                ],
            },
        )
        self.assertEqual(create_response.status_code, 201)
        automation = create_response.json()
        self.assertEqual(automation["step_count"], 1)

        list_response = self.client.get("/api/v1/automations")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        validate_response = self.client.post(f"/api/v1/automations/{automation['id']}/validate")
        self.assertEqual(validate_response.status_code, 200)
        self.assertTrue(validate_response.json()["valid"])

        execute_response = self.client.post(f"/api/v1/automations/{automation['id']}/execute")
        self.assertEqual(execute_response.status_code, 200)
        run = execute_response.json()
        self.assertEqual(run["automation_id"], automation["id"])
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["steps"][0]["step_name"], "Operator log")

        runs_response = self.client.get(f"/api/v1/automations/{automation['id']}/runs")
        self.assertEqual(runs_response.status_code, 200)
        self.assertEqual(len(runs_response.json()), 1)

        delete_response = self.client.delete(f"/api/v1/automations/{automation['id']}")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(self.client.get("/api/v1/automations").json(), [])

    def test_schedule_automation_registers_scheduler_job(self) -> None:
        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Scheduled automation",
                "description": "Runs once per day.",
                "enabled": True,
                "trigger_type": "schedule",
                "trigger_config": {"schedule_time": "09:30"},
                "steps": [
                    {
                        "type": "log",
                        "name": "Scheduled log",
                        "config": {"message": "Scheduled"},
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201)
        automation = response.json()
        self.assertIsNotNone(automation["next_run_at"])

        jobs_response = self.client.get("/api/v1/scheduler/jobs")
        self.assertEqual(jobs_response.status_code, 200)
        jobs = jobs_response.json()
        self.assertTrue(any(job["id"] == automation["id"] and job["kind"] == "automation" for job in jobs))

    def test_inbound_triggered_automation_runs_when_event_is_received(self) -> None:
        inbound = self.create_inbound_api()
        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Inbound automation",
                "description": "Runs on inbound events.",
                "enabled": True,
                "trigger_type": "inbound_api",
                "trigger_config": {"inbound_api_id": inbound["id"]},
                "steps": [
                    {
                        "type": "condition",
                        "name": "Always continue",
                        "config": {"expression": "True", "stop_on_false": True},
                    },
                    {
                        "type": "log",
                        "name": "Inbound log",
                        "config": {"message": "Received {{payload.order_id}}"},
                    },
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()

        event_response = self.client.post(
            f"/api/v1/inbound/{inbound['id']}",
            headers={
                "Authorization": f"Bearer {inbound['secret']}",
                "Content-Type": "application/json",
            },
            json={"order_id": 42},
        )
        self.assertEqual(event_response.status_code, 202)

        runs_response = self.client.get(f"/api/v1/automations/{automation['id']}/runs")
        self.assertEqual(runs_response.status_code, 200)
        runs = runs_response.json()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["trigger_type"], "inbound_api")


if __name__ == "__main__":
    unittest.main()
