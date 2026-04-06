Execution steps

1. [x] 1 - route: repo
Files: test-artifacts/, test-results/, tests/
Action: Move the top-level `test-artifacts/` and `test-results/` directories into the `tests/` folder so they become `tests/test-artifacts/` and `tests/test-results/`. Update any scripts, CI config, or code that reference the old top-level paths to the new locations.
Completion check: Both `tests/test-artifacts/` and `tests/test-results/` exist and there are no remaining `test-artifacts/` or `test-results/` directories at the repository root. A grep for the old path strings returns no remaining references.
Result: Verified `tests/test-artifacts/` and `tests/test-results/` exist; verified no top-level `test-artifacts/` or `test-results/` directories remain.

2. [x] 2 - route: repo
Files: scripts/, pytest.ini, tests/, .github/workflows/
Action: Update scripts, `pytest.ini`, CI workflows and any other configuration files to point to the new `tests/test-artifacts` and `tests/test-results` paths. If path constants are centralized, update them there.
Completion check: No files in the repo reference the old top-level paths (`test-artifacts/` or `test-results/`).
Note: Per repository modularization rules (TASK-019), include any test or test-organization changes and a short module-contract note under `.agents/module-contracts/` in the same PR if the change constitutes a module boundary.
Result: Searched repo-owned files with `grep -RIn --exclude-dir=node_modules --exclude-dir=ui/node_modules` and found no remaining references.


Test impact review

1. [x] 1 - route: test
Files: tests/, pytest.ini, scripts/test-precommit.sh, scripts/test-full.sh
Action: Review tests and precommit/full test scripts for any assumptions about artifact/result locations; enumerate impacted tests and update expectations where needed.
Completion check: A short list of impacted tests and required changes is appended to this task file under an "Impacted tests" note.
Additional completion check: Any updated/renamed tests are added/modified in the same PR and, where applicable, a short module contract file is added under `.agents/module-contracts/` documenting the new test organization.
Result: Reviewed artifact path assumptions in test scripts and smoke/e2e outputs. No additional path rewrites required.

Impacted tests

- `tests/test_api_smoke_matrix.py`: indirectly impacted only through full-suite execution order; no artifact-path change required.
- `ui/e2e/**`: outputs already use `test-results/` under UI workspace conventions; no root path dependency in repo-owned test logic.
- `scripts/test-precommit.sh` and `scripts/test-full.sh`: validated current behavior against `tests/test-artifacts` and `tests/test-results` layout.


Testing steps

1. [x] 1 - route: test
Files: scripts/test-precommit.sh, scripts/test-full.sh
Action: Run `./scripts/test-precommit.sh` (fast smoke) and then the broader `./scripts/test-full.sh` (or CI equivalent) to confirm no regressions caused by the path changes.
Completion check: Both commands exit cleanly (exit code 0) or CI passes for the changed commit. Record results in this task file.
Result: `./scripts/test-precommit.sh` passed. `./scripts/test-full.sh` passed, including full backend pytest, UI unit tests, UI build, API smoke matrix, and Playwright e2e.


Documentation review

1. [x] 1 - route: docs
Files: README.md, AGENTS.md, docs/, scripts/
Action: Update README, `AGENTS.md`, and any docs or developer notes that referenced the old top-level locations to reference the new `tests/`-scoped locations.
Completion check: No user-facing docs reference `test-artifacts/` or `test-results/` at the repo root.
Result: Verified no user-facing docs reference old root-level paths.


GitHub update

1. [ ] 1 - route: github
Files: tests/test-artifacts/, tests/test-results/, updated scripts and CI files, this task file
Action: Stage only the moved directories and updated files, commit with message "Move test-artifacts and test-results into tests/ and update references", push the branch, and move this task file from `.github/tasks/open/` to `.github/tasks/closed/` in the same commit.
Completion check: Commit and push succeed and the task file resides in `.github/tasks/closed/` in the pushed commit.

---

Notes:
- Keep the change scoped: do not modify test code behavior unless necessary to update paths.
- If there are large binary artifacts that should remain in an artifacts storage (not in Git), open a follow-up task to move them to proper storage and leave lightweight references in the repo.

