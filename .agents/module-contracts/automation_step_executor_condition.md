Owner: backend/services/automation_step_executors
Responsibilities:
- Evaluate `condition` automation steps. Interpret a safe predicate
  representation and return a normalized boolean result: `{ "result": bool }`.

Public API:
- `evaluate_condition_step(connection, logger, *, step, context) -> dict`

Owned DB tables:
- None.

Inbound dependencies:
- None required; should be pure logic.

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests must validate boolean, string, and missing-predicate handling.
