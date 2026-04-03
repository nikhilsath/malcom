## Execution steps

1. [x] [db]
Files: requirements.txt, alembic.ini, backend/migrations/env.py, backend/migrations/script.py.mako
Action: Add Alembic as the repo migration system for PostgreSQL. Create `alembic.ini`, a `backend/migrations/` environment, and the standard script template. Configure the migration environment to read the active database URL from the existing backend database configuration rather than introducing a second connection source.
Completion check: `requirements.txt` includes Alembic, `alembic.ini` points `script_location` at `backend/migrations`, and `backend/migrations/env.py` resolves the database URL from the existing backend configuration path.

2. [x] [db]
Files: backend/migrations/versions/0001_baseline_schema.py, backend/database.py
Action: Add a baseline migration that creates the current live PostgreSQL schema, including `settings`, `integration_presets`, `connectors`, `connector_endpoint_definitions`, automations/run tables, scripts, log metadata tables, runtime snapshots, and API resource tables. In `backend/database.py`, add a migration runner helper that later call sites can invoke before seeding.
Completion check: `backend/migrations/versions/0001_baseline_schema.py` exists and contains create/drop logic for `integration_presets`, `connectors`, and `connector_endpoint_definitions`, and `backend/database.py` exports a helper that runs Alembic migrations.

3. [x] [db]
Files: backend/services/automation_execution.py, tests/postgres_test_utils.py, backend/tool_registry.py
Action: Switch application startup, test database reset, and tool-registry DB bootstrap to run the migration helper before seeding settings, presets, or tool metadata. Keep the existing seeding behavior after migration execution.
Completion check: the startup/test/tool-registry call sites in these files invoke the migration helper before seeding, and no new connector/builder schema edits are added to `CREATE_SCHEMA_SQL` or `_ensure_column(...)` as part of this task.

4. [x] [backend]
Files: backend/schemas/settings.py, backend/routes/settings.py, backend/services/automation_execution.py
Action: Remove connector entity records from the app settings contract. `AppSettingsResponse` and `AppSettingsUpdate` should cover only general, logging, notifications, data, automation, and options, and `/api/v1/settings` plus `get_settings_payload()` must stop returning or accepting a `connectors` section.
Completion check: `backend/schemas/settings.py` no longer declares `connectors` in `AppSettingsResponse` or `AppSettingsUpdate`, `backend/routes/settings.py` no longer handles connector writes, and `backend/services/automation_execution.py` no longer injects connectors into the settings payload.

5. [x] [backend]
Files: backend/schemas/settings.py, backend/services/connectors.py
Action: Add dedicated connector request/update models and direct connector service helpers for create, update, delete, and auth-policy writes. Keep `GET /api/v1/connectors` response-compatible for the UI, but stop routing first-party writes through `ConnectorSettingsUpdate` / settings-shaped normalization.
Completion check: `backend/schemas/settings.py` contains dedicated connector create/update/auth-policy request models, and `backend/services/connectors.py` exposes direct CRUD/auth-policy helpers that first-party routes can call without building a whole settings payload.

6. [x] [backend]
Files: backend/routes/connectors.py, backend/routes/settings.py
Action: Add dedicated connector write endpoints: `POST /api/v1/connectors`, `PATCH /api/v1/connectors/{connector_id}`, `DELETE /api/v1/connectors/{connector_id}`, and `PATCH /api/v1/connectors/auth-policy`. Refactor the existing `/test`, `/refresh`, `/revoke`, and OAuth routes to load and persist connector rows through the direct connector helpers instead of settings-shaped wrappers.
Completion check: the new connector write routes exist in `backend/routes/connectors.py`, existing connector action routes use direct connector helpers, and `backend/routes/settings.py` no longer acts as a connector write surface.

7. [x] [ui]
Files: ui/scripts/log-store.js, ui/scripts/settings.js, ui/scripts/settings/connectors/state.js
Action: Split connector data out of the shared settings store. Keep app settings methods for true settings only, and add dedicated connector store methods for loading the connector payload, creating/updating/deleting connectors, and updating connector auth policy.
Completion check: `ui/scripts/log-store.js` no longer stores connector records inside `cachedAppSettings`, `ui/scripts/settings.js` only patches true settings sections, and `ui/scripts/settings/connectors/state.js` reads connector state from dedicated connector store methods instead of `settings.connectors`.

8. [x] [ui]
Files: ui/scripts/settings/connectors/page.js, ui/scripts/settings/connectors/form.js, ui/scripts/settings/connectors/oauth.js, ui/scripts/settings/connectors/render.js
Action: Refactor the connectors settings UI to use the dedicated connector endpoints/store methods. Creating a draft from a preset, editing fields, saving auth policy, deleting a connector, and bootstrapping Google OAuth must all stop cloning and PATCHing the whole settings payload.
Completion check: these files contain no `updateAppSettings(` calls, no direct writes to `settings.connectors.records`, and all create/update/delete/auth-policy actions route through dedicated connector methods or `/api/v1/connectors*` calls.

9. [x] [ui]
Files: ui/scripts/settings/data.js, ui/scripts/log-store.js, ui/scripts/settings/connectors/state.js
Action: Update the settings data page to derive connector-backed storage availability from the dedicated connector payload instead of `getAppSettings()`. Keep local storage location rendering unchanged.
Completion check: `ui/scripts/settings/data.js` no longer reads connector records from the app settings payload and instead renders connector-backed storage from the dedicated connector data source.

10. [x] [backend]
Files: backend/services/connector_activities_catalog.py, backend/services/http_presets.py, backend/services/automation_execution.py, backend/routes/connectors.py
Action: Seed `connector_endpoint_definitions` from the current code-defined connector activity and HTTP preset catalogs, then switch runtime reads for `GET /api/v1/connectors/activity-catalog` and `GET /api/v1/connectors/http-presets` to DB-backed resolver functions. Keep the code catalogs only as seed/default content.
Completion check: the connector activity and HTTP preset route handlers no longer return `CONNECTOR_ACTIVITY_DEFINITIONS` or `DEFAULT_HTTP_PRESET_CATALOG` directly, and `backend/services/automation_execution.py` seeds `connector_endpoint_definitions` from the code catalogs.

11. [x] [ui]
Files: ui/src/automation/builder-api.ts, ui/src/automation/step-modals/connector-activity-step-form.tsx
Action: Keep the automation builder read flow stable while aligning it to the persisted catalogs. The builder must continue to load saved connectors from `/api/v1/automations/workflow-connectors`, activities from `/api/v1/connectors/activity-catalog`, and HTTP presets from `/api/v1/connectors/http-presets`, without introducing new UI-owned provider allowlists or availability rules beyond display-only ordering/labels.
Completion check: these files still consume the canonical builder endpoints and do not add new hardcoded provider option lists or activity availability catalogs in the UI.

12. [x] [test]
Files: tests/test_settings_api.py, tests/test_connectors_api.py, tests/test_connectors_availability.py, tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py, tests/test_automations_api.py, tests/test_connector_activities_api.py, tests/test_http_presets.py, tests/api_smoke_registry/settings_connectors_cases.py, tests/api_smoke_registry/automation_log_cases.py
Action: Update backend contract tests and smoke registry cases to match the new API boundary: `/api/v1/settings` no longer owns connector records, connector CRUD/auth-policy routes are first-class, and activity/preset catalogs are read from persisted definitions.
Completion check: these files assert the dedicated connector routes and catalog behavior directly, and none of them rely on `PATCH /api/v1/settings` for connector record lifecycle.

13. [x] [test]
Files: ui/src/automation/__tests__/fixtures/builder-api-fixtures.ts, ui/e2e/support/api-response-builders.ts, ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx, ui/e2e/support/automations-scripts.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/support/dashboard-settings.ts, ui/e2e/connectors.spec.ts, ui/e2e/automations-builder.spec.ts
Action: Create shared canonical fixture builders for settings, connectors, workflow-builder connector options, connector activity catalog, and HTTP presets, then refactor the React tests and Playwright harnesses to use those helpers instead of handcrafting divergent payloads inline.
Completion check: the new shared fixture helper files exist, the listed unit/e2e harness files import them, and the inline ad hoc endpoint payload objects previously defined in those files are removed or reduced to test-specific overrides.

## Test impact review

1. [x] [test]
Files: tests/test_settings_api.py, tests/test_connectors_api.py, tests/test_connectors_availability.py
Action: Intent: verify the app settings boundary and connector CRUD/auth-policy contracts. Recommended action: update. Validation command: `pytest -q tests/test_settings_api.py tests/test_connectors_api.py tests/test_connectors_availability.py`
Completion check: This task file records the exact files, intent, recommended action, and validation command for this test group.

2. [x] [test]
Files: tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py, tests/test_automations_api.py, tests/test_connector_activities_api.py, tests/test_http_presets.py, tests/api_smoke_registry/settings_connectors_cases.py, tests/api_smoke_registry/automation_log_cases.py
Action: Intent: verify workflow-builder connector options, connector activity catalog, HTTP preset catalog, and API smoke coverage after the storage/source-of-truth refactor. Recommended action: update. Validation command: `pytest -q tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py tests/test_automations_api.py tests/test_connector_activities_api.py tests/test_http_presets.py tests/test_api_smoke_matrix.py`
Completion check: This task file records the exact files, intent, recommended action, and validation command for this test group.

3. [x] [test]
Files: ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Action: Intent: keep React builder tests aligned to the real endpoint contracts after connectors leave `/api/v1/settings` and builder catalogs become DB-backed. Recommended action: update. Validation command: `npm --prefix ui run test -- --run ui/src/automation/__tests__/automation-app.test.tsx ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx`
Completion check: This task file records the exact files, intent, recommended action, and validation command for this test group.

4. [x] [test]
Files: ui/e2e/support/automations-scripts.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/support/dashboard-settings.ts, ui/e2e/connectors.spec.ts, ui/e2e/automations-builder.spec.ts
Action: Intent: keep Playwright route harnesses and end-to-end flows aligned to the canonical settings/connectors/builder response shapes. Recommended action: update. Validation command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts e2e/automations-builder.spec.ts`
Completion check: This task file records the exact files, intent, recommended action, and validation command for this test group.

## Testing steps

1. [x] [test]
Files: tests/test_settings_api.py, tests/test_connectors_api.py, tests/test_connectors_availability.py
Action: Run the targeted backend connector/settings contract tests after the stale assertions are updated. Command: `pytest -q tests/test_settings_api.py tests/test_connectors_api.py tests/test_connectors_availability.py`
Completion check: The command exits 0.

2. [x] [test]
Files: tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py, tests/test_automations_api.py, tests/test_connector_activities_api.py, tests/test_http_presets.py, tests/test_api_smoke_matrix.py
Action: Run the targeted backend builder/catalog/smoke regression suite after the catalog/storage assertions are updated. Command: `pytest -q tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py tests/test_automations_api.py tests/test_connector_activities_api.py tests/test_http_presets.py tests/test_api_smoke_matrix.py`
Completion check: The command exits 0.

3. [x] [test]
Files: ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Action: Run the targeted React builder tests after the canonical fixture builders are wired in. Command: `npm --prefix ui run test -- --run ui/src/automation/__tests__/automation-app.test.tsx ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx`
Completion check: The command exits 0.

4. [x] [test]
Files: ui/e2e/connectors.spec.ts, ui/e2e/automations-builder.spec.ts, ui/e2e/support/automations-scripts.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/support/dashboard-settings.ts
Action: Run the targeted Playwright connector and builder flows after the route harnesses are updated. Command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts e2e/automations-builder.spec.ts`
Completion check: The command exits 0.

5. [x] [test]
Files: scripts/test-precommit.sh
Action: Run the repo precommit validation after the targeted suites pass. Command: `./scripts/test-precommit.sh`
Completion check: The command exits 0.

6. [!] [test]
Files: scripts/test-full.sh, ui/e2e/apis-outgoing.spec.ts, ui/e2e/connectors.spec.ts, ui/e2e/settings.spec.ts, ui/e2e/automations-builder.spec.ts
Action: Run the full validation gate after the precommit suite passes. Command: `./scripts/test-full.sh`. If it fails, run the affected Playwright specs directly to confirm whether the failure is a known cross-browser E2E regression in the current branch before rerunning the full gate.
Completion check: `./scripts/test-full.sh` exits 0.
Blocker: `./scripts/test-full.sh` exits 1 with 12 Playwright failures (141 passed) across Chromium/Firefox/WebKit, concentrated in `e2e/apis-outgoing.spec.ts` and `e2e/settings.spec.ts`. Direct rerun of affected specs (`npm --prefix ui run test:e2e -- e2e/apis-outgoing.spec.ts e2e/settings.spec.ts`) reproduces the same 12 cross-browser failures (`toHaveValue` empty select values in workspace/notifications settings and `toHaveText` mismatch for logging totals), so full gate remains blocked pending UI/e2e fixture alignment.

## Documentation review

1. [x] [docs]
Files: README.md, AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md, scripts/check-policy.sh
Action: Update documentation and policy text to reflect migration-based schema ownership, connectors as first-class DB entities outside app settings, and `connector_endpoint_definitions` as the persisted source for builder activity/preset catalogs. If `AGENTS.md` changes, update `scripts/check-policy.sh` in the same step.
Completion check: The listed docs describe the new connector/settings and migration boundaries, and any `AGENTS.md` edits are accompanied by a matching `scripts/check-policy.sh` update.

## GitHub update

1. [x] [github]
Files: .agents/tasks/open/TASK-007-finish-connector-db-boundary-and-builder-catalogs.md, requirements.txt, alembic.ini, backend/migrations/env.py, backend/migrations/script.py.mako, backend/migrations/versions/0001_baseline_schema.py, backend/database.py, backend/services/automation_execution.py, backend/services/connectors.py, backend/services/connector_activities_catalog.py, backend/services/http_presets.py, backend/routes/settings.py, backend/routes/connectors.py, backend/schemas/settings.py, tests/postgres_test_utils.py, backend/tool_registry.py, ui/scripts/log-store.js, ui/scripts/settings.js, ui/scripts/settings/data.js, ui/scripts/settings/connectors/state.js, ui/scripts/settings/connectors/page.js, ui/scripts/settings/connectors/form.js, ui/scripts/settings/connectors/oauth.js, ui/scripts/settings/connectors/render.js, ui/src/automation/builder-api.ts, ui/src/automation/step-modals/connector-activity-step-form.tsx, ui/src/automation/__tests__/fixtures/builder-api-fixtures.ts, ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx, ui/e2e/support/api-response-builders.ts, ui/e2e/support/automations-scripts.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/support/dashboard-settings.ts, ui/e2e/connectors.spec.ts, ui/e2e/automations-builder.spec.ts, tests/test_settings_api.py, tests/test_connectors_api.py, tests/test_connectors_availability.py, tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py, tests/test_automations_api.py, tests/test_connector_activities_api.py, tests/test_http_presets.py, tests/api_smoke_registry/settings_connectors_cases.py, tests/api_smoke_registry/automation_log_cases.py, README.md, AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md, scripts/check-policy.sh
Action: Skipped per user instruction for this run (no staging/commit/push). Task closure is tracked locally by documentation completion and moving this task file to `.agents/tasks/closed/`.
Completion check: Docs are updated and this task file is moved to `.agents/tasks/closed/` without performing git commit/push.
