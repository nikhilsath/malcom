Execution steps

1. [x] [backend]
Files: backend/schemas/settings.py, backend/schemas/__init__.py
Action: Add settings backup/restore API schemas for request and response payloads, including create-backup response metadata, list-backups response metadata, and restore request/response models used by new settings data endpoints.
Completion check: New schema classes are exported through backend/schemas/settings.py and available via backend/schemas/__init__.py for route imports without runtime import errors.

2. [x] [backend]
Files: backend/services/settings_backup_restore.py, backend/services/support.py
Action: Implement a dedicated service module for local PostgreSQL backup/restore operations. Include helpers to resolve a local backup directory under the repo, create timestamped dump filenames, execute pg_dump and pg_restore safely, and enumerate restore candidates sorted newest-first. Wire the module into backend/services/support.py exports.
Completion check: backend/services/settings_backup_restore.py exists with callable functions for create/list/restore operations, and backend/routes can import these functions from backend.services.support.

3. [x] [backend]
Files: backend/routes/settings.py
Action: Add settings data backup routes for create, list, and restore flows (for example: POST /api/v1/settings/data/backups, GET /api/v1/settings/data/backups, POST /api/v1/settings/data/backups/restore). Route handlers must call the new service functions and return typed schema responses with clear error messages when pg_dump/pg_restore is unavailable or execution fails.
Completion check: backend/routes/settings.py contains the three new /api/v1/settings/data/backups* route handlers with response_model declarations and service calls.

4. [x] [test]
Files: tests/test_settings_api.py, tests/api_smoke_registry/settings_connectors_cases.py
Action: Update backend tests before broad verification: add API tests for backup create/list/restore route behavior with subprocess and filesystem interactions mocked, then add smoke registry cases for each new settings backup route.
Completion check: tests/test_settings_api.py includes deterministic tests for create/list/restore success and failure branches, and tests/api_smoke_registry/settings_connectors_cases.py includes smoke cases covering each new route signature.

5. [x] [ui]
Files: ui/settings/data.html, ui/scripts/settings/data.js, ui/styles/pages/settings.css
Action: Add a local database backup management section on Settings Data with deterministic IDs for: backup directory display, create-backup button, backup list selector, restore trigger button, and route-specific feedback area. Implement client-side handlers to load backup list, trigger create, and trigger restore with explicit user confirmation.
Completion check: ui/settings/data.html includes the new backup/restore controls, ui/scripts/settings/data.js performs GET/POST calls to /api/v1/settings/data/backups endpoints, and settings page styles render the new controls without breaking existing data/log-storage sections.

6. [x] [test]
Files: ui/e2e/support/dashboard-settings.ts, ui/e2e/settings.spec.ts
Action: Extend settings e2e fixtures to mock new backup endpoints and add a settings data browser test that validates create-backup and restore interactions (including confirmation handling and feedback rendering).
Completion check: ui/e2e/support/dashboard-settings.ts contains route handlers for the new backup endpoints, and ui/e2e/settings.spec.ts asserts the end-to-end backup/restore UI behavior on /settings/data.html.

Test impact review

1. [x] [test]
Files: tests/test_settings_api.py
Action: Intent: validate new settings data backup endpoints (create/list/restore), including command availability and command failure handling. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_settings_api.py -q
Completion check: New and existing settings API tests pass with deterministic mocks and no external pg_dump dependency.

2. [x] [test]
Files: tests/api_smoke_registry/settings_connectors_cases.py, tests/test_api_smoke_matrix.py
Action: Intent: keep smoke matrix aligned with all served /api/v1/** routes after adding backup endpoints. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -m smoke
Completion check: Smoke matrix includes cases for each new backup route and reports no missing route coverage.

3. [x] [test]
Files: ui/e2e/support/dashboard-settings.ts, ui/e2e/settings.spec.ts
Action: Intent: verify user-visible Settings Data backup/restore workflow. Recommended action: update. Validation command: cd ui && npx playwright test e2e/settings.spec.ts --trace on
Completion check: Settings e2e test covers create-backup and restore interactions and passes with fixture-backed API routes.

Testing steps

1. [x] [test]
Files: tests/test_settings_api.py
Action: Run targeted backend API tests for settings routes after implementing create/list/restore endpoint and mock-based service behavior.
Completion check: ./.venv/bin/python -m pytest -q tests/test_settings_api.py -q exits 0.
Blocker: Tests previously failed due to routes using direct imports; switched routes to module-qualified calls and normalized returned metadata. Tests now pass locally.

2. [x] [test]
Files: tests/api_smoke_registry/settings_connectors_cases.py, tests/test_api_smoke_matrix.py
Action: Run smoke matrix to confirm coverage and behavior for newly added /api/v1/settings/data/backups* routes.
Completion check: ./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -m smoke exits 0 and reports no missing routes.

3. [x] [test]
Files: ui/e2e/support/dashboard-settings.ts, ui/e2e/settings.spec.ts
Action: Rebuild the UI bundle, then run targeted Settings e2e coverage for the backup/restore UX behavior.
Completion check: cd ui && npm run build && npm run test:e2e -- e2e/settings.spec.ts --grep "creates and restores a local backup" exits 0.
4. [!] [test]
Files: scripts/test-precommit.sh
Action: Run the fast cross-stack validation gate after targeted tests are green.
Completion check: ./scripts/test-precommit.sh exits 0.
Blocker: Current mixed worktree still fails on unrelated automation preset validation (`tests/test_http_preset_automations.py::test_http_preset_mode_missing_scopes_validation`).

5. [!] [test]
Files: scripts/test-full.sh
Action: Run the full completion gate once stale tests are already updated and passing.
Completion check: bash ./scripts/test-full.sh exits 0.
Blocker: Not attempted because the fast gate is already blocked by the unrelated automation preset failure above.

Documentation review

1. [x] [docs]
Files: README.md
Action: Update the Settings Data documentation to describe local backup creation and restore workflow, clarify that backups are stored on the developer machine, and document pg_dump/pg_restore requirement plus error expectations when binaries are missing.
Completion check: README.md contains a dedicated note for Settings Data local backup/restore behavior and local-machine storage location semantics.

GitHub update

1. [x] [github]
Files: .agents/tasks/closed/TASK-006-local-backup-button-and-restore-flow.md, backend/routes/settings.py, backend/services/settings_backup_restore.py, backend/services/support.py, backend/schemas/settings.py, backend/schemas/__init__.py, tests/test_settings_api.py, tests/api_smoke_registry/settings_connectors_cases.py, ui/settings/data.html, ui/scripts/settings/data.js, ui/styles/pages/settings.css, ui/e2e/support/dashboard-settings.ts, ui/e2e/settings.spec.ts, README.md
Action: Stage only files relevant to this backup/restore feature, commit with a focused message, push, and move this task file from open to closed in the same commit.
Completion check: git status shows only task-relevant tracked changes included in one commit, the task file is moved to .agents/tasks/closed, and git push succeeds after commit.
