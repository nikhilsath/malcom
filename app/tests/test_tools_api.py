from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi.testclient import TestClient

from backend.database import connect, fetch_one
from backend.main import app
from backend.schemas import (
    CoquiTtsInstallationStateResponse,
    AutomationStepConfig,
    AutomationStepDefinition,
    CoquiTtsOptionResponse,
    CoquiTtsToolRuntimeResponse,
    LocalLlmChatResponse,
)
from backend.services import coqui_tts_installation
from backend.services.coqui_tts_runtime import discover_coqui_tts_runtime
from backend.services.support import build_local_llm_native_chat_body, build_local_llm_stream, execute_local_llm_chat_request
from backend.services.tool_execution import execute_coqui_tts_tool_step
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


def build_coqui_runtime(
    *,
    ready: bool = True,
    command_available: bool = True,
    message: str = "Coqui TTS runtime is available for workflow steps.",
    installation: CoquiTtsInstallationStateResponse | None = None,
    models: list[str] | None = None,
    speakers: list[str] | None = None,
    languages: list[str] | None = None,
) -> CoquiTtsToolRuntimeResponse:
    model_values = ["tts_models/en/ljspeech/tacotron2-DDC", "tts_models/en/vctk/vits"] if models is None else models
    speaker_values = ["ljspeech"] if speakers is None else speakers
    language_values = ["en"] if languages is None else languages
    return CoquiTtsToolRuntimeResponse(
        ready=ready,
        command_available=command_available,
        message=message,
        installation=build_coqui_installation_state() if installation is None else installation,
        command_options=[CoquiTtsOptionResponse(value="tts", label="tts")] if command_available else [],
        model_options=[
            CoquiTtsOptionResponse(value=value, label=value)
            for value in model_values
        ],
        speaker_options=[
            CoquiTtsOptionResponse(value=value, label=value)
            for value in speaker_values
        ],
        language_options=[
            CoquiTtsOptionResponse(value=value, label=value)
            for value in language_values
        ],
    )


def build_coqui_installation_state(
    *,
    status: str = "installed",
    installed: bool = True,
    install_available: bool = False,
    remove_available: bool = True,
    managed_command: str = ".venv/bin/tts",
    message: str = "Coqui TTS runtime is installed in the workspace virtualenv.",
) -> CoquiTtsInstallationStateResponse:
    return CoquiTtsInstallationStateResponse(
        status=status,
        installed=installed,
        install_available=install_available,
        remove_available=remove_available,
        managed_command=managed_command,
        message=message,
    )


def build_coqui_tool_response(
    *,
    command: str = "",
    enabled: bool = False,
    ready: bool = True,
    command_available: bool = True,
    message: str = "Coqui TTS runtime is available for workflow steps.",
    installation: CoquiTtsInstallationStateResponse | None = None,
) -> dict[str, object]:
    runtime = build_coqui_runtime(
        ready=ready,
        command_available=command_available,
        message=message,
        installation=installation,
    )
    return {
        "tool_id": "coqui-tts",
        "config": {
            "enabled": enabled,
            "command": command,
            "model_name": "",
            "speaker": "",
            "language": "",
        },
        "runtime": runtime.model_dump(mode="json"),
    }


class ToolMetadataApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        ensure_test_ui_scripts_dir(self.root_dir)
        self.database_url = setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.skip_ui_build_check = False
        self.tempdir.cleanup()

    def test_updates_tool_db_override_and_manifest(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/image-magic/directory",
            json={
                "name": "Image Magic Pro",
                "description": "Convert and transform image files for downstream processing.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Image Magic Pro")
        self.assertEqual(
            body["description"],
            "Convert and transform image files for downstream processing.",
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
                ("image-magic",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["source_name"], "Image Magic")
        self.assertEqual(saved_row["name_override"], "Image Magic Pro")
        self.assertEqual(
            saved_row["description_override"],
            "Convert and transform image files for downstream processing.",
        )

        manifest_source = (self.root_dir / "app" / "ui" / "scripts" / "tools-manifest.js").read_text(encoding="utf-8")
        self.assertIn("Image Magic Pro", manifest_source)
        self.assertIn("Convert and transform image files for downstream processing.", manifest_source)
        self.assertIn("tools/image-magic.html", manifest_source)

    def test_lists_tool_directory_entries_with_page_and_enabled_state(self) -> None:
        response = self.client.get("/api/v1/tools")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        image_magic = next((item for item in body if item["id"] == "image-magic"), None)
        coqui_tts = next((item for item in body if item["id"] == "coqui-tts"), None)
        self.assertIsNotNone(image_magic)
        self.assertIsNotNone(coqui_tts)
        self.assertEqual(image_magic["page_href"], "/tools/image-magic.html")
        self.assertFalse(image_magic["enabled"])
        self.assertEqual(image_magic["inputs"][0]["key"], "input_file")
        self.assertEqual(image_magic["outputs"][0]["key"], "output_file_path")
        self.assertIn("output_directory", [field["key"] for field in coqui_tts["inputs"]])

    def test_updates_enabled_state_in_directory_endpoint(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/image-magic/directory",
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
                ("image-magic",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["enabled"], 1)

    def test_rejects_empty_updates(self) -> None:
        response = self.client.patch("/api/v1/tools/image-magic/directory", json={})
        self.assertEqual(response.status_code, 400)

    def test_can_boot_without_built_ui_when_bypass_enabled(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/image-magic/directory",
            json={"name": "Image Magic Runtime"},
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

        connection = connect(database_url=self.database_url)
        try:
            config_row = fetch_one(
                connection,
                """
                SELECT config_json
                FROM tool_configs
                WHERE tool_id = ?
                """,
                ("llm-deepl",),
            )
            tool_row = fetch_one(
                connection,
                """
                SELECT enabled
                FROM tools
                WHERE id = ?
                """,
                ("llm-deepl",),
            )
            legacy_row = fetch_one(
                connection,
                """
                SELECT key
                FROM settings
                WHERE key = ?
                """,
                ("local_llm_tool",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(config_row)
        self.assertEqual(json.loads(config_row["config_json"])["provider"], "lm_studio_api_v1")
        self.assertEqual(tool_row["enabled"], 1)
        self.assertIsNone(legacy_row)

    def test_get_smtp_tool_migrates_legacy_settings_row_to_tool_configs(self) -> None:
        connection = connect(database_url=self.database_url)
        try:
            now_value = "2026-04-03T00:00:00+00:00"
            connection.execute(
                """
                INSERT INTO settings (key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (
                    "smtp_tool",
                    json.dumps(
                        {
                            "enabled": True,
                            "bind_host": "127.0.0.1",
                            "port": 2626,
                            "recipient_email": "migrated@example.com",
                        }
                    ),
                    now_value,
                    now_value,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        response = self.client.get("/api/v1/tools/smtp")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["config"]["enabled"])
        self.assertEqual(body["config"]["port"], 2626)
        self.assertEqual(body["config"]["recipient_email"], "migrated@example.com")

        connection = connect(database_url=self.database_url)
        try:
            config_row = fetch_one(
                connection,
                """
                SELECT config_json
                FROM tool_configs
                WHERE tool_id = ?
                """,
                ("smtp",),
            )
            tool_row = fetch_one(
                connection,
                """
                SELECT enabled
                FROM tools
                WHERE id = ?
                """,
                ("smtp",),
            )
            legacy_row = fetch_one(
                connection,
                """
                SELECT key
                FROM settings
                WHERE key = ?
                """,
                ("smtp_tool",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(config_row)
        self.assertEqual(json.loads(config_row["config_json"])["port"], 2626)
        self.assertEqual(tool_row["enabled"], 1)
        self.assertIsNone(legacy_row)

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
        with mock.patch(
            "backend.services.tool_runtime.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ):
            initial_response = self.client.get("/api/v1/tools/coqui-tts")

        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.json()["tool_id"], "coqui-tts")
        self.assertIn("runtime", initial_response.json())
        self.assertNotIn("output_directory", initial_response.json()["config"])

        with mock.patch(
            "backend.routes.tools.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ), mock.patch(
            "backend.services.tool_runtime.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ):
            update_response = self.client.patch(
                "/api/v1/tools/coqui-tts",
                json={
                    "enabled": True,
                    "command": "tts",
                    "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
                    "speaker": "ljspeech",
                    "language": "en",
                },
            )
        self.assertEqual(update_response.status_code, 200)
        body = update_response.json()
        self.assertTrue(body["config"]["enabled"])
        self.assertEqual(body["config"]["command"], "tts")
        self.assertEqual(body["config"]["language"], "en")
        self.assertTrue(body["runtime"]["ready"])
        self.assertNotIn("output_directory", body["config"])

        connection = connect(database_url=self.database_url)
        try:
            config_row = fetch_one(
                connection,
                """
                SELECT config_json
                FROM tool_configs
                WHERE tool_id = ?
                """,
                ("coqui-tts",),
            )
            tool_row = fetch_one(
                connection,
                """
                SELECT enabled
                FROM tools
                WHERE id = ?
                """,
                ("coqui-tts",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(config_row)
        self.assertEqual(json.loads(config_row["config_json"])["language"], "en")
        self.assertNotIn("output_directory", json.loads(config_row["config_json"]))
        self.assertEqual(tool_row["enabled"], 1)

    def test_rejects_coqui_enable_when_runtime_is_unavailable(self) -> None:
        with mock.patch(
            "backend.routes.tools.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(
                ready=False,
                command_available=False,
                message="Coqui TTS command is not executable on this host: tts",
                models=[],
                speakers=[],
                languages=[],
            ),
        ):
            response = self.client.patch(
                "/api/v1/tools/coqui-tts",
                json={
                    "enabled": True,
                    "command": "tts",
                    "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Coqui TTS command is not executable on this host: tts")

    def test_installs_coqui_runtime_and_persists_managed_command(self) -> None:
        installation_state = build_coqui_installation_state(
            status="installed",
            installed=True,
            install_available=False,
            remove_available=True,
            managed_command=".venv/bin/tts",
            message="Coqui TTS runtime was installed in the workspace virtualenv.",
        )

        with mock.patch(
            "backend.routes.tools.install_coqui_tts_runtime",
            return_value=installation_state,
        ) as install_runtime, mock.patch(
            "backend.routes.tools.build_coqui_tts_tool_response",
            return_value=build_coqui_tool_response(
                command=".venv/bin/tts",
                enabled=False,
                ready=True,
                command_available=True,
                message="Coqui TTS runtime was installed in the workspace virtualenv.",
                installation=installation_state,
            ),
        ):
            response = self.client.post("/api/v1/tools/coqui-tts/install")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["config"]["command"], ".venv/bin/tts")
        self.assertEqual(body["runtime"]["installation"]["status"], "installed")
        self.assertTrue(body["runtime"]["installation"]["installed"])
        install_runtime.assert_called_once_with(self.root_dir)

        connection = connect(database_url=self.database_url)
        try:
            config_row = fetch_one(
                connection,
                """
                SELECT config_json
                FROM tool_configs
                WHERE tool_id = ?
                """,
                ("coqui-tts",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(config_row)
        saved_config = json.loads(config_row["config_json"])
        self.assertEqual(saved_config["command"], ".venv/bin/tts")
        self.assertFalse(saved_config.get("enabled", False))

    def test_rejects_coqui_install_when_runtime_installation_fails(self) -> None:
        with mock.patch(
            "backend.routes.tools.install_coqui_tts_runtime",
            side_effect=RuntimeError("Coqui install failed."),
        ):
            response = self.client.post("/api/v1/tools/coqui-tts/install")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Coqui install failed.")

    def test_coqui_install_service_uses_configured_package_spec(self) -> None:
        not_installed = coqui_tts_installation.CoquiTtsInstallationState(
            status="not_installed",
            installed=False,
            install_available=True,
            remove_available=False,
            managed_command=".venv/bin/tts",
            message="not installed",
        )
        installed = coqui_tts_installation.CoquiTtsInstallationState(
            status="installed",
            installed=True,
            install_available=False,
            remove_available=True,
            managed_command=".venv/bin/tts",
            message="installed",
        )

        with mock.patch.dict(
            "os.environ",
            {"MALCOM_COQUI_TTS_PACKAGE_SPEC": "/tmp/fake-coqui-package"},
            clear=False,
        ), mock.patch(
            "backend.services.coqui_tts_installation.get_coqui_tts_installation_state",
            side_effect=[not_installed, installed],
        ), mock.patch(
            "backend.services.coqui_tts_installation._run_repo_virtualenv_pip",
        ) as run_pip:
            state = coqui_tts_installation.install_coqui_tts_runtime(self.root_dir)

        self.assertTrue(state.installed)
        run_pip.assert_called_once_with(
            self.root_dir,
            ["install", "/tmp/fake-coqui-package"],
            action_label="installation",
        )

    def test_coqui_install_service_can_copy_configured_command_source(self) -> None:
        virtualenv_bin = self.root_dir / ".venv" / "bin"
        virtualenv_bin.mkdir(parents=True)
        python_path = virtualenv_bin / "python"
        python_path.write_text("#!/bin/sh\n", encoding="utf-8")
        python_path.chmod(0o755)
        source_path = self.root_dir / "fixtures" / "tts"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("#!/bin/sh\necho fixture\n", encoding="utf-8")

        with mock.patch.dict(
            "os.environ",
            {"MALCOM_COQUI_TTS_COMMAND_SOURCE": str(source_path)},
            clear=False,
        ), mock.patch(
            "backend.services.coqui_tts_installation._run_repo_virtualenv_pip",
        ) as run_pip:
            installed_state = coqui_tts_installation.install_coqui_tts_runtime(self.root_dir)
            removed_state = coqui_tts_installation.remove_coqui_tts_runtime(self.root_dir)

        managed_command = virtualenv_bin / "tts"
        self.assertTrue(installed_state.installed)
        self.assertFalse(removed_state.installed)
        self.assertFalse(managed_command.exists())
        run_pip.assert_not_called()

    def test_coqui_runtime_discovers_three_segment_model_names(self) -> None:
        command_path = self.root_dir / "bin" / "tts"
        command_path.parent.mkdir(parents=True)
        command_path.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *--list_models*) echo tts_models/en/ljspeech/tacotron2-DDC ;;\n"
            "  *--list_speaker_idxs*) echo ljspeech ;;\n"
            "  *--list_language_idxs*) echo en ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        command_path.chmod(0o755)

        runtime = discover_coqui_tts_runtime(
            command=str(command_path),
            selected_model_name="tts_models/en/ljspeech/tacotron2-DDC",
            root_dir=self.root_dir,
        )

        self.assertTrue(runtime.ready)
        self.assertEqual(
            [option.value for option in runtime.model_options],
            ["tts_models/en/ljspeech/tacotron2-DDC"],
        )
        self.assertEqual([option.value for option in runtime.speaker_options], ["ljspeech"])
        self.assertEqual([option.value for option in runtime.language_options], ["en"])

    def test_removes_managed_coqui_runtime_and_disables_tool(self) -> None:
        installation_state = build_coqui_installation_state(
            status="installed",
            installed=True,
            install_available=False,
            remove_available=True,
            managed_command=".venv/bin/tts",
            message="Coqui TTS runtime was installed in the workspace virtualenv.",
        )
        removed_state = build_coqui_installation_state(
            status="not_installed",
            installed=False,
            install_available=True,
            remove_available=False,
            managed_command=".venv/bin/tts",
            message="Coqui TTS runtime was removed from the workspace virtualenv.",
        )

        with mock.patch(
            "backend.routes.tools.install_coqui_tts_runtime",
            return_value=installation_state,
        ), mock.patch(
            "backend.routes.tools.build_coqui_tts_tool_response",
            return_value=build_coqui_tool_response(
                command=".venv/bin/tts",
                enabled=False,
                ready=True,
                command_available=True,
                message=installation_state.message,
                installation=installation_state,
            ),
        ):
            install_response = self.client.post("/api/v1/tools/coqui-tts/install")
        self.assertEqual(install_response.status_code, 200)

        config_row = fetch_one(
            app.state.connection,
            """
            SELECT config_json
            FROM tool_configs
            WHERE tool_id = ?
            """,
            ("coqui-tts",),
        )
        self.assertIsNotNone(config_row)
        enabled_config = json.loads(config_row["config_json"])
        enabled_config["enabled"] = True
        app.state.connection.execute(
            """
            UPDATE tool_configs
            SET config_json = ?
            WHERE tool_id = ?
            """,
            (json.dumps(enabled_config), "coqui-tts"),
        )
        app.state.connection.execute(
            """
            UPDATE tools
            SET enabled = ?
            WHERE id = ?
            """,
            (1, "coqui-tts"),
        )
        app.state.connection.commit()

        with mock.patch(
            "backend.routes.tools.remove_coqui_tts_runtime",
            return_value=removed_state,
        ) as remove_runtime, mock.patch(
            "backend.routes.tools.build_coqui_tts_tool_response",
            return_value=build_coqui_tool_response(
                command=".venv/bin/tts",
                enabled=False,
                ready=False,
                command_available=False,
                message=removed_state.message,
                installation=removed_state,
            ),
        ):
            response = self.client.post("/api/v1/tools/coqui-tts/remove")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["runtime"]["installation"]["status"], "not_installed")
        self.assertFalse(body["runtime"]["installation"]["installed"])
        remove_runtime.assert_called_once_with(self.root_dir)

        connection = connect(database_url=self.database_url)
        try:
            config_row = fetch_one(
                connection,
                """
                SELECT config_json
                FROM tool_configs
                WHERE tool_id = ?
                """,
                ("coqui-tts",),
            )
            tool_row = fetch_one(
                connection,
                """
                SELECT enabled
                FROM tools
                WHERE id = ?
                """,
                ("coqui-tts",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(config_row)
        saved_config = json.loads(config_row["config_json"])
        self.assertEqual(saved_config["command"], ".venv/bin/tts")
        self.assertFalse(saved_config.get("enabled", False))
        self.assertIsNotNone(tool_row)
        self.assertEqual(tool_row["enabled"], 0)

    def test_rejects_coqui_remove_when_runtime_removal_fails(self) -> None:
        with mock.patch(
            "backend.routes.tools.remove_coqui_tts_runtime",
            side_effect=RuntimeError("Coqui removal failed."),
        ):
            response = self.client.post("/api/v1/tools/coqui-tts/remove")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Coqui removal failed.")

    def test_coqui_remove_service_uses_configured_package_name(self) -> None:
        installed = coqui_tts_installation.CoquiTtsInstallationState(
            status="installed",
            installed=True,
            install_available=False,
            remove_available=True,
            managed_command=".venv/bin/tts",
            message="installed",
        )
        not_installed = coqui_tts_installation.CoquiTtsInstallationState(
            status="not_installed",
            installed=False,
            install_available=True,
            remove_available=False,
            managed_command=".venv/bin/tts",
            message="not installed",
        )

        with mock.patch.dict(
            "os.environ",
            {"MALCOM_COQUI_TTS_PACKAGE_NAME": "malcom-playwright-coqui-tts"},
            clear=False,
        ), mock.patch(
            "backend.services.coqui_tts_installation.get_coqui_tts_installation_state",
            side_effect=[installed, not_installed],
        ), mock.patch(
            "backend.services.coqui_tts_installation._run_repo_virtualenv_pip",
        ) as run_pip:
            state = coqui_tts_installation.remove_coqui_tts_runtime(self.root_dir)

        self.assertFalse(state.installed)
        run_pip.assert_called_once_with(
            self.root_dir,
            ["uninstall", "-y", "malcom-playwright-coqui-tts"],
            action_label="removal",
        )

    def test_coqui_execution_uses_output_directory_override(self) -> None:
        with mock.patch(
            "backend.routes.tools.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ), mock.patch(
            "backend.services.tool_runtime.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ):
            response = self.client.patch(
                "/api/v1/tools/coqui-tts",
                json={
                    "enabled": True,
                    "command": "tts",
                    "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
                    "speaker": "",
                    "language": "",
                },
            )
        self.assertEqual(response.status_code, 200)

        connection = connect(database_url=self.database_url)
        try:
            step = AutomationStepDefinition(
                id="step-coqui",
                type="tool",
                name="Coqui",
                config=AutomationStepConfig(
                    tool_id="coqui-tts",
                    tool_inputs={
                        "text": "Hello from override.",
                        "output_filename": "voice-clip",
                        "output_directory": "exports/coqui-audio",
                    },
                ),
            )
            with mock.patch("backend.services.tool_execution.subprocess.run") as run_command:
                run_command.return_value = mock.Mock(stdout="ok", stderr="")
                result = execute_coqui_tts_tool_step(connection, step, {}, root_dir=self.root_dir)
        finally:
            connection.close()

        self.assertEqual(
            result.output["audio_file_path"],
            str((self.root_dir / "exports" / "coqui-audio" / "voice-clip.wav").resolve()),
        )

    def test_coqui_execution_falls_back_to_default_output_directory(self) -> None:
        with mock.patch(
            "backend.routes.tools.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ), mock.patch(
            "backend.services.tool_runtime.discover_coqui_tts_runtime",
            return_value=build_coqui_runtime(),
        ):
            response = self.client.patch(
                "/api/v1/tools/coqui-tts",
                json={
                    "enabled": True,
                    "command": "tts",
                    "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
                    "speaker": "",
                    "language": "",
                },
            )
        self.assertEqual(response.status_code, 200)

        connection = connect(database_url=self.database_url)
        try:
            step = AutomationStepDefinition(
                id="step-coqui-default",
                type="tool",
                name="Coqui",
                config=AutomationStepConfig(
                    tool_id="coqui-tts",
                    tool_inputs={
                        "text": "Hello default path.",
                        "output_filename": "default-voice",
                    },
                ),
            )
            with mock.patch("backend.services.tool_execution.subprocess.run") as run_command:
                run_command.return_value = mock.Mock(stdout="ok", stderr="")
                result = execute_coqui_tts_tool_step(connection, step, {}, root_dir=self.root_dir)
        finally:
            connection.close()

        self.assertEqual(
            result.output["audio_file_path"],
            str((self.root_dir / "data" / "generated" / "coqui-tts" / "default-voice.wav").resolve()),
        )

    def test_reads_and_updates_image_magic_tool_config(self) -> None:
        initial_response = self.client.get("/api/v1/tools/image-magic")
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.json()["tool_id"], "image-magic")

        update_response = self.client.patch(
            "/api/v1/tools/image-magic",
            json={
                "enabled": True,
                "target_worker_id": "worker-remote-test-host",
                "command": "magick",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        body = update_response.json()
        self.assertTrue(body["config"]["enabled"])
        self.assertEqual(body["config"]["target_worker_id"], "worker-remote-test-host")
        self.assertEqual(body["config"]["command"], "magick")

        connection = connect(database_url=self.database_url)
        try:
            config_row = fetch_one(
                connection,
                """
                SELECT config_json
                FROM tool_configs
                WHERE tool_id = ?
                """,
                ("image-magic",),
            )
            tool_row = fetch_one(
                connection,
                """
                SELECT enabled
                FROM tools
                WHERE id = ?
                """,
                ("image-magic",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(config_row)
        self.assertEqual(json.loads(config_row["config_json"])["target_worker_id"], "worker-remote-test-host")
        self.assertEqual(tool_row["enabled"], 1)

    def test_rejects_image_magic_enable_when_command_is_missing(self) -> None:
        with mock.patch(
            "backend.routes.tools.verify_local_command_ready",
            side_effect=RuntimeError("Image Magic command is not executable on this host: missing-magick"),
        ):
            response = self.client.patch(
                "/api/v1/tools/image-magic",
                json={
                    "enabled": True,
                    "command": "missing-magick",
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Image Magic command is not executable on this host: missing-magick")

    def test_allows_image_magic_enable_when_command_is_available(self) -> None:
        with mock.patch("backend.routes.tools.verify_local_command_ready", return_value=["magick"]) as probe_command:
            response = self.client.patch(
                "/api/v1/tools/image-magic",
                json={
                    "enabled": True,
                    "command": "magick",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["config"]["enabled"])
        probe_command.assert_called_once()
        self.assertEqual(probe_command.call_args.args[0], "magick")

    def test_executes_image_magic_with_mocked_runtime(self) -> None:
        with mock.patch("backend.routes.tools.verify_local_command_ready", return_value=["magick"]):
            self.client.patch(
                "/api/v1/tools/image-magic",
                json={
                    "enabled": True,
                    "command": "magick",
                },
            )

        with mock.patch(
            "backend.routes.tools.execute_image_magic_conversion_request",
            return_value={"output_file_path": "data/generated/image-magic/output.png", "stdout": "ok"},
        ) as execute_conversion:
            response = self.client.post(
                "/api/v1/tools/image-magic/execute",
                json={
                    "input_file": "input.jpg",
                    "output_format": "png",
                    "resize": "1024x768",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["output_file_path"].endswith("output.png"))
        execute_conversion.assert_called_once()
        call_payload = execute_conversion.call_args.args[0]
        self.assertEqual(call_payload.resize, "1024x768")

    def test_executes_image_magic_through_remote_worker_rpc(self) -> None:
        self.client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "worker_remote_image",
                "name": "Remote Image Worker",
                "hostname": "remote-image.local",
                "address": "http://192.168.1.55:8000",
                "capabilities": ["image-magic-execution"],
            },
        )

        self.client.patch(
            "/api/v1/tools/image-magic",
            json={
                "enabled": True,
                "target_worker_id": "worker_remote_image",
                "command": "magick",
            },
        )

        mocked_response = mock.Mock()
        mocked_response.json.return_value = {
            "ok": True,
            "output_file_path": "data/generated/image-magic/remote-output.png",
            "worker_id": "worker_remote_image",
            "worker_name": "Remote Image Worker",
        }

        with mock.patch("backend.routes.tools.call_worker_rpc", return_value=mocked_response) as rpc_call, mock.patch(
            "backend.routes.tools.execute_image_magic_conversion_request"
        ) as execute_local:
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
        self.assertEqual(body["worker_id"], "worker_remote_image")
        self.assertTrue(body["output_file_path"].endswith("remote-output.png"))
        rpc_call.assert_called_once()
        execute_local.assert_not_called()

    def test_updates_tool_metadata_via_generic_patch_endpoint(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/image-magic",
            json={
                "name": "Image Magic Runtime",
                "description": "Updated through the generic metadata route.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "image-magic")
        self.assertEqual(response.json()["name"], "Image Magic Runtime")
        self.assertEqual(response.json()["description"], "Updated through the generic metadata route.")

        manifest_source = (self.root_dir / "app" / "ui" / "scripts" / "tools-manifest.js").read_text(encoding="utf-8")
        self.assertIn("Image Magic Runtime", manifest_source)


if __name__ == "__main__":
    unittest.main()
