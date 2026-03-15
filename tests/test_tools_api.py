from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend.database import connect, fetch_one
from backend.main import LocalLlmChatResponse, app


class ToolMetadataApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        self.db_path = self.root_dir / "backend" / "data" / "malcom.db"
        manifest_dir = self.root_dir / "ui" / "scripts"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        app.state.root_dir = self.root_dir
        app.state.db_path = str(self.db_path)
        app.state.skip_ui_build_check = True
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.skip_ui_build_check = False
        self.tempdir.cleanup()

    def test_updates_tool_db_override_and_manifest(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/convert-audio/directory",
            json={
                "name": "Convert - Audio Pro",
                "description": "Convert and normalize audio files for downstream processing.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Convert - Audio Pro")
        self.assertEqual(
            body["description"],
            "Convert and normalize audio files for downstream processing.",
        )

        connection = connect(self.db_path)
        try:
            saved_row = fetch_one(
                connection,
                """
                SELECT source_name, source_description, name_override, description_override
                FROM tools
                WHERE id = ?
                """,
                ("convert-audio",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["source_name"], "Convert - Audio")
        self.assertEqual(saved_row["name_override"], "Convert - Audio Pro")
        self.assertEqual(
            saved_row["description_override"],
            "Convert and normalize audio files for downstream processing.",
        )

        manifest_source = (self.root_dir / "ui" / "scripts" / "tools-manifest.js").read_text(encoding="utf-8")
        self.assertIn("Convert - Audio Pro", manifest_source)
        self.assertIn("Convert and normalize audio files for downstream processing.", manifest_source)
        self.assertIn("tools/convert-audio.html", manifest_source)

    def test_lists_tool_directory_entries_with_page_and_enabled_state(self) -> None:
        response = self.client.get("/api/v1/tools")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        convert_audio = next((item for item in body if item["id"] == "convert-audio"), None)
        self.assertIsNotNone(convert_audio)
        self.assertEqual(convert_audio["page_href"], "/tools/convert-audio.html")
        self.assertFalse(convert_audio["enabled"])

    def test_updates_enabled_state_in_directory_endpoint(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/convert-audio/directory",
            json={"enabled": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["enabled"])

        connection = connect(self.db_path)
        try:
            saved_row = fetch_one(
                connection,
                """
                SELECT enabled
                FROM tools
                WHERE id = ?
                """,
                ("convert-audio",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["enabled"], 1)

    def test_rejects_empty_updates(self) -> None:
        response = self.client.patch("/api/v1/tools/convert-audio/directory", json={})
        self.assertEqual(response.status_code, 400)

    def test_can_boot_without_built_ui_when_bypass_enabled(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/convert-audio/directory",
            json={"name": "Convert - Audio Runtime"},
        )
        self.assertEqual(response.status_code, 200)

    def test_reads_and_updates_local_llm_runtime_config(self) -> None:
        initial_response = self.client.get("/api/v1/tools/llm-deepl/local-llm")
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.json()["tool_id"], "llm-deepl")

        update_response = self.client.patch(
            "/api/v1/tools/llm-deepl/local-llm",
            json={
                "enabled": True,
                "provider": "lm_studio_api_v1",
                "server_base_url": "http://127.0.0.1:1234",
                "model_identifier": "qwen/qwen3.5-9b",
                "endpoints": {
                    "models": "/api/v1/models",
                    "chat": "/api/v1/chat",
                    "model_load": "/api/v1/models/load",
                    "model_download": "/api/v1/models/download",
                    "model_download_status": "/api/v1/models/download/status/:job_id",
                },
            },
        )

        self.assertEqual(update_response.status_code, 200)
        body = update_response.json()
        self.assertTrue(body["config"]["enabled"])
        self.assertEqual(body["config"]["provider"], "lm_studio_api_v1")
        self.assertEqual(body["config"]["model_identifier"], "qwen/qwen3.5-9b")

        directory_response = self.client.get("/api/v1/tools")
        self.assertEqual(directory_response.status_code, 200)
        local_llm = next((item for item in directory_response.json() if item["id"] == "llm-deepl"), None)
        self.assertIsNotNone(local_llm)
        self.assertTrue(local_llm["enabled"])

    def test_local_llm_chat_endpoint_uses_saved_tool_config(self) -> None:
        self.client.patch(
            "/api/v1/tools/llm-deepl/local-llm",
            json={
                "enabled": True,
                "provider": "lm_studio_api_v1",
                "server_base_url": "http://127.0.0.1:1234",
                "model_identifier": "qwen/qwen3.5-9b",
                "endpoints": {
                    "chat": "/api/v1/chat",
                },
            },
        )

        with mock.patch(
            "backend.routes.api.execute_local_llm_chat_request",
            return_value=LocalLlmChatResponse(
                ok=True,
                model_identifier="qwen/qwen3.5-9b",
                response_text="Hello from local model.",
                response_id="response_abc",
            ),
        ) as execute_chat:
            response = self.client.post(
                "/api/v1/tools/llm-deepl/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "Say hello"}
                    ]
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response_text"], "Hello from local model.")
        execute_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()
