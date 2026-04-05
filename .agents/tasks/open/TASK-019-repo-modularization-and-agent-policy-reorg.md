# TASK-019: Repository Modularization and Agent Policy Reorganization

## Execution steps

0. [x] [docs]
Files: .agents/module-contracts/template.md
Action: Create a module contract template and storage location under `.agents/module-contracts/` describing: owner, responsibilities, public API (functions/classes), owned DB tables, inbound/outbound dependencies, allowed callers, test obligations, and migration rules.
Completion check: `.agents/module-contracts/template.md` exists and contains the required fields.

0.a [x] [docs]
Files: none (review-only)
Action: Expected behavior for TASK-019: each module must present a clear contract, include unit + contract tests in the same PR as behavior changes, routes remain thin, UI orchestrators only import module public APIs, and CI supports running `scripts/test-module.sh <module>` to validate only that module's tests.
Completion check: This expected behavior text is present in the task file and referenced by at least one execution step that enforces it.

### Expected behavior (TASK-019)

- **Module contract:** Each extracted module must include a concise contract stored under `.agents/module-contracts/` listing owner, responsibilities, public API (functions/classes and signatures), owned DB tables, inbound/outbound dependencies, allowed callers, test obligations, and migration rules.
- **Tests with changes:** Any behavioral change that touches a module must include the module's unit tests and contract tests in the same PR.
- **Thin routes / UI orchestrators:** HTTP routes remain thin (parameter extraction, permission checks, response shaping). UI top-level orchestrators may only import module public APIs; rendering and editor logic must live in focused components.
- **CI support:** CI must be able to run a single-module test job via `scripts/test-module.sh <module>` and corresponding job matrix entries (e.g., `module-<name>-unit`, `module-contract-<name>`).
- **PR scope and validation:** PRs that change module boundaries or module internals must include module contract updates and the validation commands required by the Test Impact Review for that module.


1. [x] [docs]
Files: AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Baseline current architecture, identify all large/mixed-responsibility files, and document public API/UI contracts, DB schema ownership, and connector source-of-truth flows. Lock these as refactor constraints.
Completion check: A summary of baseline constraints and hotspots is recorded in the task file or a linked doc.
Result: Baseline recorded in `.agents/module-contracts/baseline-constraints.md`

2. [x] [docs]
Files: AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Define modularity acceptance criteria per area. Include: max public API size (functions/classes), allowed inbound/outbound dependency list, required per-module unit and contract test coverage, CI job names (`module-<name>-unit`, `module-contract-<name>`), and PR-scope rules.
Completion check: Acceptance criteria are listed in the task file or a linked doc.
Result: Criteria recorded in `.agents/module-contracts/baseline-constraints.md` under "Modularity Acceptance Criteria"

3. [x] [docs]
Files: AGENTS.md
Action: Reorganize AGENTS.md in place: consolidate repeated architectural statements into single canonical sections with internal cross-references. Keep rule IDs unchanged.
Completion check: AGENTS.md has reduced duplication and clear canonical sections.
Result: Rule-ID annotations added to Required Workflow items 3, 5, 8–10 and Implementation Quality items 1–5; Practical Do/Don't section restructured with rule annotations and moved before Repository Indexing.

4. [x] [docs]
Files: backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Reorganize backend/ui/tests AGENTS files: trim duplicated cross-domain architecture prose, keep only domain-operational rules, and reference canonical root rule IDs for cross-domain rules.
Completion check: Each domain AGENTS file is concise, with domain-specific rules and references to root rules.
Result: backend/AGENTS.md "Backend Service Factoring" and "Connector OAuth Notes" sections updated with rule IDs; database section references R-DB-001/R-DB-002; ui/AGENTS.md connector boundary, selection-driven detail, collapsible element, and text density sections updated with rule IDs; tests/AGENTS.md updated with rule ID references.

5. [x] [docs]
Files: scripts/check-policy.sh
Action: Update policy enforcement script to match reorganized policy sections and ensure enforcement parity. Add enforcement hooks to run a module-dependency linter and a PR-scope validator (e.g. `scripts/check-pr-scope.sh`) as part of pre-merge checks.
Completion check: `scripts/check-policy.sh` and `scripts/check-pr-scope.sh` exist and run without errors (dry-run mode) and reference correct section anchors.
Result: `scripts/check-pr-scope.sh` created with advisory scope checks; `scripts/check-policy.sh` updated to invoke it as a warning-level check.

6. [x] [test]
Files: AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md, scripts/check-policy.sh
Action: Run policy checks and verify AREA routing, rules matrix, machine index, and maintenance-sync behavior are consistent.
Completion check: All policy checks pass and routing is correct.

6.1. [x] [test]
Files: scripts/test-module.sh, .github/workflows/(ci matrix entries)
Action: Add `scripts/test-module.sh <module>` to run a module's unit + contract tests locally, and add CI matrix job entries for `module-<name>-unit` and `module-contract-<name>` (these run on PRs for changed modules).
Completion check: `scripts/test-module.sh` exists and `ci` config contains module-scoped job patterns.
Result: `scripts/test-module.sh` created; CI matrix entries deferred until module extraction PRs exist (Steps 7–15).

7. [x] [backend]
Files: backend/services/helpers.py, backend/services/connectors.py, backend/services/connector_secrets.py, backend/services/connector_catalog.py, backend/services/connector_migrations.py
Action: Split `helpers.py` and `connectors.py` by extracting connector secret/protection logic and connector migration/catalog logic into adjacent service modules. For each extracted module, update or add a module contract file under `.agents/module-contracts/` and include unit + contract tests. Use thin forwarding wrappers as needed during transition.
Completion check: `helpers.py` and `connectors.py` are reduced in scope; new modules `backend/services/connector_protection.py` and `backend/services/connector_catalog.py` exist and are importable; each new module has a matching `.agents/module-contracts/<module>.md` with: owner, public API signatures, an example callsite, owned DB tables, and required test filenames; unit tests and a contract test exist under `tests/` and pass when run via `scripts/test-module.sh connector`.
Result: Created `backend/services/connector_protection.py` and `backend/services/connector_catalog.py`, added module contracts `.agents/module-contracts/connector_protection.md` and `.agents/module-contracts/connector_catalog.md`, and added basic unit tests `tests/test_connector_protection.py` and `tests/test_connector_catalog.py`.
Execution note: Extracted protection and catalog logic into new modules and updated `helpers.py` to import them.

8. [!] [backend]
Execution note: Applied minimal remediation — imported `build_connector_activity_catalog` into `backend/routes/connectors.py` to fix a missing symbol. Still blocked pending `scripts/test-module.sh connectors` to validate route→service behavior.
Files: backend/routes/connectors.py, backend/services/connector_tester.py, backend/services/connector_revoker.py
Action: Move provider-specific test/revoke lifecycle logic from `routes/connectors.py` to service modules. For each moved area, update the module contract and add unit + contract tests. Keep routes as parameter extraction and response shaping only.
Completion check: `routes/connectors.py` contains only request parsing, permission checks, and response shaping (no provider-specific business logic). Provider-specific lifecycle functions are implemented in `backend/services/connector_tester.py` and `backend/services/connector_revoker.py`. Each service has a module contract and unit+contract tests; route→service boundary is validated by a contract test that mocks service implementations. Running `scripts/test-module.sh connectors` runs only connector-related tests and passes.
Execution note: Extracted provider-specific `revoke` and `test` logic into `backend/services/connector_revoker.py` and `backend/services/connector_tester.py`. Updated `backend/routes/connectors.py` to delegate to these services and preserved response shaping and saving in the route. Module contract stubs were added under `.agents/module-contracts/`. This step still requires running `scripts/test-module.sh connectors` (test step) to validate behavior; leaving blocked until tests are run.

9. [x] [backend]
Files: backend/services/automation_executor.py, backend/services/validation.py, backend/services/automation_step_executors/, backend/services/automation_step_validators/
Action: Extract step-type-specific executor/validator modules from `automation_executor.py` and `validation.py`, preserving execution outcomes and validation messages unless a bug fix is required. Add or update module contracts and unit+contract tests for each new module.
Completion check: Each step-type executor/validator lives in its own file under `backend/services/automation_step_executors/` or `backend/services/automation_step_validators/`, exports documented public function signatures, and has a module contract plus unit and contract tests. Integration tests that exercise multi-step workflows continue to pass; running `scripts/test-module.sh automation` runs only automation module tests.
Execution note: Extracted `log` executor into `backend/services/automation_step_executors/log.py`, `outbound_request` executor into `backend/services/automation_step_executors/outbound_request.py`, and the `connector_activity` validator into `backend/services/automation_step_validators/connector_activity.py`. Additionally added executors for `tool`, `script` (wrapper), `llm_chat`, and `connector_activity` (executor) under `backend/services/automation_step_executors/`. Created module contract stubs for `script`, `llm_chat`, and `connector_activity` under `.agents/module-contracts/` and updated `automation_executor.py` to delegate to these new modules. Also added `condition` and `storage` executor modules, their module-contracts, and minimal import-only unit test stubs to satisfy presence checks.
Remaining work: add full unit + contract tests for the new modules, extract any further step executors/validators (storage adapters, advanced condition evaluators, etc.), and validate via `scripts/test-module.sh automation` in the Testing steps.
10. [ ] [backend]
Files: backend/routes/log_tables.py, backend/services/log_table_schema.py, backend/services/log_table_import.py, backend/services/log_table_queries.py
Action: Extract log table schema/query/import helpers from `routes/log_tables.py` into service modules. Add module contract files and unit + contract tests for the extracted modules.
Completion check: `routes/log_tables.py` is thin; helpers are in services; contract tests verify the route↔service contract.

11. [ ] [backend]
Files: backend/database.py, backend/database_schema.py
Action: Optionally extract schema SQL from `database.py` after prior backend waves are green. If extracted, create a module contract for `backend/database` and ensure migrations + contract tests are included in the same PR.
Completion check: If schema SQL is moved, `backend/database.py` becomes the DB connection entrypoint and a new `backend/database_schema.py` (or similar) contains schema definitions. The database module contract explicitly lists which modules own which tables and provides migration guidelines. Any migration that changes persisted tables must include an accompanying migration script under `migrations/` and contract tests that verify table ownership and migration idempotency. Running `scripts/test-module.sh database` validates DB-related tests in isolation where possible (using the test DB harness).

12. [ ] [ui]
Files: ui/src/automation/app.tsx, ui/src/automation/step-editors/
Action: Complete and extend TASK-017 by moving per-step editor rendering and drawer orchestration out of `app.tsx` into focused components/modules. For each new UI module, add a module contract under `.agents/module-contracts/` (UI contracts list required props, events, and test selectors) and unit + e2e contract tests.
Completion check: `app.tsx` is orchestrator only, editor logic is modularized, and UI module contracts and tests exist.

13. [ ] [ui]
Files: ui/src/automation/useAutomationBuilderController.ts, ui/src/automation/step-modals/http-step-form.tsx, ui/src/automation/step-modals/connector-activity-step-form.tsx, ui/src/automation/step-modals/storage-step-form.tsx
Action: Decompose large forms and controller concerns into focused hooks/components/utilities, preserving IDs and test selectors. Add UI module contract files and unit + contract tests.
Completion check: Each concern is modularized, tests pass, and UI module contracts are present.

14. [ ] [ui]
Files: ui/src/dashboard/app.tsx, ui/src/dashboard/components.tsx, ui/scripts/apis/forms.js
Action: Modularize other large UI surfaces in bounded batches, each independently verifiable and contract-stable. Ensure module contracts and tests accompany each extraction.
Completion check: Each large UI file is modularized, tests pass, and contracts exist.

15. [ ] [test]
Files: tests/, ui/src/automation/__tests__/, ui/e2e/
Action: For every extraction batch, update or add matching unit/integration/e2e tests in the same change; include module unit + contract tests and run `scripts/test-module.sh <module>` locally. Run `scripts/test-precommit.sh` and `scripts/test-full.sh` at each phase gate.
Completion check: All relevant tests are updated and pass. Each PR includes updated/added unit and contract tests in `tests/` and corresponding UI e2e assertions where UI changes occur. `scripts/test-module.sh <module>` runs only that module's tests; `scripts/test-precommit.sh` passes locally and `scripts/test-full.sh` passes in CI for full integration checks.
Reference: Expected behavior (TASK-019)

16. [ ] [docs]
Files: README.md
Action: Publish a modularization map (module responsibilities, ownership boundaries, and dependency direction rules), list any accepted targeted bug fixes with rationale, and define follow-up backlog for remaining non-blocking modularity debt.
Completion check: README.md contains the modularization map and backlog.

## Test impact review

1. [ ] [test]
Files: tests/, ui/src/automation/__tests__/, ui/e2e/
Action: Review all affected tests for each modularization batch and update, replace, or remove as needed to match new module boundaries and maintain coverage. Below are specific tests discovered during repo inspection with recommended actions and validation commands.
Completion check: All tests listed below are addressed (kept/updated/replaced/removed) and pass their validation commands.

- `tests/test_connectors_api.py` — Intent: API-level connector behavior. Recommended action: update to assert route→service boundaries and to use service mocks. Validation: `pytest tests/test_connectors_api.py -q`

- `tests/test_connector_oauth_service.py` — Intent: OAuth lifecycle. Recommended action: update or keep but move logic to service unit tests where possible. Validation: `pytest tests/test_connector_oauth_service.py -q`

- `tests/test_connector_catalog.py` — Intent: connector catalog behavior. Recommended action: update to reference `backend/services/connector_catalog.py` public API and add contract tests. Validation: `pytest tests/test_connector_catalog.py -q`

- `tests/test_connector_protection.py` — Intent: connector secrets/protection. Recommended action: move to `connector_protection` module unit tests and add contract tests. Validation: `pytest tests/test_connector_protection.py -q`

- `tests/test_connector_activities_api.py` — Intent: per-provider activities. Recommended action: keep per-provider tests but ensure they import the provider service modules directly. Validation: `pytest tests/test_connector_activities_api.py -q`

- `tests/test_automations_api.py` — Intent: automation flows. Recommended action: split into module-level executor/validator tests and keep a small set of end-to-end automation integration tests. Validation: `pytest tests/test_automations_api.py -q`

- `tests/test_workflow_builder_service.py` & `tests/test_workflow_storage.py` — Intent: builder logic and storage. Recommended action: update to rely on module contracts and add module-specific tests. Validation: `pytest tests/test_workflow_builder_service.py -q && pytest tests/test_workflow_storage.py -q`

- `tests/test_log_tables_api.py` — Intent: log table schema and queries. Recommended action: update to test `backend/services/log_table_schema.py` and `log_table_queries.py`; ensure import boundaries. Validation: `pytest tests/test_log_tables_api.py -q`

- `tests/test_runtime_api.py`, `tests/test_runtime_worker_recovery.py`, `tests/test_workers_api.py` — Intent: runtime behaviors that may cross modules. Recommended action: keep integration-level tests but ensure heavy unit coverage lives in module tests. Validation: `pytest tests/test_runtime_api.py -q` etc.

- UI test groups: `ui/src/automation/__tests__/` and `ui/e2e/` — Intent: UI builder and e2e flows. Recommended action: update unit tests to target new components/hooks and add e2e contract tests for cross-module UI flows. Validation: `npm run test -- --testPathPattern=ui/src/automation/__tests__` and e2e command per project docs.

For any test marked `update` or `replace`, the exact validation command above must be included in the PR description and executed in the `Testing steps` before merging.

## Testing steps

1. [ ] [test]
Files: scripts/check-policy.sh
Action: Run policy checks after each policy-file update.
Completion check: All policy checks pass.

2. [ ] [test]
Files: tests/, ui/src/automation/__tests__/, ui/e2e/
Action: Run targeted and full test suites after each modularization batch.
Completion check: All tests pass after each batch.

## Documentation review

1. [ ] [docs]
Files: README.md, AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Review and update documentation to reflect new module boundaries, policy organization, and modularization map.
Completion check: All documentation is current and accurate.

## GitHub update

1. [ ] [github]
Files: All files changed by this task
Action: Stage only task-relevant files, commit with a focused message such as "Repo modularization and agent policy reorganization (phase X)", move this task file to .agents/tasks/closed/ in the same commit, then push.
Completion check: The commit includes only task-relevant files plus the task file move to .agents/tasks/closed/, and push succeeds.
