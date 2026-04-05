from __future__ import annotations

from typing import Any

from backend.runtime import RuntimeExecutionResult
from backend.services.automation_execution import render_template_string
from backend.services.tool_execution import execute_local_llm_chat_request


def execute_llm_chat_step(connection: Any, logger: Any, *, step: Any, context: dict[str, Any]) -> dict:
    messages: list[dict[str, str]] = []
    if step.config.system_prompt:
        messages.append({"role": "system", "content": render_template_string(step.config.system_prompt, context)})
    messages.append({"role": "user", "content": render_template_string(step.config.user_prompt, context)})
    llm_response = execute_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=render_template_string(step.config.model_identifier, context) if step.config.model_identifier else None,
    )
    detail = llm_response.model_dump()
    detail["request_messages"] = messages
    result = RuntimeExecutionResult(status="completed", response_summary=llm_response.response_text[:500], detail=detail, output=detail)
    return {"runtime_result": result}
