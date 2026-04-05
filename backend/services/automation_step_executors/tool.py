from __future__ import annotations

import logging
from typing import Any

from backend.database import fetch_one
from backend.services.tool_execution import (
    execute_coqui_tts_tool_step,
    execute_image_magic_tool_step,
    execute_llm_deepl_tool_step,
    execute_local_llm_chat_request,
    execute_smtp_tool_step,
)


def execute_tool_step(connection: Any, logger: logging.Logger, *, step: Any, context: dict[str, Any], root_dir: str | None = None) -> dict:
    """Execute `tool` step logic. Returns dict with `result` or `error` keys.

    This mirrors the previous inlined logic in `automation_executor`.
    """
    tool_row = fetch_one(connection, "SELECT * FROM tools WHERE id = ?", (step.config.tool_id,))
    if tool_row is None:
        return {"error": f"Tool '{step.config.tool_id}' was not found."}

    tool_id = tool_row["id"]
    try:
        if tool_id == "coqui-tts":
            out = execute_coqui_tts_tool_step(connection, step, context, root_dir=root_dir)
            return {"result": out}
        if tool_id == "llm-deepl":
            out = execute_llm_deepl_tool_step(connection, step, context)
            return {"result": out}
        if tool_id == "smtp":
            out = execute_smtp_tool_step(step, context)
            return {"result": out}
        if tool_id == "image-magic":
            out = execute_image_magic_tool_step(connection, step, context, root_dir=root_dir)
            return {"result": out}

        # Default: return meta about the tool
        detail = {"tool_id": tool_row["id"], "name": tool_row["name"], "description": tool_row["description"]}
        return {"result": {"status": "completed", "response_summary": f"Loaded tool {tool_row['name']}.", "detail": detail}}
    except Exception as exc:
        logger = logging.getLogger("automation_step_tool")
        logger.exception("tool execution failed")
        return {"error": str(exc)}
