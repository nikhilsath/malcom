## Execution steps

1. [x] [connector]
Files: app/backend/services/connector_activities_catalog.py, app/backend/services/connector_activities_runtime.py, app/backend/services/connector_activities_notion.py, app/backend/services/connector_activities_trello.py
Action: Add provider-specific Notion and Trello connector activity definitions plus runtime handlers, and register them in the canonical catalog/runtime registries (AGENTS.md#connector-and-tool-boundary, R-ARCH-001; AGENTS.md#implementation-quality-and-source-of-truth, R-SOT-001).
Completion check: Catalog registry includes Notion and Trello activity definitions, and runtime handler registry resolves their execution kinds.

2. [x] [connector]
Files: app/backend/services/http_presets.py, app/backend/services/automation_execution.py
Action: Add Notion and Trello HTTP preset definitions and ensure `seed_connector_endpoint_definitions` persists them into `connector_endpoint_definitions` so builder/API resolvers expose DB-backed catalogs.
Completion check: `DEFAULT_HTTP_PRESET_CATALOG` includes Notion and Trello presets, and seeding path writes endpoint IDs for both providers.

3. [x] [test]
Files: app/tests/test_connector_activities_api.py, app/tests/test_http_presets.py, app/tests/test_http_preset_automations.py
Action: Add/update tests to assert Notion and Trello activity catalog entries, HTTP preset availability, and validation behavior for preset-mode automations using those providers.
Completion check: Each listed test file includes explicit Notion/Trello assertions rather than only Google/GitHub coverage.

4. [x] [docs]
Files: README.md
Action: Remove or rewrite the unfinished-features bullet that says Notion/Trello connectors are generic-only in builder catalogs.
Completion check: README no longer states Notion and Trello lack provider-specific activities/presets.
Blocker: none.

## Test impact review

1. [x] [test]
Files: app/tests/test_connector_activities_api.py
Action: Intent: verify `/api/v1/connectors/activity-catalog` includes provider-aware Notion and Trello actions; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_connector_activities_api.py`.
Completion check: Activity-catalog assertions include Notion and Trello provider/activity IDs.

2. [x] [test]
Files: app/tests/test_http_presets.py
Action: Intent: verify Notion/Trello preset definitions and schema fields in catalog resolvers; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_http_presets.py`.
Completion check: Preset tests assert provider coverage beyond Google/GitHub.

3. [x] [test]
Files: app/tests/test_http_preset_automations.py
Action: Intent: verify automation validation accepts and enforces Notion/Trello preset-mode step rules; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_http_preset_automations.py`.
Completion check: Preset-mode automation tests include at least one Notion/Trello preset scenario.

## Testing

1. [x] [test]
Files: app/tests/test_connector_activities_api.py, app/tests/test_http_presets.py, app/tests/test_http_preset_automations.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_connector_activities_api.py app/tests/test_http_presets.py app/tests/test_http_preset_automations.py`.
Completion check: Command exits with status 0.

2. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as first-pass real-system verification.
Completion check: Command exits with status 0.
Blocker: none.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-034-add-notion-trello-provider-catalogs.md, app/backend/services/connector_activities_catalog.py, app/backend/services/connector_activities_runtime.py, app/backend/services/connector_activities_notion.py, app/backend/services/connector_activities_trello.py, app/backend/services/http_presets.py, app/backend/services/automation_execution.py, app/tests/test_connector_activities_api.py, app/tests/test_http_presets.py, app/tests/test_http_preset_automations.py, README.md
Action: Stage only relevant files and run `git add <files> && git commit -m "Add Notion and Trello builder activity and preset catalogs" && git push` per AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit and `git status --short` is clean for the listed files.
