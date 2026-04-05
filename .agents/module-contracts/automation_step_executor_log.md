Owner: backend/services/automation_step_executors
Responsibilities:
- Implement the `log` automation step executor. Handle DB log writes, file-backed workflow storage writes, Google Drive-backed writes via connector activities, and default logging.

Public API:
- `execute_log_step(connection, logger, *, automation_id, step, context, root_dir) -> dict` — returns `{ "result": ... }` or `{ "error": ... }`.

Owned DB tables:
- None exclusively; reads/writes may touch `storage_locations` and `automation_runs` through existing services.

Inbound dependencies:
- `backend/services/automation_execution`
- `backend/services/connector_activities`
- `backend/services/workflow_storage`
- `backend/services/storage_locations`

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests for file write, google drive delegate, and default logging paths.
- Contract test ensuring return shape and that `automation_executor` translates results correctly.

Example callsite:
```
result = execute_log_step(connection, logger, automation_id=automation_id, step=step, context=context, root_dir=root_dir)
```
