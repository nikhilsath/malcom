## Execution steps

1. [x] [scripts]
Files: app/scripts/dev.py, app/scripts/test-precommit.sh, app/scripts/test-full.sh
Action: Extend the existing developer/test entrypoints so the separate `frontend/` workspace is treated as a first-class module alongside `app/ui/`, including dependency install/build/test hooks without removing the current legacy UI compatibility path.
Completion check: `app/scripts/dev.py`, `app/scripts/test-precommit.sh`, and `app/scripts/test-full.sh` all contain explicit `frontend/` workspace install/build/test handling in addition to the existing `app/ui/` flow.

2. [x] [test]
Files: app/tests/test_dev_launcher.py, app/tests/test_frontend_platform_structure.py
Action: Update launcher and structure coverage so the repo fails when the hosted frontend workspace is omitted from the bootstrap/tooling path.
Completion check: `app/tests/test_dev_launcher.py` asserts the launcher runs hosted-frontend bootstrap steps, and `app/tests/test_frontend_platform_structure.py` asserts the separate workspace contract expected by the scripts.

## Test impact review

1. [x] [test]
Files: app/tests/test_dev_launcher.py
Action: Intent: verify the main launcher/bootstrap flow includes hosted frontend workspace preparation; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_dev_launcher.py`.
Completion check: Launcher tests assert hosted frontend bootstrap steps alongside the legacy UI path.

2. [x] [test]
Files: app/tests/test_frontend_platform_structure.py
Action: Intent: verify the separate `frontend/` workspace remains present and correctly shaped for tooling; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_frontend_platform_structure.py`.
Completion check: Structure tests cover the files and package metadata relied on by the scripts.

3. [x] [test]
Files: frontend/packages/sdk/src/index.test.mjs, frontend/packages/host/src/plugin-runtime.test.mjs
Action: Intent: preserve hosted frontend package-level test coverage while scripts begin invoking the separate workspace; Recommended action: keep.
Completion check: Existing frontend package tests remain the canonical lightweight frontend workspace checks.

## Testing steps

1. [x] [test]
Files: app/tests/test_dev_launcher.py, app/tests/test_frontend_platform_structure.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_dev_launcher.py app/tests/test_frontend_platform_structure.py`.
Completion check: Command exits with status 0.

2. [x] [test]
Files: frontend/package.json, frontend/packages/sdk/src/index.test.mjs, frontend/packages/host/src/plugin-runtime.test.mjs
Action: Run `cd frontend && npm test`.
Completion check: Command exits with status 0.

3. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the required first-pass real-system validation before any broader gate per AGENTS.md#real-test-first-pass-policy (R-TEST-009).
Completion check: Command exits with status 0.
Execution note: `bash app/scripts/test-real-failfast.sh` passed after hosted-frontend browser contract/test updates; startup lifecycle, backend suite, and critical browser checks all completed successfully.

## Documentation review

1. [x] [docs]
Files: README.md, frontend/README.md, data/docs/frontend-plugin-sdk.md
Action: Update operator/developer docs to describe how the hosted frontend workspace is installed, tested, and launched during the migration, following AGENTS.md#documentation-ownership-model (R-DOC-001).
Completion check: README and frontend docs both include the hosted frontend setup/test flow and no longer imply `app/ui/` is the only frontend workspace.

