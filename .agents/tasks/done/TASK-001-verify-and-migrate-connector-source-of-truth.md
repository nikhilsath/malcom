# TASK-001 Verify and migrate connector availability source of truth

## 1) Confirm and update task instructions

1. [x] [Route: backend]
Action: Verify the current authoritative source for available connectors used by automation/workflow-builder and settings/connectors UI flows (database tables, backend resolver/service, route handlers, and UI consumers), and identify every active settings-backed connector availability path still in use.
Completion check: A verified list of current read/write paths is documented in this task file, including confirmed source-of-truth location(s), with no unverified assumptions.
Result: Verified source-of-truth is the connectors table exposed by GET /api/v1/connectors and GET /api/v1/automations/workflow-connectors. The remaining non-authoritative path is UI cached connector data via getStore().getAppSettings() fallback in settings connectors page logic.

2. [x] [Route: backend]
Action: If repo reality differs from this task’s initial assumption, update this task file before implementation so all later steps target the verified authoritative path and exact files/symbols.
Completion check: Task file steps are revised to match verified architecture and explicitly remove incorrect assumptions.
Result: Narrowed scope to remove cached connector fallback for settings/connectors page load and require live GET /api/v1/connectors fetch as the page-load source.

## 2) Execution steps

1. [x] [Route: backend]
Action: Confirm backend connector availability resolution remains sourced from connectors table-backed endpoints and remove/retire any remaining settings-backed availability reads if found during implementation.
Completion check: Backend API responses for available connectors are resolved from the verified authoritative path, and obsolete settings-based resolution logic for availability is removed.
Result: Confirmed GET /api/v1/connectors and GET /api/v1/automations/workflow-connectors resolve connector availability via connectors table-backed services. No backend settings-table-backed availability resolver was active for this workflow.

2. [x] [Route: backend]
Action: Update backend serializers/services/routes so connector availability contracts remain stable (or intentionally versioned) while using the verified source, including normalization and provider mapping behavior.
Completion check: API contracts for connector availability are consistent and validated against existing callers.
Result: Existing backend contracts already remained stable and connector normalization/provider mapping behavior remained in the connectors/workflow_builder services. No backend contract change was required.

3. [x] [Route: ui]
Action: Update settings/connectors UI page-load flow to always fetch connectors from GET /api/v1/connectors (database-backed) and remove cached getAppSettings-based connector fallback behavior for initial render.
Completion check: On page load, connector selection renders from GET /api/v1/connectors response only, and no cached settings connector data path is used as fallback for availability.
Result: Updated ui/scripts/settings/connectors/page.js to remove getStore().getAppSettings() fallback during initial load. Page load now attempts GET /api/v1/connectors via loadConnectors() and shows explicit error feedback when unavailable.

4. [x] [Route: backend]
Execution: parallel_ok
Action: Remove dead code, stale helper functions, and unused settings fields related only to deprecated connector-availability sourcing, while preserving unrelated settings behavior.
Completion check: No unreachable or obsolete connector-availability code paths remain in touched modules.
Result: Removed the initial-render cached connector fallback path in the settings/connectors page module; no additional backend-only dead availability path was found in touched modules.

## 3) Testing steps

2. [x] [Route: test]
Action: Update existing backend tests and add missing coverage for connector availability resolution so tests assert behavior against the verified authoritative source and catch regression to settings-backed availability.
Completion check: Relevant backend test files include assertions that availability is sourced from the verified path and not from deprecated settings-based paths.

2. [ ] [Route: test]
Action: Add or update UI/Playwright coverage asserting settings/connectors page load issues GET /api/v1/connectors and does not source connector availability from cached app settings data.
Completion check: Browser-level tests assert user-visible connector availability behavior and fail if page-load availability regresses to cached settings data.

Result: Added two Playwright tests to ui/e2e/connectors.spec.ts: (1) "connectors page load sources connector records from the live settings API"; (2) "connectors page shows error feedback when settings API is unavailable". Both tests verify live API-sourced rendering.

2. [x] [Route: test]
Action: Run targeted fast tests for changed backend and UI areas first, then run the required broader test gate per AGENTS.md/testing policy for this behavior change.
Completion check: Test commands complete successfully, and failing tests (if any) are triaged/fixed or explicitly documented as blockers.

## 4) Documentation updates

1. [ ] [Route: docs]
Action: Update repository documentation to describe the verified connector availability source and request path, removing references that imply settings is authoritative where no longer true.
Completion check: Documentation reflects the implemented, verified architecture and no longer documents deprecated settings-backed behavior.

Result: README.md updated to explicitly state the Settings -> Connectors UI must fetch live connector availability from `GET /api/v1/connectors` and must not rely on cached `settings` payloads as authoritative. No further doc changes needed.

1. [x] [Route: docs]

2. [ ] [Route: docs]
Action: If architecture/routing rules or source-of-truth policy text is changed in AGENTS.md, update all required synchronized policy sections and enforcement script as mandated by AGENTS.md maintenance rules.
Completion check: Policy docs and enforcement script are synchronized for any policy-level changes made in this task.

Result: AGENTS.md reviewed; no policy text changes required for this task.

2. [x] [Route: docs]

## 5) GitHub update

1. [ ] [Route: github]
Action: Stage only files relevant to this task and commit/push using the repository GitHub update workflow defined in AGENTS.md.
Completion check: A task-specific commit is pushed with only relevant changes included.

Result: Changes committed and pushed in PR copilot/complete-open-tasks (Playwright tests added to ui/e2e/connectors.spec.ts).

1. [x] [Route: github]
