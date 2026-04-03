## Execution steps

1. [x] [db]
Files: backend/database.py, backend/migrations/versions/0001_baseline_schema.py
Action: Add dedicated relational tables for settings domains that currently live in settings JSON but belong to other backend domains: `tool_configs` (one row per tool_id with config JSON) and `connector_auth_policies` (workspace-level connector auth policy row). Keep existing `settings` table unchanged for now to allow staged migration.
Completion check: Both schema files define `tool_configs` and `connector_auth_policies`, and each table is created during DB initialization/migration without relying on `settings` rows.

2. [x] [backend]
Files: backend/services/automation_execution.py, backend/services/tool_runtime.py, backend/services/tool_configs.py
Action: Migrate managed tool runtime config persistence (`smtp_tool`, `local_llm_tool`, `coqui_tts_tool`, `image_magic_tool`) from `settings` key/value rows to `tool_configs`. Implement backward-compatible read migration (fallback to legacy `settings` key once, write into `tool_configs`, then remove migrated legacy key) so existing workspaces keep their current tool configs.
Completion check: Tool config get/save functions no longer execute `SELECT/INSERT ... FROM/INTO settings WHERE key IN ('smtp_tool','local_llm_tool','coqui_tts_tool','image_magic_tool')` except explicit one-time migration fallback paths.

3. [x] [backend]
Files: backend/routes/tools.py, backend/routes/workers.py, backend/services/automation_execution.py, backend/tool_registry.py
Action: Remove dual source-of-truth for managed tool enabled state by making `tools.enabled` authoritative and treating per-tool config blobs as non-authoritative for enabled status. Ensure directory and tool detail responses derive enabled state from `tools` table consistently, and PATCH handlers keep `tools.enabled` synchronized without requiring duplicated enabled persistence in config blobs.
Completion check: Managed tool responses and `/api/v1/tools` directory return enabled values from `tools.enabled`; toggling enabled state updates `tools` table and remains consistent across directory and tool-specific endpoints.

4. [x] [backend]
Files: backend/services/connectors.py, backend/services/settings.py
Action: Move connector auth policy persistence off `settings.connector_auth_policy` into `connector_auth_policies`, with legacy read/migrate/delete support for existing rows. Keep `/api/v1/connectors/auth-policy` API contract unchanged.
Completion check: Connector auth policy reads/writes no longer depend on `settings` as the primary store; legacy `connector_auth_policy` in `settings` is only read during migration and then removed.

5. [x] [test]
Files: tests/postgres_test_utils.py, tests/test_tools_api.py, tests/test_connectors_api.py, tests/test_settings_api.py, tests/api_smoke_registry/tools_cases.py, tests/api_smoke_registry/settings_connectors_cases.py
Action: Update tests and test fixtures for the new storage layout, including DB reset truncation list, tool config persistence assertions, and connector auth policy persistence expectations. Keep endpoint contracts intact while replacing settings-table-specific assertions with assertions against `tool_configs` and `connector_auth_policies`.
Completion check: Updated tests no longer assume tool configs or connector auth policy are persisted in `settings` rows.

## Test impact review

1. [x] [test]
Files: tests/test_tools_api.py
Action: Intent: verify managed tool GET/PATCH endpoints still behave the same while persistence moves from `settings` rows to `tool_configs` and enabled source is unified to `tools.enabled`. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_tools_api.py`
Completion check: Test coverage asserts endpoint behavior and DB writes without relying on settings-key storage for tool runtime configs.

2. [x] [test]
Files: tests/test_connectors_api.py
Action: Intent: preserve connector auth-policy API behavior while persistence moves from `settings` to `connector_auth_policies`. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py`
Completion check: Auth-policy route tests pass with assertions aligned to the new table-backed persistence.

3. [x] [test]
Files: tests/test_settings_api.py
Action: Intent: keep `/api/v1/settings` contract stable while ensuring connector/tool storage migration no longer leaks as settings-backed source-of-truth assumptions. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_settings_api.py`
Completion check: Settings API tests no longer require tool runtime configs or connector auth policy to be stored in `settings`.

4. [x] [test]
Files: tests/postgres_test_utils.py
Action: Intent: ensure test DB resets truncate newly added tables so test isolation remains deterministic. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_startup_lifecycle.py`
Completion check: Test reset/setup runs cleanly with the new tables included in truncation flow.

5. [x] [test]
Files: tests/api_smoke_registry/tools_cases.py, tests/api_smoke_registry/settings_connectors_cases.py, tests/test_api_smoke_matrix.py
Action: Intent: preserve smoke coverage for tools/settings/connectors workflows after storage migration. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "tools or connectors or settings"`
Completion check: Smoke matrix still validates the affected routes with updated setup expectations.

## Testing steps

1. [x] [test]
Files: tests/test_tools_api.py, tests/test_connectors_api.py, tests/test_settings_api.py
Action: Run focused backend tests for migrated persistence domains. Command: `./.venv/bin/python -m pytest -q tests/test_tools_api.py tests/test_connectors_api.py tests/test_settings_api.py`
Completion check: The command exits 0.

2. [x] [test]
Files: tests/test_api_smoke_matrix.py, tests/api_smoke_registry/tools_cases.py, tests/api_smoke_registry/settings_connectors_cases.py
Action: Run smoke regression focused on tools/connectors/settings routes. Command: `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k "tools or connectors or settings"`
Completion check: The command exits 0.

3. [x] [test]
Files: scripts/test-precommit.sh
Action: Run the precommit gate after targeted suites pass. Command: `./scripts/test-precommit.sh`
Completion check: The command exits 0.

## Documentation review

1. [x] [docs]
Files: README.md, AGENTS.md, scripts/check-policy.sh
Action: Update schema and data-lineage documentation to reflect that managed tool runtime configs are persisted in `tool_configs` and connector auth policy in `connector_auth_policies`, while `settings` remains for app-level settings sections only. Keep policy/script synchronization intact if AGENTS schema text changes.
Completion check: README and AGENTS database documentation match the implemented tables and ownership, and `scripts/check-policy.sh` is updated in the same change if AGENTS policy enforcement expectations changed.

## GitHub update

1. [ ] [github]
Files: .agents/tasks/open/TASK-010-reduce-settings-table-source-of-truth-duplication.md, backend/database.py, backend/migrations/versions/0001_baseline_schema.py, backend/services/automation_execution.py, backend/services/tool_runtime.py, backend/services/tool_configs.py, backend/routes/tools.py, backend/routes/workers.py, backend/services/connectors.py, backend/services/settings.py, tests/postgres_test_utils.py, tests/test_tools_api.py, tests/test_connectors_api.py, tests/test_settings_api.py, tests/api_smoke_registry/tools_cases.py, tests/api_smoke_registry/settings_connectors_cases.py, README.md, AGENTS.md, scripts/check-policy.sh
Action: Stage only task-relevant files, commit with a focused message such as `Migrate tool and connector policy storage off settings table`, move this task file to `.agents/tasks/closed/` in the same commit, then push.
Completion check: Commit includes only relevant implementation/test/doc files plus the task-file move to `.agents/tasks/closed/`, and push succeeds.
