from __future__ import annotations

import ast
from typing import Any

from backend.runtime import RuntimeExecutionResult


def execute_condition_step(connection: Any, logger: Any, *, step: Any, context: dict[str, Any]) -> RuntimeExecutionResult:
    compiled = ast.parse(step.config.expression or "", mode="eval")
    result = bool(
        eval(
            compile(compiled, "<automation-condition>", "eval"),
            {"__builtins__": {}},
            {"context": context, "payload": context.get("payload"), "steps": context.get("steps", {})},
        )
    )
    return RuntimeExecutionResult(
        status="completed",
        response_summary="Condition matched." if result else "Condition evaluated to false.",
        detail={"expression": step.config.expression, "result": result, "stop_on_false": step.config.stop_on_false},
        output=result,
    )


def evaluate_condition_step(connection: Any, logger: Any, *, step: Any, context: dict[str, Any]) -> RuntimeExecutionResult:
    return execute_condition_step(connection, logger, step=step, context=context)
