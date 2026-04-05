# TASK-019: Repository Modularization and Agent Policy Reorganization

## Execution steps

0. [x] [docs]
Files: .agents/module-contracts/template.md
Action: Create a module contract template and storage location under `.agents/module-contracts/` describing: owner, responsibilities, public API (functions/classes), owned DB tables, inbound/outbound dependencies, allowed callers, test obligations, and migration rules.
Completion check: `.agents/module-contracts/template.md` exists and contains the required fields.

1. [ ] [docs]
Files: AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Baseline current architecture, identify all large/mixed-responsibility files, and document public API/UI contracts, DB schema ownership, and connector source-of-truth flows. Lock these as refactor constraints.
Completion check: A summary of baseline constraints and hotspots is recorded in the task file or a linked doc.

2. [ ] [docs]
Files: AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Define modularity acceptance criteria per area. Include: max public API size (functions/classes), allowed inbound/outbound dependency list, required per-module unit and contract test coverage, CI job names (`module-<name>-unit`, `module-contract-<name>`), and PR-scope rules.
Completion check: Acceptance criteria are listed in the task file or a linked doc.

3. [ ] [docs]
Files: AGENTS.md
Action: Reorganize AGENTS.md in place: consolidate repeated architectural statements into single canonical sections with internal cross-references. Keep rule IDs unchanged.
Completion check: AGENTS.md has reduced duplication and clear canonical sections.

4. [ ] [docs]
Files: backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md
Action: Reorganize backend/ui/tests AGENTS files: trim duplicated cross-domain architecture prose, keep only domain-operational rules, and reference canonical root rule IDs for cross-domain rules.
Completion check: Each domain AGENTS file is concise, with domain-specific rules and references to root rules.

5. [ ] [docs]
Files: scripts/check-policy.sh
Action: Update policy enforcement script to match reorganized policy sections and ensure enforcement parity. Add enforcement hooks to run a module-dependency linter and a PR-scope validator (e.g. `scripts/check-pr-scope.sh`) as part of pre-merge checks.
Completion check: `scripts/check-policy.sh` and `scripts/check-pr-scope.sh` exist and run without errors (dry-run mode) and reference correct section anchors.

6. [ ] [test]
Files: AGENTS.md, backend/AGENTS.md, ui/AGENTS.md, tests/AGENTS.md, scripts/check-policy.sh
Action: Run policy checks and verify AREA routing, rules matrix, machine index, and maintenance-sync behavior are consistent.
Completion check: All policy checks pass and routing is correct.

6.1. [ ] [test]
Files: scripts/test-module.sh, .github/workflows/(ci matrix entries)
Action: Add `scripts/test-module.sh <module>` to run a module's unit + contract tests locally, and add CI matrix job entries for `module-<name>-unit` and `module-contract-<name>` (these run on PRs for changed modules).
Completion check: `scripts/test-module.sh` exists and `ci` config contains module-scoped job patterns.

7. [ ] [backend]
Files: backend/services/helpers.py, backend/services/connectors.py, backend/services/connector_secrets.py, backend/services/connector_catalog.py, backend/services/connector_migrations.py
Action: Split `helpers.py` and `connectors.py` by extracting connector secret/protection logic and connector migration/catalog logic into adjacent service modules. For each extracted module, update or add a module contract file under `.agents/module-contracts/` and include unit + contract tests. Use thin forwarding wrappers as needed during transition.
Completion check: helpers.py and connectors.py are reduced in scope, new modules exist with correct logic, and each extracted module has a contract file plus unit and contract tests.

8. [ ] [backend]
Files: backend/routes/connectors.py, backend/services/connector_tester.py, backend/services/connector_revoker.py
Action: Move provider-specific test/revoke lifecycle logic from `routes/connectors.py` to service modules. For each moved area, update the module contract and add unit + contract tests. Keep routes as parameter extraction and response shaping only.
Completion check: `routes/connectors.py` is thin; provider-specific logic is in services; contract tests validate the route→service boundary.

9. [ ] [backend]
Files: backend/services/automation_executor.py, backend/services/validation.py, backend/services/automation_step_executors/, backend/services/automation_step_validators/
Action: Extract step-type-specific executor/validator modules from `automation_executor.py` and `validation.py`, preserving execution outcomes and validation messages unless a bug fix is required. Add or update module contracts and unit+contract tests for each new module.
Completion check: Step execution and validation logic is modularized, tests pass, and each new step module has a contract file.

10. [ ] [backend]
Files: backend/routes/log_tables.py, backend/services/log_table_schema.py, backend/services/log_table_import.py, backend/services/log_table_queries.py
Action: Extract log table schema/query/import helpers from `routes/log_tables.py` into service modules. Add module contract files and unit + contract tests for the extracted modules.
Completion check: `routes/log_tables.py` is thin; helpers are in services; contract tests verify the route↔service contract.

11. [ ] [backend]
Files: backend/database.py, backend/database_schema.py
Action: Optionally extract schema SQL from `database.py` after prior backend waves are green. If extracted, create a module contract for `backend/database` and ensure migrations + contract tests are included in the same PR.
Completion check: `database.py` contains only connection logic and schema SQL placement is documented in a contract; migrations and contract tests are present when schema changes.

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
Completion check: All relevant tests are updated and pass; `scripts/test-module.sh` validates module tests.

16. [ ] [docs]
Files: README.md
Action: Publish a modularization map (module responsibilities, ownership boundaries, and dependency direction rules), list any accepted targeted bug fixes with rationale, and define follow-up backlog for remaining non-blocking modularity debt.
Completion check: README.md contains the modularization map and backlog.

## Test impact review

1. [ ] [test]
Files: tests/, ui/src/automation/__tests__/, ui/e2e/
Action: Review all affected tests for each modularization batch and update, replace, or remove as needed to match new module boundaries and maintain coverage.
Completion check: All tests are aligned with new module structure and pass.

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
