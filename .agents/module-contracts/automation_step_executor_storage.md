Owner: backend/services/automation_step_executors
Responsibilities:
- Provide a stable executor entrypoint for `storage` automation steps. Orchestrates
  interactions with storage backends (local, S3, GCS) and normalizes runtime results.

Public API:
- `execute_storage_step(connection, logger, *, step, context) -> dict`

Owned DB tables:
- May write `automation_run_step_artifacts` or similar via caller; does not own tables by default.

Inbound dependencies:
- Storage adapter interfaces (S3/GCS/local) — injected by callers or resolved via services.

Allowed callers:
- `backend/services/automation_executor.py`

Test obligations:
- Unit tests must verify error handling, artifact metadata shape, and adapter failures.
