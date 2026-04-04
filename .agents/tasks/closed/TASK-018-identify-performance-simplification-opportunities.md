Execution steps

1. [ ] [backend]
Files: backend/runtime.py
Action: Replace the full-scan requeue logic in `RuntimeEventBus._requeue_expired_claims_locked` with a claimed-jobs-only pass or a lightweight claimed-index to avoid scanning all jobs on each query. Add a small helper `_iterate_claimed_jobs` or `_claimed_jobs_index` and keep public API unchanged.
Completion check: `backend/runtime.py` contains a new helper function named `_iterate_claimed_jobs` or `_claimed_jobs_index` (verify with `grep -n "_iterate_claimed_jobs\|_claimed_jobs_index" backend/runtime.py`).

2. [ ] [backend]
Files: backend/services/automation_executor.py, backend/runtime.py
Action: Replace thread-per-non-blocking-request creation in `finalize_non_blocking_http_step` with a shared `ThreadPoolExecutor` (or a module-level `BackgroundDeliveryExecutor`) to limit thread growth. Add a module-level executor instance and use `executor.submit(...)` instead of spawning `threading.Thread(...)`.
Completion check: `backend/services/automation_executor.py` or `backend/runtime.py` contains `ThreadPoolExecutor` or a symbol named `BACKGROUND_DELIVERY_EXECUTOR` (verify with `grep -n "ThreadPoolExecutor\|BACKGROUND_DELIVERY_EXECUTOR" backend/services/automation_executor.py backend/runtime.py`).

3. [ ] [backend]
Files: backend/tool_registry.py
Action: Avoid writing the UI manifest and running migrations synchronously on every `load_tools_manifest`/`write_tools_manifest` call. Implement a short-term mitigation: batch file writes by making `write_tools_manifest` idempotent and move expensive work (migrations) out of hot paths. Suggested minimal-change: guard `run_migrations` behind an explicit `SKIP_MIGRATIONS` env var and debounce `write_tools_manifest` calls via a simple timestamp check.
Completion check: `backend/tool_registry.py` contains a guard `os.getenv("SKIP_MIGRATIONS")` or a debouncing timestamp check (verify with `grep -n "SKIP_MIGRATIONS\|debounc" backend/tool_registry.py`).

4. [ ] [backend]
Files: backend/services/workflow_storage.py
Action: Serialize append-mode writes to CSV/JSON to avoid concurrent file corruption and high filesystem contention. Add a file-level lock (module-level `threading.Lock()` named `WORKFLOW_STORAGE_LOCK`) and use it around append branches. Keep atomic-write behavior for new-file paths.
Completion check: `backend/services/workflow_storage.py` contains `WORKFLOW_STORAGE_LOCK` or an import of `threading` with lock usage around `open(..., 'a')` (verify with `grep -n "WORKFLOW_STORAGE_LOCK\|open(.*'a'" backend/services/workflow_storage.py`).

5. [ ] [db]
Files: backend/database.py, migrations/
Action: Add targeted indexes to support common lookup patterns: create `automation_run_steps_run_id_idx` on `automation_run_steps(run_id)` and `automation_runs_next_run_at_idx` if missing. Add the CREATE INDEX statements to `backend/database.py` and, if migrations are used, add a corresponding migration file in `migrations/` that runs the index creation.
Completion check: `backend/database.py` contains `automation_run_steps_run_id_idx` and/or `automation_runs_next_run_at_idx` (verify with `grep -n "automation_run_steps_run_id_idx\|automation_runs_next_run_at_idx" backend/database.py`).

6. [ ] [backend]
Files: backend/services/connectors.py, backend/services/connector_oauth.py
Action: Consolidate OAuth state and secret handling so that lifecycle and state TTL live in `connector_oauth.py` only. Remove duplicated constants or state handling from `connectors.py` and keep `connectors.py` focused on protection/encoding helpers.
Completion check: `CONNECTOR_OAUTH_STATE_TTL_SECONDS` and OAuth state-management logic exist only in `backend/services/connector_oauth.py` and not in `backend/services/connectors.py` (verify with `grep -n "CONNECTOR_OAUTH_STATE_TTL_SECONDS" backend/services | sed -n '1,200p'`).

7. [ ] [ui]
Files: ui/src/automation/app.tsx, ui/src/automation/add-step-modal.tsx, ui/src/automation/data-main.tsx
Action: Convert heavy components to dynamic imports / React.lazy where appropriate (example: lazily import `add-step-modal.tsx` from `app.tsx`). Identify 2–3 candidate components for lazy loading to reduce initial bundle size.
Completion check: `ui/src/automation/app.tsx` or other automation files contain `React.lazy` or `import(` dynamic imports (verify with `grep -n "React.lazy\|import(.*add-step-modal" ui/src/automation -R`).

8. [ ] [test]
Files: tests/test_runtime_performance.py
Action: Add a lightweight performance test that enqueues N (e.g., 5000) jobs into `RuntimeEventBus` and measures `pending_jobs()` and `claim_next()` latency to ensure earlier runtime change reduces scan time. Keep test focused on micro-benchmark behavior and not on full CI-size runs.
Completion check: New file `tests/test_runtime_performance.py` exists and contains a test named `test_runtime_eventbus_requeue_performance` (verify with `test -f tests/test_runtime_performance.py` and `grep -n "test_runtime_eventbus_requeue_performance" tests/test_runtime_performance.py`).

9. [ ] [docs]
Files: AGENTS.md, backend/AGENTS.md, README.md
Action: Document the canonical owner for connector OAuth lifecycle (move note to `backend/AGENTS.md`) and add a short description of the `RuntimeEventBus` complexity + mitigation in `README.md` or `backend/AGENTS.md`.
Completion check: `backend/AGENTS.md` contains a short paragraph mentioning `RuntimeEventBus` and connector OAuth ownership (verify with `grep -n "RuntimeEventBus\|connector OAuth" backend/AGENTS.md`).

10. [ ] [github]
Files: .agents/tasks/open/TASK-018-identify-performance-simplification-opportunities.md (this file), plus the changed/created files listed above when implemented
Action: Stage only the task file (this file) now. After executor implements each code change, they should stage the minimal changes grouped by concern (runtime, executor, workflow_storage, db-schema, connectors, ui), commit with focused messages, and push. Move this task file to `.agents/tasks/closed/` only when all implementation steps are complete.
Completion check: This task file remains in `.agents/tasks/open/` until an executor confirms all changes; the executor will commit implementation patches separately.

Test impact review

- `tests/test_runtime_worker_recovery.py` — Intent: covers worker lifecycle; action: keep and update if runtime API changes. Validation: `pytest -q tests/test_runtime_worker_recovery.py::test_worker_recovery`
- `tests/test_workflow_storage.py` — Intent: covers file-backed writes; action: update to assert locking/serialization if implemented. Validation: `pytest -q tests/test_workflow_storage.py`
- `tests/test_connectors_for_builder.py` & `tests/test_connectors_for_builder_extra.py` — Intent: connector availability; action: keep and run after connector refactor. Validation: `pytest -q tests/test_connectors_for_builder.py`
- `tests/test_automations_api.py` — Intent: end-to-end automation behavior; action: run as smoke after refactors and update snapshots if necessary. Validation: `pytest -q tests/test_automations_api.py`

Testing steps

1. [ ] [test]
Files: none (commands)
Action: After each implementation step, run the narrow validation commands listed above for the affected area (unit tests and the new micro-benchmark). Example sequence:
```
pytest -q tests/test_runtime_performance.py::test_runtime_eventbus_requeue_performance
pytest -q tests/test_workflow_storage.py
pytest -q tests/test_connectors_for_builder.py
```
Completion check: Each targeted command runs and outputs runtime numbers or test pass/fail; record results in `.agents/tasks/open/TASK-018-test-run-results.md`.

2. [ ] [test]
Files: none (commands)
Action: After DB index migration is added, run only the workflow persistence test and record execution time before/after: `pytest -q tests/test_workflow_storage.py::test_large_workflow_persistence -q` (adjust test name to match repo tests if different).
Completion check: A runtimes snapshot line is added to `.agents/tasks/open/TASK-018-test-run-results.md`.

Documentation review

1. [ ] [docs]
Files: AGENTS.md, backend/AGENTS.md, README.md
Action: Apply the short docs edits captured above (connector OAuth owner, RuntimeEventBus note). If no doc edits are necessary, note "no doc changes required" in `.agents/tasks/open/TASK-018-docs-review.md`.
Completion check: `backend/AGENTS.md` updated or `TASK-018-docs-review.md` created stating no changes.

GitHub update

1. [ ] [github]
Files: `.agents/tasks/open/TASK-018-identify-performance-simplification-opportunities.md`
Action: Stage this updated task file and commit it with message: "TASK-018: replace discovery with concrete cleanup steps for runtime, executor, storage, db, connectors, and UI". Push the commit. Executors will stage implementation changes in separate commits grouped by concern.
Completion check: Commit pushed containing only the updated task file.

Expected behavior

- This task replaces discovery with a concrete cleanup plan: each step names exact files to edit, a recommended minimal change, and a small, verifiable completion check. An executor can pick one step, implement it, and verify the check without additional discovery.
- The repository will retain test coverage and include a micro-benchmark to validate the key runtime improvement.

Notes

- I performed a lightweight scan of `backend/runtime.py`, `backend/tool_registry.py`, `backend/services/*`, `backend/database.py`, and `ui/src/automation` to identify these candidate improvements. The executor should follow each step and push small commits per concern.
- If you want, I can now (A) attempt to implement the first two small changes (add claimed-jobs helper and switch to ThreadPoolExecutor) and create the accompanying tests, or (B) hand this updated task file to an executor to implement. Which do you want me to do next?