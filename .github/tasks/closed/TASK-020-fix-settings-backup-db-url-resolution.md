Execution steps

1. [x] [backend]
Files: backend/routes/settings.py
Action: Update backup route handlers to use the app runtime database URL instead of relying on environment lookup inside backup services. Pass `request.app.state.database_url` into `support.create_backup(...)` and `support.restore_backup(...)` for `POST /api/v1/settings/data/backups` and `POST /api/v1/settings/data/backups/restore`.
Completion check: `create_settings_backup` and `restore_settings_backup` both pass an explicit `db_url` argument sourced from `request.app.state.database_url` in backend/routes/settings.py.

2. [x] [backend]
Files: backend/services/settings_backup_restore.py
Action: Harden database URL resolution so direct service calls do not fail when `MALCOM_DATABASE_URL` is unset but the app uses default DB resolution. Replace strict env-only fallback with canonical backend DB resolver (`backend.database.get_database_url`) while preserving optional explicit `db_url` override behavior.
Completion check: `_get_database_url` resolves `db_url` first and otherwise falls back to `get_database_url()` rather than raising the current "No database URL provided..." error for normal runtime calls.

2. [x] [test]
Files: tests/test_settings_api.py
Action: Add regression coverage proving backup create and restore routes pass explicit runtime DB URL into support-layer calls and do not depend on `MALCOM_DATABASE_URL` being set in the process environment.
Completion check: tests assert mocked `backend.services.support.create_backup` and `backend.services.support.restore_backup` receive the expected `db_url` argument from app state.
Execution note: Ran `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "settings-backup"` and it passed (3 passed, 111 deselected).
Execution note: Ran `./.venv/bin/python -m pytest -q tests/test_settings_api.py -k "backup"` and it passed (2 passed, 7 deselected).

4. [x] [test]
Files: tests/api_smoke_registry/settings_connectors_cases.py
Action: Verify the existing smoke cases for settings backup routes remain accurate after DB URL resolution changes; only edit this file if route contract/shape changed.
Completion check: Either no diff is needed because smoke coverage already matches current routes, or any required route-contract updates are applied in tests/api_smoke_registry/settings_connectors_cases.py.
Execution note: No diff needed; settings-backup smoke cases already match current route contract and response shape.

Test impact review

1. [x] [test]
Files: tests/test_settings_api.py
Action: Intent: keep settings backup API regression coverage aligned with runtime DB URL resolution used by the Settings Data UI flow. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_settings_api.py -k "backup"`.
Completion check: Backup-focused settings API tests pass and include the new regression assertion(s).
Execution note: Ran `./.venv/bin/python -m pytest -q tests/test_settings_api.py -k "backup"` and it passed (2 passed, 7 deselected).

2. [x] [test]
Files: tests/api_smoke_registry/settings_connectors_cases.py, tests/test_api_smoke_matrix.py
Action: Intent: preserve smoke coverage for `/api/v1/settings/data/backups*` endpoints while implementation details change. Recommended action: keep (update only if request/response contract changed). Validation command (if updated): `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "settings-backup"`.
Completion check: Smoke route coverage for settings backup endpoints remains present and passing.
Execution note: No registry diff required; ran `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "settings-backup"` and it passed (3 passed, 111 deselected).

3. [x] [test]
Files: ui/e2e/settings.spec.ts, ui/e2e/support/dashboard-settings.ts
Action: Intent: maintain browser-level confidence for create/restore backup UX messaging. Recommended action: keep (no edit expected unless route contract changed).
Completion check: No fixture/test edit required if API contract is unchanged; existing e2e coverage remains valid.
Execution note: Verified UI e2e fixtures and handlers already use `backup_id` and include backup metadata; no edits required.

Testing steps

1. [x] [test]
Files: tests/test_settings_api.py
Action: Run targeted backup-related settings API tests after implementing runtime DB URL wiring.
Completion check: `./.venv/bin/python -m pytest -q tests/test_settings_api.py -k "backup"` exits 0.
Execution note: Ran `./.venv/bin/python -m pytest -q tests/test_settings_api.py -k "backup"` and it passed (2 passed, 9 deselected).

2. [x] [test]
Files: tests/test_api_smoke_matrix.py, tests/api_smoke_registry/settings_connectors_cases.py
Action: Run targeted smoke validation for settings backup routes to confirm route contract continuity.
Completion check: `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "settings-backup"` exits 0.
Execution note: Ran `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "settings-backup"` and it passed (3 passed, 112 deselected).

3. [x] [test]
Files: scripts/test-precommit.sh
Action: Run the fast cross-stack validation gate after targeted tests pass.
Completion check: `./scripts/test-precommit.sh` exits 0, or blocker details are captured in task execution notes if unrelated failures occur.
Execution note: Startup lifecycle regression is fixed and targeted backup/smoke tests pass.
Execution note: After follow-up UI automation test remediation, `./scripts/test-precommit.sh` now exits 0 end-to-end (backend pytest, UI route coverage, UI vitest, and UI build all pass).

Documentation review

1. [x] [docs]
Files: README.md, docs/settings-reference.md
Action: Review backup wording for DB URL resolution assumptions; if needed, update docs to state backup operations use the app runtime database URL (resolved via backend database configuration) rather than requiring ad hoc env checks at request time.
Completion check: Either documentation is updated in README.md and docs/settings-reference.md to match implementation, or execution notes explicitly record that no doc text change is required.
Execution note: Reviewed wording; no documentation text change required for this task because implementation behavior already aligns with current docs phrasing.

GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-020-fix-settings-backup-db-url-resolution.md, backend/routes/settings.py, backend/services/settings_backup_restore.py, tests/test_settings_api.py, tests/api_smoke_registry/settings_connectors_cases.py, README.md, docs/settings-reference.md
Action: Stage only task-relevant files, commit with a focused message, push, and move this task file to `.github/tasks/closed/` in the same commit.
Completion check: `git status` shows only intended files staged, commit and push succeed, and the task file is relocated from open to closed in the committed diff.