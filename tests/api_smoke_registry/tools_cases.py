from __future__ import annotations

from unittest import mock

from .builders import action_case, list_case, patch_case
from .core import RouteSmokeCase, assert_json_response, default_invoke
from .local_llm_mocks import invoke_local_llm_chat, invoke_local_llm_stream
from .resources import configure_image_magic_tool, configure_local_llm, configure_smtp_tool
from .smtp_mocks import invoke_smtp_runtime_sync, invoke_smtp_send_relay, invoke_smtp_send_test


def invoke_image_magic_execute(case, context, state):
    with mock.patch(
        "backend.routes.tools.execute_image_magic_conversion_request",
        return_value={
            "output_file_path": "data/generated/image-magic/smoke-output.png",
            "stdout": "ok",
        },
    ):
        return default_invoke(case, context, state)


def invoke_image_magic_patch(case, context, state):
    with mock.patch("backend.routes.tools.verify_local_command_ready", return_value=["magick"]):
        return default_invoke(case, context, state)


TOOLS_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("tools-smtp-get", "GET", "/api/v1/tools/smtp", response_assert=assert_json_response),
    list_case("tools-local-llm-get", "GET", "/api/v1/tools/llm-deepl/local-llm", response_assert=assert_json_response),
    list_case("tools-coqui-get", "GET", "/api/v1/tools/coqui-tts", response_assert=assert_json_response),
    list_case("tools-image-magic-get", "GET", "/api/v1/tools/image-magic", response_assert=assert_json_response),
    action_case(
        "tools-local-llm-chat",
        "POST",
        "/api/v1/tools/llm-deepl/chat",
        200,
        setup=configure_local_llm,
        payload={"messages": [{"role": "user", "content": "Smoke hello"}]},
        response_assert=assert_json_response,
        invoke=invoke_local_llm_chat,
    ),
    action_case(
        "tools-local-llm-stream",
        "POST",
        "/api/v1/tools/llm-deepl/chat/stream",
        200,
        setup=configure_local_llm,
        payload={"messages": [{"role": "user", "content": "Smoke hello"}]},
        invoke=invoke_local_llm_stream,
    ),
    list_case("tools-directory-list", "GET", "/api/v1/tools", response_assert=assert_json_response),
    patch_case(
        "tools-smtp-patch",
        "/api/v1/tools/smtp",
        "/api/v1/tools/smtp",
        None,
        {"enabled": True, "bind_host": "127.0.0.1", "port": 2525, "recipient_email": "recipient@example.com"},
        response_assert=assert_json_response,
        invoke=invoke_smtp_runtime_sync,
    ),
    patch_case(
        "tools-local-llm-patch",
        "/api/v1/tools/llm-deepl/local-llm",
        "/api/v1/tools/llm-deepl/local-llm",
        None,
        {
            "enabled": True,
            "provider": "lm_studio_api_v1",
            "server_base_url": "http://127.0.0.1:1234",
            "model_identifier": "qwen/qwen3.5-9b",
            "endpoints": {"chat": "/api/v1/chat"},
        },
        response_assert=assert_json_response,
    ),
    patch_case(
        "tools-coqui-patch",
        "/api/v1/tools/coqui-tts",
        "/api/v1/tools/coqui-tts",
        None,
        {
            "enabled": True,
            "command": "tts",
            "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
            "speaker": "ljspeech",
            "language": "en",
            "output_directory": "generated-audio",
        },
        response_assert=assert_json_response,
    ),
    patch_case(
        "tools-image-magic-patch",
        "/api/v1/tools/image-magic",
        "/api/v1/tools/image-magic",
        None,
        {"enabled": True, "target_worker_id": None, "command": "magick"},
        response_assert=assert_json_response,
        invoke=invoke_image_magic_patch,
    ),
    action_case(
        "tools-smtp-start",
        "POST",
        "/api/v1/tools/smtp/start",
        200,
        setup=configure_smtp_tool,
        response_assert=assert_json_response,
        invoke=invoke_smtp_runtime_sync,
    ),
    action_case(
        "tools-smtp-stop",
        "POST",
        "/api/v1/tools/smtp/stop",
        200,
        setup=configure_smtp_tool,
        response_assert=assert_json_response,
        invoke=invoke_smtp_runtime_sync,
    ),
    action_case(
        "tools-smtp-send-test",
        "POST",
        "/api/v1/tools/smtp/send-test",
        200,
        setup=configure_smtp_tool,
        payload={
            "mail_from": "smtp-test@example.com",
            "recipients": ["recipient@example.com"],
            "subject": "Smoke test",
            "body": "hello",
        },
        response_assert=assert_json_response,
        invoke=invoke_smtp_send_test,
    ),
    action_case(
        "tools-smtp-send-relay",
        "POST",
        "/api/v1/tools/smtp/send-relay",
        200,
        payload={
            "host": "smtp.example.com",
            "port": 587,
            "security": "starttls",
            "auth_mode": "password",
            "username": "demo",
            "password": "demo",
            "mail_from": "relay@example.com",
            "recipients": ["recipient@example.com"],
            "subject": "Smoke relay",
            "body": "hello",
        },
        response_assert=assert_json_response,
        invoke=invoke_smtp_send_relay,
    ),
    action_case(
        "tools-image-magic-execute",
        "POST",
        "/api/v1/tools/image-magic/execute",
        200,
        setup=configure_image_magic_tool,
        payload={"input_file": "input.jpg", "output_format": "png", "resize": "800x600"},
        response_assert=assert_json_response,
        invoke=invoke_image_magic_execute,
    ),
    patch_case(
        "tools-directory-patch",
        "/api/v1/tools/image-magic/directory",
        "/api/v1/tools/{tool_id}/directory",
        None,
        {"name": "Image Magic Smoke", "enabled": True},
        response_assert=assert_json_response,
    ),
    patch_case(
        "tools-metadata-patch",
        "/api/v1/tools/image-magic",
        "/api/v1/tools/{tool_id}",
        None,
        {"name": "Image Magic Generic", "description": "Patched via smoke."},
        response_assert=assert_json_response,
    ),
)
