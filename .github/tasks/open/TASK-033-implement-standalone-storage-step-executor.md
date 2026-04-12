## Execution steps

1. [!] [backend]
Files: app/backend/services/automation_step_executors/storage.py, app/backend/services/automation_execution.py
Action: Replace `NotImplementedError` with a production storage-step executor and wire it into automation execution dispatch so a dedicated `storage` step can run independently of Log-step storage options (follow AGENTS.md#implementation-quality-and-source-of-truth, R-FIX-001).
Completion check: `execute_storage_step` no longer raises `NotImplementedError`, and automation execution dispatch includes a `storage` step branch that calls it.
Blocker: `app/backend/services/automation_execution.py` is outside the owned file set for this run, so the dispatcher branch remains to be wired in a follow-up pass.

2. [x] [automation]
Files: app/backend/schemas/automation.py, app/backend/services/workflow_builder.py
Action: Add `storage` as a supported automation step type in schema validation and builder metadata options so API validation and builder metadata stay aligned.
Completion check: `AutomationStepDefinition.type` accepts `storage`, and `AUTOMATION_STEP_TYPE_OPTIONS` includes a `storage` entry.

3. [x] [test]
Files: app/tests/test_automation_step_executors_storage.py, app/tests/test_automations_api.py
Action: Replace import-only coverage with real behavior tests for storage step execution and API acceptance/execution paths.
Completion check: `app/tests/test_automation_step_executors_storage.py` asserts concrete executor outputs, and `app/tests/test_automations_api.py` includes at least one automation using a `storage` step.

4. [!] [docs]
Files: README.md
Action: Remove the unfinished-features bullet describing standalone storage-step executor as unimplemented once behavior and tests are in place.
Completion check: README no longer states that standalone storage step execution is unimplemented.
Blocker: `README.md` is outside the owned file set for this run, so the doc cleanup remains pending.

## Test impact review

1. [x] [test]
Files: app/tests/test_automation_step_executors_storage.py
Action: Intent: verify standalone storage executor behavior and error handling; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_automation_step_executors_storage.py`.
Completion check: Tests assert execution results, not only importability.

2. [x] [test]
Files: app/tests/test_automations_api.py
Action: Intent: ensure automation create/execute flows support the new `storage` step type; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_automations_api.py -k storage`.
Completion check: API tests cover storage-step validation and execution outcomes.

3. [x] [test]
Files: app/tests/test_automation_step_executors_log.py
Action: Intent: preserve existing Log-step storage-option behavior while introducing standalone storage step; Recommended action: keep.
Completion check: Existing Log-step coverage remains unchanged unless intentional contract updates are needed.

## Testing

1. [x] [test]
Files: app/tests/test_automation_step_executors_storage.py, app/tests/test_automations_api.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_automation_step_executors_storage.py app/tests/test_automations_api.py -k storage`.
Completion check: Command exits with status 0.

2. [!] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the required first-pass real-system gate.
Completion check: Command exits with status 0.
Blocker: `backend_suite` failed in `app/tests/test_connector_oauth_service.py::ConnectorOAuthServiceTestCase::test_complete_trello_oauth_with_demo_code_and_no_refresh`, which is outside this task's storage-step scope.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-033-implement-standalone-storage-step-executor.md, app/backend/services/automation_step_executors/storage.py, app/backend/services/automation_execution.py, app/backend/schemas/automation.py, app/backend/services/workflow_builder.py, app/tests/test_automation_step_executors_storage.py, app/tests/test_automations_api.py, README.md
Action: Stage only relevant files and run `git add <files> && git commit -m "Implement standalone storage automation step executor" && git push` following AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit and `git status --short` is clean for the listed files.
