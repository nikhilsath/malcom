Owner: backend/services/automation_step_executors
Responsibilities:
- Orchestrate `script` step execution: resolve repo checkout, determine working directory, call the canonical `execute_script_step` implementation, and record checkout size.

Public API:
- `execute_script_step_wrapper(connection, logger, *, automation_id, step, context, root_dir) -> dict` — returns `{ "runtime_result": RuntimeExecutionResult }` or `{ "error": str }`.

Owned DB tables:
- Reads `scripts` and `repo_checkouts`; does not own tables.

Inbound dependencies:
- `backend/services/automation_execution` (canonical `execute_script_step`)
- `backend/services/repo_checkout_service`

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests for repo checkout handling, working directory resolution, and error paths.
