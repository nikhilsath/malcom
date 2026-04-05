Owner: backend/services/automation_step_executors
Responsibilities:
- Execute `tool` automation steps and route to specific tool implementations (coqui-tts, llm-deepl, smtp, image-magic, etc.).

Public API:
- `execute_tool_step(connection, logger, *, step, context, root_dir) -> dict` — returns `{ "result": ... }` or `{ "error": ... }`.

Owned DB tables:
- reads `tools` table to resolve tool metadata; does not own tables exclusively.

Inbound dependencies:
- `backend/services/tool_execution`
- `backend/database`

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests for each supported tool path and error handling for unknown tool IDs.
- Contract test ensuring `automation_executor` translates executor returns to `RuntimeExecutionResult`.

Example callsite:
```
exec_result = execute_tool_step(connection, logger, step=step, context=context)
if exec_result.get('error'):
    handle_error()
else:
    process(exec_result['result'])
```
