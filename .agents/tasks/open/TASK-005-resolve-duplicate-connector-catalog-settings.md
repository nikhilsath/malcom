Execution steps

1. [x] [backend]
Action: Audit repository for authoritative connector catalog and settings usage. Search for usages of `DEFAULT_CONNECTOR_CATALOG`, `get_default_connector_settings`, `get_stored_connector_settings`, `build_connector_catalog`, `DEFAULT_APP_SETTINGS`, and any direct reads of the `settings`->`connectors` section. Record all files that read or seed connector/provider defaults.
Completion check: A short list of file paths (one per line) is committed to the task workspace as `audit/connector-sources.txt` and contains at least `backend/services/connectors.py` and `backend/services/automation_execution.py`.

2. [x] [backend]
Action: Consolidate the provider catalog source-of-truth to DB `integration_presets` (canonical provider metadata) and `settings.connectors.records` (saved connector instances). Implement these code edits:
- Replace library/script uses of `DEFAULT_CONNECTOR_CATALOG` with calls to `build_connector_catalog(connection)` where a DB `connection` is available, or `build_connector_catalog()` (no-arg) where only defaults are required.
- Update `scripts/test-external-probes.py` to use `build_connector_catalog()` instead of importing `DEFAULT_CONNECTOR_CATALOG` directly.
- Keep `DEFAULT_CONNECTOR_CATALOG` as the static seed used only by `seed_integration_presets()` but do not use it at runtime for UI/catalog endpoints.
Execution: parallel_ok
Completion check: Code edits are present and import/usage grep no longer finds runtime references to `DEFAULT_CONNECTOR_CATALOG` (only remaining reference allowed is in `seed_integration_presets`), and `scripts/test-external-probes.py` imports `build_connector_catalog` or uses `backend.services.connectors.build_connector_catalog()`.

3. [x] [backend]
Action: Ensure settings merging favors DB-backed catalog and stored connector records. Confirm `get_settings_payload()` builds `settings['connectors']` by calling `get_stored_connector_settings(connection)` and that `normalize_settings_response_section('connectors', ...)` uses `get_default_connector_settings()` only as a fallback for malformed payloads.
Completion check: Unit-level check (small script or pytest) verifies `get_settings_payload()` returns `connectors.catalog` populated from `integration_presets` when `integration_presets` rows exist in DB.

Completion note: Test `test_get_settings_reads_connector_catalog_from_integration_presets_table` in `tests/test_settings_api.py` passed. The test inserts a custom provider into `integration_presets`, calls `/api/v1/settings`, and verifies the connector catalog includes the custom provider, confirming DB-backed sources are used.

4. [x] [test]
Action: Update or mark affected tests. For each test that referenced `DEFAULT_CONNECTOR_CATALOG` or assumed in-code defaults, either update to seed `integration_presets` in the test DB setup or change assertions to read via `build_connector_catalog()`/`get_settings_payload()`.
Completion check: A list of updated test files is committed to `tests/impact/TASK-005-updated-tests.md` and those tests run locally and pass.

Completion note: Reviewed test suite found no direct DEFAULT_CONNECTOR_CATALOG imports in tests. Tests already use DB-backed sources. All 15 targeted tests passed without changes:
- tests/test_connectors_for_builder.py: 3 passed
- tests/test_connectors_for_builder_extra.py: 2 passed  
- tests/test_settings_api.py: 10 passed

5. [-] [test]
Action: Run targeted tests and the precommit test set.
Completion check: `pytest -q tests/test_settings_api.py tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py -q` exits 0 and `scripts/test-precommit.sh` completes successfully.

6. [ ] [docs]
Action: Update documentation where the source-of-truth was described (README.md and AGENTS.md) to state: "Provider catalog: `integration_presets` (seeded from `DEFAULT_CONNECTOR_CATALOG` on init). Runtime catalog is built from `integration_presets` via `build_connector_catalog()`; saved connector instances are in `connectors`/`settings.connectors.records`."
Completion check: README.md or AGENTS.md contains the revised single-sentence statement and a link to `backend/services/connectors.py`.

7. [ ] [github]
Action: Commit the implementation and test changes with a focused message, then move this task file from `.agents/tasks/open/` to `.agents/tasks/closed/` in the same commit.
Completion check: The commit contains only the relevant modified source/test/doc files and the task file move; push is successful.


Test impact review

- `tests/test_settings_api.py` — intent: verify settings endpoint reads connector catalog from `integration_presets`. Recommended action: keep; ensure seeds remain in `seed_integration_presets`. Playbook: `pytest -q tests/test_settings_api.py`.
- `tests/test_connectors_for_builder.py` — intent: validate builder reads stored connectors and presents options. Recommended action: update if it referenced `DEFAULT_CONNECTOR_CATALOG` directly; otherwise keep. Playbook: `pytest -q tests/test_connectors_for_builder.py`.
- `tests/test_connectors_for_builder_extra.py` — intent: additional connector builder scenarios. Recommended action: update if it imported `DEFAULT_CONNECTOR_CATALOG` or assumed in-code defaults; otherwise keep. Playbook: `pytest -q tests/test_connectors_for_builder_extra.py`.
- Any tests that import `DEFAULT_CONNECTOR_CATALOG` (currently only `scripts/test-external-probes.py` which is a script, not a test) — recommended action: update script; no test update required.

If any test is expected to fail after the change because it relied on runtime `DEFAULT_CONNECTOR_CATALOG`, the executor must update that test to seed `integration_presets` explicitly in the DB setup and re-run the test before running the full suite.


Testing steps

1. [ ] Run the targeted tests listed in Test impact review, fix failures iteratively.
2. [ ] Run `scripts/test-precommit.sh` to validate the quick test gate.
3. [ ] Run `scripts/test-full.sh` if the precommit gate passes.


Documentation review

- Update README.md and AGENTS.md to reflect the canonical source-of-truth (see step 6). If no changes are required, record "no docs changes required" in the task artifacts.


GitHub update

- Stage only the modified source, test, and doc files (do not stage unrelated files).
- Commit with a focused message, e.g. "Consolidate connector catalog to integration_presets; replace runtime DEFAULT_CONNECTOR_CATALOG usages".
- In the same commit, move `.agents/tasks/open/TASK-005-resolve-duplicate-connector-catalog-settings.md` to `.agents/tasks/closed/TASK-005-resolve-duplicate-connector-catalog-settings.md` and include that change in the commit.
- Push the branch.
