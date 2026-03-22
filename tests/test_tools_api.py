from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi.testclient import TestClient

from backend.database import connect, fetch_one
from backend.main import LocalLlmChatResponse, app
from backend.services.support import build_local_llm_native_chat_body, build_local_llm_stream, execute_local_llm_chat_request
from tests.postgres_test_utils import setup_postgres_test_app


class ToolMetadataApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        manifest_dir = self.root_dir / "ui" / "scripts"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        self.database_url = setup_postgres_test_app(app=app, root_dir=self.root_dir)
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

        connection = connect(database_url=self.database_url)
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

        connection = connect(database_url=self.database_url)
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
            "backend.routes.tools.execute_local_llm_chat_request",
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

    def test_local_llm_stream_endpoint_uses_saved_tool_config(self) -> None:
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
            "backend.routes.tools.build_local_llm_stream",
            return_value=iter(
                [
                    b'event: delta\ndata: {"content": "Hello "}\n\n',
                    b'event: done\ndata: {"response_text": "Hello stream"}\n\n',
                ]
            ),
        ) as build_stream:
            response = self.client.post(
                "/api/v1/tools/llm-deepl/chat/stream",
                json={
                    "messages": [
                        {"role": "user", "content": "Stream hello"}
                    ]
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn('"content": "Hello "', response.text)
        self.assertIn('"response_text": "Hello stream"', response.text)
        build_stream.assert_called_once()

    def test_local_llm_chat_request_falls_back_to_openai_route_on_native_404(self) -> None:
        self.client.patch(
            "/api/v1/tools/llm-deepl/local-llm",
            json={
                "enabled": True,
                "provider": "lm_studio_api_v1",
                "server_base_url": "http://127.0.0.1:1234",
                "model_identifier": "qwen/qwen3.5-9b",
                "endpoints": {"chat": "/api/v1/chat"},
            },
        )

        connection = connect(database_url=self.database_url)
        native_request = httpx.Request("POST", "http://127.0.0.1:1234/api/v1/chat")
        native_response = httpx.Response(404, request=native_request)
        fallback_response = mock.Mock()
        fallback_response.raise_for_status.return_value = None
        fallback_response.json.return_value = {
            "choices": [{"message": {"content": "Fallback response."}}],
            "id": "response_fallback",
        }
        try:
            with mock.patch(
                "backend.services.support.httpx.post",
                side_effect=[
                    httpx.HTTPStatusError("Not Found", request=native_request, response=native_response),
                    fallback_response,
                ],
            ) as mocked_post:
                response = execute_local_llm_chat_request(
                    connection,
                    messages=[{"role": "user", "content": "Say hello"}],
                )
        finally:
            connection.close()

        self.assertEqual(response.response_text, "Fallback response.")
        self.assertEqual(response.response_id, "response_fallback")
        self.assertEqual(mocked_post.call_args_list[0].args[0], "http://127.0.0.1:1234/api/v1/chat")
        self.assertEqual(mocked_post.call_args_list[1].args[0], "http://127.0.0.1:1234/v1/chat/completions")
        self.assertEqual(
            mocked_post.call_args_list[1].kwargs["json"]["messages"],
            [{"role": "user", "content": "Say hello"}],
        )

    def test_local_llm_stream_falls_back_to_openai_route_on_native_404(self) -> None:
        self.client.patch(
            "/api/v1/tools/llm-deepl/local-llm",
            json={
                "enabled": True,
                "provider": "lm_studio_api_v1",
                "server_base_url": "http://127.0.0.1:1234",
                "model_identifier": "qwen/qwen3.5-9b",
                "endpoints": {"chat": "/api/v1/chat"},
            },
        )

        class FakeStreamResponse:
            def __init__(self, *, status_code: int, lines: list[str], url: str) -> None:
                self.status_code = status_code
                self._lines = lines
                self.request = httpx.Request("POST", url)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        "Not Found",
                        request=self.request,
                        response=httpx.Response(self.status_code, request=self.request),
                    )

            def iter_lines(self):
                for line in self._lines:
                    yield line

        connection = connect(database_url=self.database_url)
        try:
            with mock.patch(
                "backend.services.support.httpx.stream",
                side_effect=[
                    FakeStreamResponse(status_code=404, lines=[], url="http://127.0.0.1:1234/api/v1/chat"),
                    FakeStreamResponse(
                        status_code=200,
                        lines=[
                            'data: {"choices":[{"delta":{"content":"Fallback "}}]}',
                            "",
                            'data: {"choices":[{"delta":{"content":"stream"}}]}',
                            "",
                            "data: [DONE]",
                            "",
                        ],
                        url="http://127.0.0.1:1234/v1/chat/completions",
                    ),
                ],
            ) as mocked_stream:
                chunks = list(
                    build_local_llm_stream(
                        connection,
                        messages=[{"role": "user", "content": "Stream hello"}],
                    )
                )
        finally:
            connection.close()

        decoded = b"".join(chunks).decode("utf-8")
        self.assertIn('"content": "Fallback "', decoded)
        self.assertIn('"content": "stream"', decoded)
        self.assertIn('"response_text": "Fallback stream"', decoded)
        self.assertEqual(mocked_stream.call_args_list[0].args[1], "http://127.0.0.1:1234/api/v1/chat")
        self.assertEqual(mocked_stream.call_args_list[1].args[1], "http://127.0.0.1:1234/v1/chat/completions")

    def test_local_llm_native_chat_body_embeds_system_prompt_in_input(self) -> None:
        body = build_local_llm_native_chat_body(
            model_identifier="qwen/qwen3.5-9b",
            messages=[
                {"role": "system", "content": "Reply with yes only."},
                {"role": "user", "content": "Test Message"},
            ],
            stream=True,
        )

        self.assertEqual(body["model"], "qwen/qwen3.5-9b")
        self.assertNotIn("system", body)
        self.assertIn("System instructions:\nReply with yes only.", body["input"])
        self.assertIn("User: Test Message", body["input"])

    def test_reads_and_updates_coqui_tts_tool_config(self) -> None:
        initial_response = self.client.get("/api/v1/tools/coqui-tts")
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.json()["tool_id"], "coqui-tts")

        update_response = self.client.patch(
            "/api/v1/tools/coqui-tts",
            json={
                "enabled": True,
                "command": "tts",
                "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
                "speaker": "ljspeech",
                "language": "en",
                "output_directory": "generated-audio",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        body = update_response.json()
        self.assertTrue(body["config"]["enabled"])
        self.assertEqual(body["config"]["command"], "tts")
        self.assertEqual(body["config"]["language"], "en")
        self.assertTrue(body["config"]["output_directory"].endswith("generated-audio"))

    def test_reads_and_updates_image_magic_tool_config(self) -> None:
        initial_response = self.client.get("/api/v1/tools/image-magic")
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.json()["tool_id"], "image-magic")

        update_response = self.client.patch(
            "/api/v1/tools/image-magic",
            json={
                "enabled": True,
                "target_worker_id": "worker-local-test-host",
                "command": "magick",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        body = update_response.json()
        self.assertTrue(body["config"]["enabled"])
        self.assertEqual(body["config"]["target_worker_id"], "worker-local-test-host")
        self.assertEqual(body["config"]["command"], "magick")

    def test_executes_image_magic_with_mocked_runtime(self) -> None:
        self.client.patch(
            "/api/v1/tools/image-magic",
            json={
                "enabled": True,
                "command": "magick",
            },
        )

        with mock.patch(
            "backend.routes.tools.execute_image_magic_conversion_request",
            return_value={"output_file_path": "backend/data/generated/image-magic/output.png", "stdout": "ok"},
        ):
            response = self.client.post(
                "/api/v1/tools/image-magic/execute",
                json={
                    "input_file": "input.jpg",
                    "output_format": "png",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["output_file_path"].endswith("output.png"))

    def test_updates_tool_metadata_via_generic_patch_endpoint(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/convert-audio",
            json={
                "name": "Convert - Audio Runtime",
                "description": "Updated through the generic metadata route.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "convert-audio")
        self.assertEqual(response.json()["name"], "Convert - Audio Runtime")
        self.assertEqual(response.json()["description"], "Updated through the generic metadata route.")

        manifest_source = (self.root_dir / "ui" / "scripts" / "tools-manifest.js").read_text(encoding="utf-8")
        self.assertIn("Convert - Audio Runtime", manifest_source)


if __name__ == "__main__":
    unittest.main()
