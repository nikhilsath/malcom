from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class ScriptsApiTestCase(unittest.TestCase):
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

    def test_creates_lists_and_updates_python_script(self) -> None:
        create_response = self.client.post(
            "/api/v1/scripts",
            json={
                "name": "Normalize Payload",
                "description": "Normalizes nested event fields.",
                "language": "python",
                "sample_input": "{\"text\":\"alpha,beta\"}",
                "expected_output": "{\"normalized\":\"Whether normalization ran.\"}",
                "code": "def run(payload):\n    return payload\n",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        created_body = create_response.json()
        self.assertEqual(created_body["language"], "python")
        self.assertEqual(created_body["sample_input"], "{\"text\":\"alpha,beta\"}")
        self.assertEqual(created_body["expected_output"], "{\"normalized\":\"Whether normalization ran.\"}")
        self.assertEqual(created_body["validation_status"], "valid")
        self.assertIsNotNone(created_body["last_validated_at"])

        list_response = self.client.get("/api/v1/scripts")
        self.assertEqual(list_response.status_code, 200)
        list_body = list_response.json()
        self.assertGreaterEqual(len(list_body), 4)
        self.assertIn("Change Delimiter", {item["name"] for item in list_body})
        created_summary = next(item for item in list_body if item["id"] == created_body["id"])
        self.assertEqual(created_summary["name"], "Normalize Payload")
        self.assertEqual(created_summary["sample_input"], "{\"text\":\"alpha,beta\"}")
        self.assertEqual(created_summary["expected_output"], "{\"normalized\":\"Whether normalization ran.\"}")

        detail_response = self.client.get(f"/api/v1/scripts/{created_body['id']}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], created_body["id"])
        self.assertEqual(detail_response.json()["sample_input"], "{\"text\":\"alpha,beta\"}")
        self.assertEqual(detail_response.json()["expected_output"], "{\"normalized\":\"Whether normalization ran.\"}")
        self.assertIn("def run", detail_response.json()["code"])

        update_response = self.client.patch(
            f"/api/v1/scripts/{created_body['id']}",
            json={
                "language": "python",
                "sample_input": "{\"text\":\"alpha|beta\",\"from\":\"|\",\"to\":\",\"}",
                "expected_output": "{\"result\":\"Processed result.\"}",
                "code": "def run(payload):\n    payload['normalized'] = True\n    return payload\n",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        updated_body = update_response.json()
        self.assertEqual(updated_body["validation_status"], "valid")
        self.assertEqual(updated_body["sample_input"], "{\"text\":\"alpha|beta\",\"from\":\"|\",\"to\":\",\"}")
        self.assertEqual(updated_body["expected_output"], "{\"result\":\"Processed result.\"}")
        self.assertIn("normalized", updated_body["code"])

    def test_scripts_metadata_returns_supported_languages(self) -> None:
        response = self.client.get("/api/v1/scripts/metadata")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([item["value"] for item in body["languages"]], ["python", "javascript"])

    def test_expected_output_defaults_to_empty_json_object(self) -> None:
        create_response = self.client.post(
            "/api/v1/scripts",
            json={
                "name": "No Output Script",
                "language": "python",
                "code": "def run(payload):\n    return {}\n",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        body = create_response.json()
        self.assertEqual(body["expected_output"], "{}")

    def test_seed_scripts_carry_expected_output(self) -> None:
        list_response = self.client.get("/api/v1/scripts")
        self.assertEqual(list_response.status_code, 200)
        scripts_by_name = {item["name"]: item for item in list_response.json()}

        change_delimiter = scripts_by_name.get("Change Delimiter")
        self.assertIsNotNone(change_delimiter)
        import json
        output = json.loads(change_delimiter["expected_output"])
        self.assertIn("text", output)
        self.assertIn("line_count", output)

        regex_replace = scripts_by_name.get("Regex Replace")
        self.assertIsNotNone(regex_replace)
        output = json.loads(regex_replace["expected_output"])
        self.assertIn("text", output)
        self.assertIn("replacements", output)

    def test_rejects_invalid_python_script_save(self) -> None:
        response = self.client.post(
            "/api/v1/scripts",
            json={
                "name": "Broken Python",
                "description": "",
                "language": "python",
                "sample_input": "",
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
                "code": "if (",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertGreaterEqual(len(body["issues"]), 1)


if __name__ == "__main__":
    unittest.main()
