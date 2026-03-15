from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class ScriptsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "malcom-test.db"
        app.state.db_path = str(self.db_path)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_creates_lists_and_updates_python_script(self) -> None:
        create_response = self.client.post(
            "/api/v1/scripts",
            json={
                "name": "Normalize Payload",
                "description": "Normalizes nested event fields.",
                "language": "python",
                "code": "def run(payload):\n    return payload\n",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        created_body = create_response.json()
        self.assertEqual(created_body["language"], "python")
        self.assertEqual(created_body["validation_status"], "valid")
        self.assertIsNotNone(created_body["last_validated_at"])

        list_response = self.client.get("/api/v1/scripts")
        self.assertEqual(list_response.status_code, 200)
        list_body = list_response.json()
        self.assertEqual(len(list_body), 1)
        self.assertEqual(list_body[0]["id"], created_body["id"])
        self.assertEqual(list_body[0]["name"], "Normalize Payload")

        update_response = self.client.patch(
            f"/api/v1/scripts/{created_body['id']}",
            json={
                "language": "python",
                "code": "def run(payload):\n    payload['normalized'] = True\n    return payload\n",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        updated_body = update_response.json()
        self.assertEqual(updated_body["validation_status"], "valid")
        self.assertIn("normalized", updated_body["code"])

    def test_rejects_invalid_python_script_save(self) -> None:
        response = self.client.post(
            "/api/v1/scripts",
            json={
                "name": "Broken Python",
                "description": "",
                "language": "python",
                "code": "def run(:\n    pass\n",
            },
        )

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertFalse(body["detail"]["valid"])
        self.assertIn("issues", body["detail"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript validation tests.")
    def test_validates_invalid_javascript_script(self) -> None:
        response = self.client.post(
            "/api/v1/scripts/validate",
            json={
                "language": "javascript",
                "code": "export function run( { return true; }",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertGreaterEqual(len(body["issues"]), 1)


if __name__ == "__main__":
    unittest.main()
