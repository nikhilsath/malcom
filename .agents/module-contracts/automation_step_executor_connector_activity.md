Owner: backend/services/automation_step_executors
Responsibilities:
- Execute `connector_activity` automation steps by invoking connector activity runners, mapping outputs to runtime results, and recording execution history.

Public API:
- `execute_connector_activity_step(connection, logger, *, step, context) -> dict` — returns `{ "result": {...}, "status": "success" }` or `{ "error": str }`.

Owned DB tables:
- `connector_activity_runs` (read/write) — if present; otherwise records to `automation_run_steps` via caller.

Inbound dependencies:
- `backend/services/connectors` and connector activity runners

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests validating successful execution, connector errors, and transient retry paths.
