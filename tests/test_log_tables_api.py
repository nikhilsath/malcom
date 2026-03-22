"""Tests for the Log Tables (Write-to-DB) API endpoints."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app

_TABLE_PAYLOAD = {
    "name": "test_events",
    "description": "Events captured during tests.",
    "columns": [
        {"column_name": "event_type", "data_type": "text", "nullable": True},
        {"column_name": "event_count", "data_type": "integer", "nullable": True},
    ],
}


class LogTablesApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
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

    def _create_table(self, payload: dict | None = None) -> dict:
        resp = self.client.post("/api/v1/log-tables", json=payload or _TABLE_PAYLOAD)
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()

    # ── List ──────────────────────────────────────────────────────────────────

    def test_list_log_tables_returns_empty_list_initially(self) -> None:
        resp = self.client.get("/api/v1/log-tables")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ── Create ────────────────────────────────────────────────────────────────

    def test_create_log_table_returns_detail_with_columns(self) -> None:
        data = self._create_table()
        self.assertEqual(data["name"], "test_events")
        self.assertEqual(data["description"], "Events captured during tests.")
        self.assertEqual(len(data["columns"]), 2)
        col_names = {c["column_name"] for c in data["columns"]}
        self.assertIn("event_type", col_names)
        self.assertIn("event_count", col_names)
        self.assertEqual(data["row_count"], 0)

    def test_create_log_table_appears_in_list(self) -> None:
        created = self._create_table()
        resp = self.client.get("/api/v1/log-tables")
        self.assertEqual(resp.status_code, 200)
        ids = [t["id"] for t in resp.json()]
        self.assertIn(created["id"], ids)

    def test_create_log_table_rejects_duplicate_name(self) -> None:
        self._create_table()
        resp = self.client.post("/api/v1/log-tables", json=_TABLE_PAYLOAD)
        self.assertEqual(resp.status_code, 409)

    def test_create_log_table_rejects_invalid_identifier(self) -> None:
        bad_payload = dict(_TABLE_PAYLOAD, name="Bad Name!")
        resp = self.client.post("/api/v1/log-tables", json=bad_payload)
        self.assertIn(resp.status_code, (422, 400))

    def test_create_log_table_rejects_invalid_column_name(self) -> None:
        bad_payload = {
            "name": "ok_name",
            "description": "",
            "columns": [{"column_name": "1invalid", "data_type": "text", "nullable": True}],
        }
        resp = self.client.post("/api/v1/log-tables", json=bad_payload)
        self.assertIn(resp.status_code, (422, 400))

    def test_create_log_table_with_imported_rows_persists_initial_dataset(self) -> None:
        payload = {
            "name": "imported_people",
            "description": "Imported for reuse.",
            "columns": [
                {"column_name": "email", "data_type": "text", "nullable": True},
                {"column_name": "company", "data_type": "text", "nullable": True},
            ],
            "rows": [
                {"email": "ada@example.com", "company": "Analytical Engines"},
                {"email": "grace@example.com", "company": "Compiler Labs"},
            ],
        }
        resp = self.client.post("/api/v1/log-tables", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        created = resp.json()
        self.assertEqual(created["row_count"], 2)

        rows_resp = self.client.get(f"/api/v1/log-tables/{created['id']}/rows")
        self.assertEqual(rows_resp.status_code, 200, rows_resp.text)
        rows_data = rows_resp.json()
        self.assertEqual(rows_data["total"], 2)
        values = {(row["email"], row["company"], row["automation_id"]) for row in rows_data["rows"]}
        self.assertEqual(
            values,
            {
                ("ada@example.com", "Analytical Engines", "dataset_import"),
                ("grace@example.com", "Compiler Labs", "dataset_import"),
            },
        )

    def test_create_log_table_rejects_import_rows_with_unknown_columns(self) -> None:
        payload = {
            "name": "bad_import",
            "description": "",
            "columns": [
                {"column_name": "email", "data_type": "text", "nullable": True},
            ],
            "rows": [
                {"email": "ok@example.com", "extra": "unexpected"},
            ],
        }
        resp = self.client.post("/api/v1/log-tables", json=payload)
        self.assertEqual(resp.status_code, 422, resp.text)

    # ── Detail ────────────────────────────────────────────────────────────────

    def test_get_log_table_returns_detail(self) -> None:
        created = self._create_table()
        resp = self.client.get(f"/api/v1/log-tables/{created['id']}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], created["id"])
        self.assertEqual(len(data["columns"]), 2)

    def test_get_log_table_404_for_unknown_id(self) -> None:
        resp = self.client.get("/api/v1/log-tables/does_not_exist")
        self.assertEqual(resp.status_code, 404)

    # ── Rows ──────────────────────────────────────────────────────────────────

    def test_list_log_table_rows_returns_empty_initially(self) -> None:
        created = self._create_table()
        resp = self.client.get(f"/api/v1/log-tables/{created['id']}/rows")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["table_name"], "test_events")
        self.assertEqual(data["rows"], [])
        self.assertEqual(data["total"], 0)
        self.assertIn("seq_id", data["columns"])
        self.assertIn("row_id", data["columns"])
        self.assertIn("automation_id", data["columns"])
        self.assertIn("inserted_at", data["columns"])
        self.assertIn("event_type", data["columns"])
        self.assertIn("event_count", data["columns"])

    def test_list_log_table_rows_404_for_unknown_table(self) -> None:
        resp = self.client.get("/api/v1/log-tables/does_not_exist/rows")
        self.assertEqual(resp.status_code, 404)

    def test_list_log_table_rows_rejects_out_of_range_limit(self) -> None:
        created = self._create_table()
        resp = self.client.get(f"/api/v1/log-tables/{created['id']}/rows?limit=0")
        self.assertIn(resp.status_code, (422, 400))
        resp2 = self.client.get(f"/api/v1/log-tables/{created['id']}/rows?limit=9999")
        self.assertIn(resp2.status_code, (422, 400))

    # ── Clear rows ────────────────────────────────────────────────────────────

    def test_clear_log_table_rows_returns_ok(self) -> None:
        created = self._create_table()
        resp = self.client.post(f"/api/v1/log-tables/{created['id']}/rows/clear")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["cleared"])
        self.assertEqual(data["table"], "test_events")

    def test_clear_log_table_rows_404_for_unknown_table(self) -> None:
        resp = self.client.post("/api/v1/log-tables/does_not_exist/rows/clear")
        self.assertEqual(resp.status_code, 404)

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_log_table_returns_204(self) -> None:
        created = self._create_table()
        resp = self.client.delete(f"/api/v1/log-tables/{created['id']}")
        self.assertEqual(resp.status_code, 204)

    def test_delete_log_table_removes_from_list(self) -> None:
        created = self._create_table()
        self.client.delete(f"/api/v1/log-tables/{created['id']}")
        resp = self.client.get("/api/v1/log-tables")
        ids = [t["id"] for t in resp.json()]
        self.assertNotIn(created["id"], ids)

    def test_delete_log_table_404_after_deletion(self) -> None:
        created = self._create_table()
        self.client.delete(f"/api/v1/log-tables/{created['id']}")
        resp = self.client.get(f"/api/v1/log-tables/{created['id']}")
        self.assertEqual(resp.status_code, 404)

    def test_delete_log_table_404_for_unknown_id(self) -> None:
        resp = self.client.delete("/api/v1/log-tables/does_not_exist")
        self.assertEqual(resp.status_code, 404)


class LogStepWritesToDbTestCase(unittest.TestCase):
    """Verify that a log step with log_table_id inserts a row via the execution engine."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
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

    def _create_log_table(self) -> dict:
        resp = self.client.post(
            "/api/v1/log-tables",
            json={
                "name": "run_events",
                "description": "Written during automation runs.",
                "columns": [
                    {"column_name": "note", "data_type": "text", "nullable": True},
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()

    def test_log_step_with_table_id_inserts_row_and_rows_api_returns_it(self) -> None:
        log_table = self._create_log_table()

        automation_resp = self.client.post(
            "/api/v1/automations",
            json={
                "name": "DB Write Automation",
                "description": "Writes to a log table.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "log",
                        "name": "write_event",
                        "config": {
                            "log_table_id": log_table["id"],
                            "log_column_mappings": {"note": "hello from test"},
                        },
                    }
                ],
            },
        )
        self.assertEqual(automation_resp.status_code, 201, automation_resp.text)
        automation_id = automation_resp.json()["id"]

        exec_resp = self.client.post(f"/api/v1/automations/{automation_id}/execute")
        self.assertEqual(exec_resp.status_code, 200, exec_resp.text)

        rows_resp = self.client.get(f"/api/v1/log-tables/{log_table['id']}/rows")
        self.assertEqual(rows_resp.status_code, 200)
        rows_data = rows_resp.json()
        self.assertEqual(rows_data["total"], 1)
        row = rows_data["rows"][0]
        self.assertEqual(row["seq_id"], 1)
        self.assertEqual(row["note"], "hello from test")
        self.assertEqual(row["automation_id"], automation_id)

    def test_log_step_row_seq_id_increments_across_inserts(self) -> None:
        log_table = self._create_log_table()

        automation_resp = self.client.post(
            "/api/v1/automations",
            json={
                "name": "DB Seq Write Automation",
                "description": "Writes two rows to validate sequential IDs.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "log",
                        "name": "write_event",
                        "config": {
                            "log_table_id": log_table["id"],
                            "log_column_mappings": {"note": "hello from test"},
                        },
                    }
                ],
            },
        )
        self.assertEqual(automation_resp.status_code, 201, automation_resp.text)
        automation_id = automation_resp.json()["id"]

        first_exec = self.client.post(f"/api/v1/automations/{automation_id}/execute")
        self.assertEqual(first_exec.status_code, 200, first_exec.text)
        second_exec = self.client.post(f"/api/v1/automations/{automation_id}/execute")
        self.assertEqual(second_exec.status_code, 200, second_exec.text)

        rows_resp = self.client.get(f"/api/v1/log-tables/{log_table['id']}/rows")
        self.assertEqual(rows_resp.status_code, 200)
        rows = rows_resp.json()["rows"]
        seq_ids = sorted(row["seq_id"] for row in rows)
        self.assertEqual(seq_ids, [1, 2])

    def test_log_step_validation_requires_log_column_mappings_when_table_id_set(self) -> None:
        log_table = self._create_log_table()
        resp = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Bad DB Write",
                "description": "",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "log",
                        "name": "bad_step",
                        "config": {
                            "log_table_id": log_table["id"],
                            # missing log_column_mappings
                        },
                    }
                ],
            },
        )
        # Should fail with 400 or 422 because mappings are required
        self.assertIn(resp.status_code, (400, 422), resp.text)

    def test_legacy_log_step_with_message_still_works(self) -> None:
        resp = self.client.post(
            "/api/v1/automations",
            json={
                "name": "Legacy Log",
                "description": "Uses the old message field.",
                "enabled": True,
                "trigger_type": "manual",
                "trigger_config": {},
                "steps": [
                    {
                        "type": "log",
                        "name": "legacy_log",
                        "config": {"message": "still works"},
                    }
                ],
            },
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        exec_resp = self.client.post(f"/api/v1/automations/{resp.json()['id']}/execute")
        self.assertEqual(exec_resp.status_code, 200, exec_resp.text)


if __name__ == "__main__":
    unittest.main()
