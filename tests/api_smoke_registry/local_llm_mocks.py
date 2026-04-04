from __future__ import annotations

from unittest import mock

from backend.schemas import LocalLlmChatResponse

from .core import default_invoke


def invoke_local_llm_chat(case, context, state):
    with mock.patch(
        "backend.routes.tools.execute_local_llm_chat_request",
        return_value=LocalLlmChatResponse(
            ok=True,
            model_identifier="qwen/qwen3.5-9b",
            response_text="Smoke response.",
            response_id="response_smoke",
        ),
    ):
        return default_invoke(case, context, state)


def invoke_local_llm_stream(case, context, state):
    with mock.patch(
        "backend.routes.tools.build_local_llm_stream",
        return_value=iter(
            [
                b'event: delta\ndata: {"content": "Smoke "}\n\n',
                b'event: done\ndata: {"response_text": "Smoke stream"}\n\n',
            ]
        ),
    ):
        return default_invoke(case, context, state)
