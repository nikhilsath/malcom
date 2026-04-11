# TASK-028 environment-first real-system-test workflow

Assumption: `TASK-027-policy-first-real-test-runner-workflow.md` has already been completed. This task builds on that policy-first work and implements the environment-building test process that no longer assumes a persistent manually running local test database.

## Execution steps

1. [x] [scripts]
Files: app/scripts/dev.py, app/scripts/require_test_database.py, app/scripts/reset_playwright_test_db.py, app/scripts/run_playwright_server.sh, app/scripts/test-real-failfast.sh
Action: Refactor database/test bootstrap responsibilities so tests no longer depend on a persistent manually running local Postgres test instance. Extract or introduce reusable bootstrap logic that first ensures the test runtime exists, then ensures the test database exists, then migrates/resets it. Do not keep the test flow centered on checking for an already-running DB and then assuming the environment is ready. Preserve compatibility with GitHub Actions by making the bootstrap consume a provided reachable DB URL when present, while allowing a local fallback startup strategy only when the environment supports it.
Completion check: the changed scripts show a clear sequence of environment bootstrap → DB existence/setup → migration/reset → tests; there is no test entrypoint whose primary contract is "assume persistent local test DB is already running".

2. [x] [scripts]
Action: Introduce a true environment-building real-system command such as `app/scripts/test-system.sh` and reposition `test-real-failfast.sh` accordingly. The primary command must provision or attach to the test DB runtime, create/prepare the real test environment from zero, stop on first failure, and write one stable machine-readable artifact for every failure path. Keep the output shape small and stable for low-token AI debugging.
Completion check: the primary system-test command writes `step`, `exit_code`, `command`, and `first_error_lines` for bootstrap failure, DB setup failure, startup-lifecycle failure, backend-suite failure, browser-suite failure if included, and success; `app/tests/AGENTS.md` documents the final artifact contract and command purpose.

3. [x] [scripts]
Files: app/scripts/test-precommit.sh, app/scripts/test-full.sh, app/tests/AGENTS.md
Action: Realign the broader gates so they sit downstream of the new primary system-test command or otherwise reflect the environment-first testing design introduced by TASK-027. Keep the two-tier broader-gate model intact, but ensure the gate scripts no longer rely on the old persistent-test-DB assumption.
Completion check: `app/scripts/test-precommit.sh` and/or `app/scripts/test-full.sh` reflect the environment-first design, and their behavior matches the updated test documentation.

4. [ ] [test]
Files: app/ui/playwright.config.ts, app/ui/e2e/README.md, app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/support/dashboard-settings.ts
Action: Audit the current real vs stubbed Playwright split and make the classification explicit and accurate in the implementation that follows TASK-027. Preserve stubbed specs where they are still useful for isolated UI logic, but document that they are secondary and not the primary proof for critical workflows. If the new system-test command will include critical browser verification, identify the minimal real Playwright subset that proves the product boots and the critical UI flows still work against the real backend.
Completion check: `app/ui/e2e/README.md` and `app/ui/playwright.config.ts` agree on which specs are real vs stubbed, and the documented classification matches the actual interception behavior in the named spec/support files; if a critical real browser subset is introduced, the docs name it explicitly.

5. [ ] [scripts]
Files: .github/workflows/, app/tests/AGENTS.md, README.md
Action: Add or update GitHub Actions workflow support so CI provides a compatible database runtime and calls the same primary system-test command. Do not make the test architecture depend on the Homebrew/macOS-only startup path as the only solution. Document the expected CI contract clearly: CI may provide the DB runtime, while the system-test command still owns test-environment creation and verification.
Completion check: the workflow files and docs agree on how GitHub Actions provides Postgres and which single command it runs; the primary command behavior remains consistent between local and CI execution.

6. [ ] [docs]
Files: README.md, app/tests/AGENTS.md
Action: Document the new environment-first testing process as a bridge toward repeatable environment rollout. Make it explicit that the test command builds the environment it needs rather than depending on a standing manual setup, and note how that supports future rollout/new-environment preparation.
Completion check: the docs explicitly describe the environment-first testing process and tie it to repeatable new-environment setup.

## Test impact review

1. [ ] [test]
Files: app/tests/test_startup_lifecycle.py
Action: keep and likely update — this remains the highest-value real startup/backup contract and should continue to run first in the real-system path, but it may need updates if the bootstrap process changes how the environment is prepared.
Completion check: `./.venv/bin/pytest -c app/pytest.ini -q -x app/tests/test_startup_lifecycle.py`

2. [ ] [test]
Files: app/scripts/test-real-failfast.sh
Action: update or replace — this script is no longer just a backend fail-fast check if the repo moves to an environment-building system-test model; validate the final role and rename/document it accordingly.
Completion check: `bash app/scripts/test-real-failfast.sh`

3. [ ] [test]
Files: app/scripts/run_playwright_server.sh, app/scripts/reset_playwright_test_db.py
Action: update — confirm the real browser path uses the same environment/bootstrap assumptions as the new primary system-test command.
Completion check: `cd app/ui && npx playwright test --project=chromium`

4. [ ] [test]
Files: app/ui/e2e/settings.spec.ts
Action: update — confirm the doc classification and any policy language about stubbed coverage still matches this spec’s interception behavior.
Completion check: `cd app/ui && npx playwright test settings.spec.ts --project=stubbed`

5. [ ] [test]
Files: app/ui/e2e/dashboard.spec.ts
Action: update — confirm the doc classification and any policy language about stubbed coverage still matches this spec’s interception behavior.
Completion check: `cd app/ui && npx playwright test dashboard.spec.ts --project=stubbed`

6. [ ] [test]
Files: app/ui/e2e/shell.spec.ts
Action: update — confirm the doc classification and any policy language about stubbed coverage still matches this spec’s interception behavior.
Completion check: `cd app/ui && npx playwright test shell.spec.ts --project=stubbed`

## Testing

1. [ ] [test]
Files: primary system-test command, app/tests/test_startup_lifecycle.py, app/tests/test-artifacts/
Action: Run the primary environment-building real-system command from a state where the dedicated test DB is not assumed to already be running, and verify both terminal output and the machine-readable artifact contract.
Completion check: `bash app/scripts/test-system.sh`

2. [ ] [test]
Files: app/ui/playwright.config.ts, app/ui/e2e/README.md, app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts
Action: Validate the documented stubbed Playwright project and ensure the named stubbed specs still execute under that classification.
Completion check: `cd app/ui && npx playwright test --project=stubbed`

3. [ ] [test]
Files: app/scripts/test-precommit.sh, app/scripts/test-full.sh
Action: After any gate-script changes, rerun the broader gates to confirm the environment-first workflow remains operational.
Completion check: `bash app/scripts/test-precommit.sh && bash app/scripts/test-full.sh`

4. [ ] [test]
Files: .github/workflows/
Action: Validate the GitHub Actions path uses the same primary system-test command and succeeds with the CI-provided database runtime.
Completion check: the relevant GitHub Actions workflow references the same primary command introduced by this task, and the workflow configuration provides the DB runtime required by that command.

## GitHub update

1. [ ] [github]
Files: app/scripts/dev.py, app/scripts/require_test_database.py, app/scripts/reset_playwright_test_db.py, app/scripts/test-real-failfast.sh, app/scripts/test-system.sh, app/scripts/run_playwright_server.sh, app/scripts/test-precommit.sh, app/scripts/test-full.sh, app/ui/playwright.config.ts, app/ui/e2e/README.md, app/ui/e2e/settings.spec.ts, app/ui/e2e/dashboard.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/support/dashboard-settings.ts, .github/workflows/, README.md, app/tests/AGENTS.md, .github/tasks/open/TASK-028-environment-first-real-system-test-workflow.md
Action: When the work is complete, stage the relevant files only and update GitHub using the repo’s required workflow in AGENTS.md#github-update-workflow.
Completion check: `git add app/scripts/dev.py app/scripts/require_test_database.py app/scripts/reset_playwright_test_db.py app/scripts/test-real-failfast.sh app/scripts/test-system.sh app/scripts/run_playwright_server.sh app/scripts/test-precommit.sh app/scripts/test-full.sh app/ui/playwright.config.ts app/ui/e2e/README.md app/ui/e2e/settings.spec.ts app/ui/e2e/dashboard.spec.ts app/ui/e2e/shell.spec.ts app/ui/e2e/support/dashboard-settings.ts .github/workflows README.md app/tests/AGENTS.md .github/tasks/open/TASK-028-environment-first-real-system-test-workflow.md && git commit -m "Build environment-first real system test workflow" && git push`
