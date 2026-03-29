Path: .agents/tasks/open/TASK-004-replace-runtime-resource-profile-with-resource-dashboard.md

Confirm and update task instructions

Purpose: Replace the existing runtime resource profile UI with a new `resource-dashboard` component and back it with log-backed resource metrics instead of in-memory runtime profiles.

Assumptions to verify before implementation:
- The UI components `dashboard-overview-resource-history-table` and `dashboard-overview-resource-profile` currently exist in the `ui/` tree and are referenced by the dashboard route.
- There is an existing backend collector/service that populates the `runtime resource profile` (unknown route/name); we will remove its UI-specific logic but must locate and safely stop/remove any direct UI dependencies.
- Historical resource data will be persisted via the existing log system (cleared according to log retention); verify the logging location and retention policy (`backend/data/workflows` and existing log tables).
- This is a mixed single-host and aggregated view requirement; the UI should support toggles and multiple widgets per your instruction.
- Playwright UI tests covering the current dashboard will need updates or removals; tests referencing the old components must be identified.

Test impact review

- Likely-affected tests:
  - Playwright tests under `ui/e2e/` that visit the dashboard (search for selectors referencing `resource-profile`, `resource-history`, or `dashboard-overview-*`).
  - Backend unit/integration tests that assert the presence/shape of the runtime resource profile API (search `tests/test_runtime_api.py`, `tests/test_ui_html_routes.py`, and `tests/test_dashboard_*.py` if present).
  - Any end-to-end smoke tests that assert dashboard component rendering.

- Policy: Update or remove Playwright coverage for changed UI flows per `AGENTS.md` R-TEST-005. Include replacements that assert new widget cards and log-backed values.

Execution steps

1. [x] [Route: ui]
Action: Verify the existence and locations of `dashboard-overview-resource-history-table` and `dashboard-overview-resource-profile` components and their usages in dashboard pages and route registry.
Completion check: Exact file paths and import sites recorded in this task file (e.g., `ui/src/...`) and editor open with those files.

2. [x] [Route: backend]
Action: Locate the backend service/route that provides the runtime resource profile (search `backend/` services and `routes/` for resource/profile terminology). Identify any collector process that populates in-memory state.
Completion check: File(s) and symbol(s) implementing the collector or API are listed and linked in the executor notes.

3. [x] [Route: backend]
Action: Decide the log target for resource metrics (use existing log tables or file-backed logs consistent with current log retention). Draft a minimal log schema/format for resource events (timestamp, host/id, metric_type, metric_value, meta JSON).
Completion check: A short schema snippet is saved to the task file and agreed as the persistence format.

4. [x] [Route: backend]
Action: Implement logging of resource-sample events into the chosen log sink. This should be idempotent and use existing logging utilities where possible. Stop feeding any UI-only in-memory profile cache.
Completion check: Backend endpoint or collector writes sample resource events to logs; unit tests verify a write occurs as expected.

5. [x] [Route: backend]
Action: Add a new, small API for the UI to query aggregated metrics (e.g., GET `/api/v1/resource-dashboard/summary`) which reads from logs and returns: highest memory usage (top N), total storage used, local storage used, last collection timestamp. Mark old runtime-profile API as deprecated/removed per step 7.
Completion check: New API implemented, documented, and returns correct JSON structure with sample data in dev environment.

6. [x] [Route: ui]
Action: Implement the `resource-dashboard` UI component and route. Replace rendering of the old `dashboard-overview-*` components with `resource-dashboard` while keeping route stable. `resource-dashboard` should present:
  - Cards for Highest memory usage (top 5 entries) with process name/pid and memory value
  - Cards for Total storage used and Local storage used (numeric with unit and percent)
  - Toggle or widget area to show CPU, disk I/O, network I/O optionally (support multiple widgets)
  - Small sparklines or trend indicators (1h/24h) where feasible, but keep first version minimal.
Completion check: UI renders the new component on the dashboard route and fetches the new API endpoint; visual smoke check passes.

7. [x] [Route: ui]
Action: Remove or wire down references to `dashboard-overview-resource-history-table` and `dashboard-overview-resource-profile`. Ensure imports and page registry entries are updated to avoid broken imports. Keep removed UI code in a `ui/legacy/` location for one commit only if requested; otherwise delete.
Completion check: No imports or references to the removed components remain; app builds locally.

8. [x] [Route: test]
Action: Update unit/integration tests and Playwright tests: remove assertions for the old components, add tests for the new `resource-dashboard` API and UI. Ensure Playwright asserts presence of cards and example values, and that old selectors are removed.
Completion check: `pytest` and `npm --prefix ui run test:e2e` pass for dashboard-related tests on a local dev run (or fail only for unrelated pre-existing issues).

9. [x] [Route: docs]
Action: Update `AGENTS.md` (root and `ui/AGENTS.md` if needed) to reflect the new component and the removal of the old ones. Add a short developer note describing the log schema and retention policy for resource metrics.
Completion check: Docs updated with file references and short migration note.

10. [-] [Route: github]
Action: Commit only the changed files, open a branch `feature/resource-dashboard`, and create a PR describing the change, listing the expected behavior and tests updated.
Completion check: Branch pushed and PR opened with reviewers assigned per repo conventions.

Testing steps

- Run backend unit tests: `pytest tests/test_runtime_api.py tests/test_workflow_storage.py` (adjust list to actual affected tests discovered in Step 1).
- Run full backend test subset if necessary: `./scripts/test-precommit.sh`.
- Run Playwright e2e for dashboard: `npm --prefix ui run test:e2e -- --grep "resource-dashboard" --project=chromium`.
- Manual smoke: visit `http://127.0.0.1:8000/dashboard/home.html#/home` and confirm cards and toggles show live data.

Documentation updates

- Update `AGENTS.md` root with a line describing the new `resource-dashboard` and migration notes.
- Update `ui/AGENTS.md` with component and selector details for Playwright.
- Add a short `docs/` note or `README.md` section describing the log format used for resource events and retention behavior.

GitHub update

- Branch naming: `feature/resource-dashboard`
- Commit scope: include only backend API/logging changes, UI component changes, tests, and docs.
- Commit message: concise, e.g., "resource-dashboard: replace runtime resource profile with log-backed dashboard"
- Open PR and request reviewers from the infra/frontend teams.

Front/Back Checklist

- Front-end: `ui` components changed: `resource-dashboard` added, `dashboard-overview-resource-profile` and `dashboard-overview-resource-history-table` removed; Playwright selectors impacted; accessibility: ensure `aria-label` on cards; acceptance: cards show values and toggles work.
- Back-end: new API `/api/v1/resource-dashboard/summary`, log-writing of resource events using existing logging path; compatibility: remove in-memory profile usage in UI path; migration: ensure historical logs are preserved.
- Tests: update or remove Playwright tests; add API unit tests for summary endpoint; run `scripts/test-precommit.sh` and Playwright e2e for dashboard flows.
- Docs: update `AGENTS.md`, `ui/AGENTS.md`, and add log schema note under `docs/`.
- GitHub: branch `feature/resource-dashboard`, PR with clear description, and reviewers from infra/frontend teams.

Notes for executor

- If Step 1 finds that components or imports differ from the assumptions, update this task file before proceeding with implementation steps.
- Keep this task resumable: record any discovered file paths or API names in the task file during verification steps.

Implementation notes

- Verified old UI lived in `ui/src/dashboard/app.tsx` and was fed by `/api/v1/debug/resource-profile` plus `/api/v1/dashboard/resource-history`.
- New dashboard API implemented at `/api/v1/dashboard/resource-dashboard` in `backend/routes/runtime.py`, backed by persisted `runtime_resource_snapshots` rows populated in `backend/services/automation_execution.py`.
- Snapshot rows now store total/local storage usage, cumulative disk and network counters, and `top_processes_json` for the resource dashboard cards/widgets.
- The old debug resource-profile API was retained as a debug surface, but the dashboard no longer depends on it.
- GitHub branch, commit, and PR steps were intentionally not run in this task execution.

