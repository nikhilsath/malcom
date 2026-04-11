from __future__ import annotations

import smtplib
import tempfile
import unittest
from time import sleep
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import LocalLlmChatResponse
from backend.services.support import get_local_worker_id
from backend.schemas import OutgoingApiTestResponse
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class AutomationsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(self.root_dir)
        self.previous_root_dir = app.state.root_dir
        self.previous_db_path = app.state.db_path
        self.previous_database_url = app.state.database_url
        self.previous_skip_ui_build_check = getattr(app.state, "skip_ui_build_check", False)
        setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.root_dir = self.previous_root_dir
        app.state.db_path = self.previous_db_path
        app.state.database_url = self.previous_database_url
        app.state.skip_ui_build_check = self.previous_skip_ui_build_check
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

    def test_workflow_builder_connector_options_follow_stored_connectors(self) -> None:
        create_legacy_google = self.client.post(
            "/api/v1/connectors",
            json={
                "id": "legacy-google",
                "provider": "google_calendar",
                "name": "Legacy Google",
                "status": "connected",
                "auth_type": "oauth2",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "base_url": "https://www.googleapis.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "token-google"},
            },
        )
        self.assertEqual(create_legacy_google.status_code, 201)

        create_github_draft = self.client.post(
            "/api/v1/connectors",
            json={
                "id": "github-primary",
                "provider": "github",
                "name": "GitHub Primary",
                "status": "draft",
                "auth_type": "bearer",
                "scopes": ["repo"],
                "base_url": "https://api.github.com",
                "owner": "Workspace",
                "auth_config": {"access_token_input": "token-gh"},
            },
        )
        self.assertEqual(create_github_draft.status_code, 201)

        options_response = self.client.get("/api/v1/automations/workflow-connectors")
        self.assertEqual(options_response.status_code, 200)
        options = options_response.json()
        self.assertEqual(len(options), 1)

        legacy_google = next(item for item in options if item["id"] == "legacy-google")
        self.assertEqual(legacy_google["provider"], "google")
        self.assertEqual(legacy_google["provider_name"], "Google")
        self.assertEqual(legacy_google["source_path"], "connectors")
        self.assertFalse(any(item["id"] == "github-primary" for item in options))

    def test_builder_metadata_returns_backend_owned_option_sets(self) -> None:
        response = self.client.get("/api/v1/automations/builder-metadata")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([item["value"] for item in body["trigger_types"]], ["manual", "schedule", "inbound_api", "github", "smtp_email"])
        self.assertEqual(
            [item["value"] for item in body["step_types"]],
            ["log", "connector_activity", "outbound_request", "script", "tool", "condition", "llm_chat"],
        )
        self.assertEqual([item["value"] for item in body["http_methods"]], ["GET", "POST", "PUT", "PATCH", "DELETE"])
        self.assertEqual([item["value"] for item in body["storage_types"]], ["table", "csv", "json", "other"])
        self.assertEqual([item["value"] for item in body["log_column_types"]], ["text", "integer", "real", "boolean", "timestamp"])

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

    def test_http_step_extracts_json_fields_for_downstream_steps(self) -> None:
        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "HTTP extraction",
                "description": "Extracts guide counts.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "Fetch guide stats",
                        "config": {
                            "destination_url": "https://example.com/guides",
                            "http_method": "GET",
                            "payload_template": "{}",
                            "wait_for_response": True,
                            "response_mappings": [
                                {"key": "guide_count", "path": "data.guides.count"},
                                {"key": "first_title", "path": "data.guides.items[0].title"},
                            ],
                        },
                    },
                    {
                        "type": "log",
                        "name": "Log extracted guide count",
                        "config": {"message": "Guides: {{steps.Fetch guide stats.guide_count}} / {{steps.Fetch guide stats.first_title}}"},
                    },
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()

        with mock.patch(
            "backend.services.helpers.execute_outgoing_test_delivery",
            return_value=OutgoingApiTestResponse(
                ok=True,
                status_code=200,
                response_body='{"data":{"guides":{"count":4,"items":[{"title":"Welcome"}]}}}',
                sent_headers={"Content-Type": "application/json"},
                destination_url="https://example.com/guides",
            ),
        ):
            execute_response = self.client.post(f"/api/v1/automations/{automation['id']}/execute")

        self.assertEqual(execute_response.status_code, 200)
        run = execute_response.json()
        self.assertEqual(run["status"], "completed")
        http_step = run["steps"][0]
        self.assertEqual(http_step["extracted_fields_json"]["guide_count"], 4)
        self.assertEqual(http_step["extracted_fields_json"]["first_title"], "Welcome")
        self.assertEqual(http_step["response_body_json"]["data"]["guides"]["count"], 4)
        log_step = run["steps"][1]
        self.assertIn("Guides: 4 / Welcome", log_step["response_summary"])

    def test_http_step_can_continue_without_waiting_for_response(self) -> None:
        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "HTTP background",
                "description": "Continues while logging later.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "outbound_request",
                        "name": "Send background request",
                        "config": {
                            "destination_url": "https://example.com/async",
                            "http_method": "POST",
                            "payload_template": "{}",
                            "wait_for_response": False,
                            "response_mappings": [{"key": "status_value", "path": "status"}],
                        },
                    },
                    {
                        "type": "log",
                        "name": "Continue immediately",
                        "config": {"message": "continued"},
                    },
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()

        with mock.patch(
            "backend.services.helpers.execute_outgoing_test_delivery",
            side_effect=lambda payload: (
                sleep(0.05),
                OutgoingApiTestResponse(
                    ok=True,
                    status_code=202,
                    response_body='{"status":"queued"}',
                    sent_headers={"Content-Type": "application/json"},
                    destination_url=payload.destination_url,
                ),
            )[1],
        ):
            execute_response = self.client.post(f"/api/v1/automations/{automation['id']}/execute")

        self.assertEqual(execute_response.status_code, 200)
        run = execute_response.json()
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["steps"][0]["response_summary"], "Request sent in background mode.")
        self.assertEqual(run["steps"][1]["step_name"], "Continue immediately")

        for _ in range(20):
            run_detail_response = self.client.get(f"/api/v1/runs/{run['run_id']}")
            self.assertEqual(run_detail_response.status_code, 200)
            refreshed_run = run_detail_response.json()
            if refreshed_run["steps"][0]["extracted_fields_json"]:
                break
            sleep(0.05)
        else:
            self.fail("Background HTTP step did not store extracted fields in time.")

        self.assertEqual(refreshed_run["steps"][0]["extracted_fields_json"]["status_value"], "queued")
        self.assertEqual(refreshed_run["steps"][0]["response_body_json"]["status"], "queued")

    def test_script_step_receives_rendered_input_template(self) -> None:
        script_response = self.client.post(
            "/api/v1/scripts",
            json={
                "name": "Delimiter transform",
                "description": "Uses a rendered script input payload.",
                "language": "python",
                "sample_input": "{\"text\":\"alpha,beta\",\"from\":\",\",\"to\":\"|\"}",
                "code": (
                    "def run(context, script_input=None):\n"
                    "    parts = str(script_input.get('text', '')).split(script_input.get('from', ','))\n"
                    "    return {\n"
                    "        'text': script_input.get('to', '|').join(part.strip() for part in parts),\n"
                    "        'source': context.get('automation', {}).get('name'),\n"
                    "    }\n"
                ),
            },
        )
        self.assertEqual(script_response.status_code, 201)
        script_id = script_response.json()["id"]

        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Script input automation",
                "description": "Renders script input before execution.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "script",
                        "name": "Transform text",
                        "config": {
                            "script_id": script_id,
                            "script_input_template": "{\"text\":\"alpha,beta,gamma\",\"from\":\",\",\"to\":\"|\"}",
                        },
                    },
                    {
                        "type": "log",
                        "name": "Log transformed text",
                        "config": {"message": "{{steps.Transform text.text}} from {{steps.Transform text.source}}"},
                    },
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()

        execute_response = self.client.post(f"/api/v1/automations/{automation['id']}/execute")
        self.assertEqual(execute_response.status_code, 200)
        run = execute_response.json()
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["steps"][0]["response_summary"], "Python script executed.")
        self.assertIn("alpha|beta|gamma from Script input automation", run["steps"][1]["response_summary"])

    def test_inbound_triggered_automation_requires_existing_inbound_api(self) -> None:
        create_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Inbound automation",
                "description": "Runs on inbound events.",
                "enabled": True,
                "trigger_type": "inbound_api",
                "trigger_config": {"inbound_api_id": "missing-api"},
                "steps": [
                    {
                        "type": "log",
                        "name": "Inbound log",
                        "config": {"message": "Received event"},
                    }
                ],
            },
        )
        self.assertEqual(create_response.status_code, 422)
        self.assertIn("existing trigger_config.inbound_api_id", create_response.json()["detail"])

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
                        "type": "log",
                        "name": "Inbound log",
                        "config": {"message": "Received event"},
                    }
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)

        update_response = self.client.patch(
            f"/api/v1/automations/{automation_response.json()['id']}",
            json={
                "trigger_type": "inbound_api",
                "trigger_config": {"inbound_api_id": "missing-api"},
            },
        )
        self.assertEqual(update_response.status_code, 422)
        self.assertIn("existing trigger_config.inbound_api_id", update_response.json()["detail"])

    def test_manual_automation_can_execute_llm_chat_step(self) -> None:
        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Local LLM automation",
                "description": "Runs a chat step.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "llm_chat",
                        "name": "Ask the model",
                        "config": {
                            "system_prompt": "You are concise.",
                            "user_prompt": "Summarize {{automation.name}}",
                        },
                    }
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()

        with mock.patch(
            "backend.services.support.execute_local_llm_chat_request",
            return_value=LocalLlmChatResponse(
                ok=True,
                model_identifier="qwen/qwen3.5-9b",
                response_text="Summary complete.",
                response_id="response_123",
            ),
        ):
            execute_response = self.client.post(f"/api/v1/automations/{automation['id']}/execute")

        self.assertEqual(execute_response.status_code, 200)
        run = execute_response.json()
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["steps"][0]["step_name"], "Ask the model")
        self.assertIn("Summary complete.", run["steps"][0]["response_summary"])

    def test_smtp_email_triggered_automation_runs_when_matching_subject_arrives(self) -> None:
        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "SMTP automation",
                "description": "Runs when a matching email is received.",
                "enabled": True,
                "trigger_type": "smtp_email",
                "trigger_config": {
                    "smtp_subject": "Process this invoice",
                    "smtp_recipient_email": "recipient@example.com",
                },
                "steps": [
                    {
                        "type": "log",
                        "name": "Email log",
                        "config": {
                            "message": "Email received: {{payload.subject}} from {{payload.mail_from}}",
                        },
                    }
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()

        local_worker_id = get_local_worker_id()
        patch_response = self.client.patch(
            "/api/v1/tools/smtp",
            json={
                "enabled": True,
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

        listening_port = started_payload["runtime"]["listening_port"]
        self.assertIsInstance(listening_port, int)

        with smtplib.SMTP("127.0.0.1", listening_port, timeout=3) as client:
            client.sendmail(
                "sender@example.com",
                ["recipient@example.com"],
                "Subject: Process this invoice\r\n\r\ninvoice body",
            )

        runs_response = self.client.get(f"/api/v1/automations/{automation['id']}/runs")
        self.assertEqual(runs_response.status_code, 200)
        runs = runs_response.json()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["trigger_type"], "smtp_email")

    def test_smtp_email_trigger_allows_blank_filters_and_exposes_payload_fields(self) -> None:
        automation_response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "SMTP catch-all automation",
                "description": "Runs for any inbound email.",
                "enabled": True,
                "trigger_type": "smtp_email",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "log",
                        "name": "Email payload log",
                        "config": {
                            "message": "Subject={{payload.subject}} From={{payload.mail_from}} To={{payload.recipients}} At={{payload.received_at}} Raw={{payload.smtp.subject}}",
                        },
                    }
                ],
            },
        )
        self.assertEqual(automation_response.status_code, 201)
        automation = automation_response.json()
        validate_response = self.client.post(f"/api/v1/automations/{automation['id']}/validate")
        self.assertEqual(validate_response.status_code, 200)
        self.assertTrue(validate_response.json()["valid"])

        local_worker_id = get_local_worker_id()
        patch_response = self.client.patch(
            "/api/v1/tools/smtp",
            json={
                "enabled": True,
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

        listening_port = started_payload["runtime"]["listening_port"]
        self.assertIsInstance(listening_port, int)

        with smtplib.SMTP("127.0.0.1", listening_port, timeout=3) as client:
            client.sendmail(
                "sender@example.com",
                ["recipient@example.com"],
                "Subject: Catch all\r\n\r\ninvoice body",
            )

        sleep(0.1)
        runs_response = self.client.get(f"/api/v1/automations/{automation['id']}/runs")
        self.assertEqual(runs_response.status_code, 200)
        runs = runs_response.json()
        self.assertEqual(len(runs), 1)

        run_detail = self.client.get(f"/api/v1/runs/{runs[0]['run_id']}")
        self.assertEqual(run_detail.status_code, 200)
        step_detail = run_detail.json()["steps"][0]
        self.assertIn("Subject=Catch all", step_detail["response_summary"])
        self.assertIn("From=sender@example.com", step_detail["response_summary"])
        self.assertIn("To=['recipient@example.com']", step_detail["response_summary"])
        self.assertIn("Raw=Catch all", step_detail["response_summary"])

    def test_smtp_tool_step_rejects_non_numeric_relay_port(self) -> None:
        response = self.client.post(
            "/api/v1/automations",
            json={
                "name": "SMTP send validation",
                "description": "Reject invalid SMTP tool config.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "tool",
                        "name": "Send email",
                        "config": {
                            "tool_id": "smtp",
                            "tool_inputs": {
                                "relay_host": "smtp.example.com",
                                "relay_port": "abc",
                                "relay_security": "starttls",
                                "from_address": "bot@example.com",
                                "to": "user@example.com",
                                "subject": "Hello",
                                "body": "World",
                            },
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("relay_port", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
