from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class WorkersApiTestCase(unittest.TestCase):
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

    def test_register_and_list_workers(self) -> None:
        register_response = self.client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "worker_local_01",
                "name": "Desk iMac",
                "hostname": "desk-imac.local",
                "address": "192.168.1.44",
                "capabilities": ["runtime-trigger-execution"],
            },
        )
        self.assertEqual(register_response.status_code, 200)

        list_response = self.client.get("/api/v1/workers")
        self.assertEqual(list_response.status_code, 200)
        workers = list_response.json()
        registered = next(worker for worker in workers if worker["worker_id"] == "worker_local_01")
        self.assertEqual(registered["name"], "Desk iMac")


if __name__ == "__main__":
    unittest.main()
