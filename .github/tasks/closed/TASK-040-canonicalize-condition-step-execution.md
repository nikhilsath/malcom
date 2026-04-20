## Execution steps

1. [x] [automation]
Files: app/backend/services/automation_step_executors/condition.py, app/backend/services/automation_executor.py, app/backend/services/helpers.py
Action: Follow AGENTS.md#implementation-quality-and-source-of-truth (R-CODE-001, R-FIX-001) — move condition evaluation onto one canonical execution path in `app/backend/services/automation_step_executors/condition.py`, and make both `app/backend/services/automation_executor.py` and `app/backend/services/helpers.py` delegate to it instead of keeping separate inline `eval` blocks or the current placeholder `predicate` contract.
Completion check: `app/backend/services/automation_step_executors/condition.py` evaluates `step.config.expression`, `step.get("predicate")` no longer appears in the executor module, and the `"<automation-condition>"` compile/eval block no longer exists inline in both `app/backend/services/automation_executor.py` and `app/backend/services/helpers.py`.

2. [x] [test]
Files: app/tests/test_automation_step_executors_condition.py, app/tests/test_automations_api.py
Action: Replace import-only condition coverage with real behavior tests that assert true/false expression handling and branch routing through `on_true_step_id` / `on_false_step_id`, following app/tests/AGENTS.md and AGENTS.md (R-TEST-008).
Completion check: `app/tests/test_automation_step_executors_condition.py` contains concrete expression assertions, and `app/tests/test_automations_api.py` includes at least one condition-step execution path that verifies branch selection.

3. [x] [audit]
Files: .github/repo-scan-index.md
Action: Update the feature-health audit tracker entry after the canonical condition path and test coverage land so the repo scan source of truth no longer leaves this feature marked unresolved.
Completion check: `.github/repo-scan-index.md` no longer marks `backend/services/automation_step_executors/condition.py` or `tests/test_automation_step_executors_condition.py` as `needs_followup` for the current audit scope.

## Test impact review

1. [x] [test]
Files: app/tests/test_automation_step_executors_condition.py
Action: Intent: verify canonical condition evaluation behavior directly at the executor layer; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_automation_step_executors_condition.py`.
Completion check: The test file covers true/false expression outcomes and no longer only asserts import presence.

2. [x] [test]
Files: app/tests/test_automations_api.py
Action: Intent: verify condition-step branch routing survives the executor cleanup in API-visible automation execution flows; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_automations_api.py -k condition`.
Completion check: The targeted automation API coverage asserts branch selection for condition steps.

3. [x] [test]
Files: app/tests/test_validation_service.py
Action: Intent: preserve existing validation guarantees for required `config.expression` and branch step references while the execution path is consolidated; Recommended action: keep.
Completion check: Existing validation coverage remains present unless a contract change requires an explicit update in the same task.

## Testing

1. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the required first-pass real-system gate before broader or more targeted validation, following AGENTS.md#real-test-first-pass-policy (R-TEST-009).
Completion check: Command exits with status 0.

2. [x] [test]
Files: app/tests/test_automation_step_executors_condition.py, app/tests/test_automations_api.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_automation_step_executors_condition.py app/tests/test_automations_api.py -k condition`.
Completion check: Command exits with status 0.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-040-canonicalize-condition-step-execution.md, app/backend/services/automation_step_executors/condition.py, app/backend/services/automation_executor.py, app/backend/services/helpers.py, app/tests/test_automation_step_executors_condition.py, app/tests/test_automations_api.py, .github/repo-scan-index.md
Action: Stage only the condition-step task and implementation files, then run `git add <files> && git commit -m "Canonicalize condition step execution" && git push` following AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit, and `git status --short` is clean for the listed files.
