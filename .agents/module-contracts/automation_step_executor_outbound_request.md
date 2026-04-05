Owner: backend/services/automation_step_executors
Responsibilities:
- Execute `outbound_request` automation steps. Support http preset materialization, blocking and non-blocking (background) delivery, recording outgoing delivery history, and returning a normalized response payload.

Public API:
- `execute_outbound_request_step(connection, logger, *, automation_id, run_step_id, step, context, root_dir, database_url) -> dict`
- `finalize_non_blocking_http_step(...)` — background finalizer callable for background deliveries.

Owned DB tables:
- `outgoing_delivery_history` interactions via helper functions; does not own schema exclusively.

Inbound dependencies:
- `backend/services/connectors`
- `backend/services/network`
- `backend/services/automation_execution`

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests for blocking delivery, background payload creation, and error handling.
- Contract test ensuring the `automation_executor` delegates correctly and background payload is sufficient for the finalizer.

Example callsite:
```
exec_result = execute_outbound_request_step(connection, logger, automation_id=..., run_step_id=..., step=step, context=context, root_dir=root_dir)
if exec_result.get('background'):
    submit_background(finalize_non_blocking_http_step, **exec_result['background'])
else:
    process_result(exec_result['result'])
```
