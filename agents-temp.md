# Dashboard Improvement Handoff Scratchpad

## Current Dashboard Gap Summary

- Stage 2 gap: the dashboard logs route and UI wiring exist in repo code, but the work is not cleanly landed yet. The route/UI/tests/docs need validation and cleanup so backend log files are the primary source, malformed lines stay non-fatal, and fallback behavior remains failure-only.
- Stage 3 gap: persisted runtime telemetry schema, persistence, route, UI, and tests exist in repo code, but they still need end-to-end verification and cleanup before this work is considered complete.
- Repo state to preserve while finishing this task:
  - relevant files already contain in-progress changes from this dashboard work
  - `backend/database.py`, `README.md`, and `ui/e2e/support/dashboard-settings.ts` are currently in an unresolved git state and must be finalized without dropping intended dashboard changes

## Exact Files To Change

### Stage 2

- `backend/routes/runtime.py`
- `backend/services/helpers.py`
- `backend/services/logging_service.py` if log path/helper changes are needed
- `ui/src/dashboard/data.ts`
- `ui/src/dashboard/app.tsx`
- `ui/src/dashboard/types.ts`
- `tests/test_runtime_api.py`
- `tests/api_smoke_registry/runtime_workers_cases.py`
- `ui/src/dashboard/__tests__/dashboard-app.test.tsx`
- `ui/e2e/support/dashboard-settings.ts`
- `ui/e2e/dashboard.spec.ts`
- `README.md`

### Stage 3

- `backend/database.py`
- `backend/routes/runtime.py`
- `backend/services/helpers.py`
- `backend/services/metrics.py` if telemetry collector changes are needed
- `ui/src/dashboard/data.ts`
- `ui/src/dashboard/types.ts`
- `ui/src/dashboard/app.tsx`
- `tests/test_runtime_api.py`
- `tests/api_smoke_registry/runtime_workers_cases.py`
- `ui/src/dashboard/__tests__/dashboard-app.test.tsx`
- `ui/e2e/support/dashboard-settings.ts`
- `ui/e2e/dashboard.spec.ts`
- `README.md`

## Stage Checklists

### Stage 2 Checklist

- [x] Confirm `/api/v1/dashboard/logs` uses existing backend logging path helpers
- [x] Confirm log parsing safely handles malformed and non-JSON lines
- [x] Normalize backend log rows to dashboard log entry shape
- [x] Keep fallback/sample logs only for backend failure cases in UI data layer
- [x] Update API/backend/frontend tests for backend-backed logs
- [x] Update README only if needed
- [x] Keep smoke coverage aligned for `/api/v1/dashboard/logs`
- [x] Record completed items, changed files, tests, and remaining issues here after Stage 2

Stage 2 completed items:

- Backend dashboard logs route is present and returns normalized entries from runtime log files.
- Malformed lines are handled safely and do not crash the route.
- Dashboard logs UI uses `/api/v1/dashboard/logs` as the primary source and keeps fallback entries for failure cases only.
- Shared Playwright fixture was cleaned up so dashboard browser coverage can run against the backend-backed logs flow.

Stage 2 changed files in this turn:

- `ui/e2e/support/dashboard-settings.ts`

Stage 2 tests added/updated in effect:

- Existing backend route coverage in `tests/test_runtime_api.py`
- Existing smoke coverage in `tests/api_smoke_registry/runtime_workers_cases.py`
- Existing dashboard unit coverage in `ui/src/dashboard/__tests__/dashboard-app.test.tsx`
- Existing dashboard browser coverage in `ui/e2e/dashboard.spec.ts`

Stage 2 remaining issues:

- No dashboard-log-specific functional blockers remain.

### Stage 3 Checklist

- [x] Confirm additive schema for persisted runtime telemetry snapshots
- [x] Preserve existing in-memory live resource profile behavior
- [x] Persist snapshots periodically instead of every metric execution
- [x] Confirm `/api/v1/dashboard/resource-history` returns persisted history
- [x] Keep dashboard history UI minimal and integrated into existing layout
- [x] Update backend/frontend tests for persisted history
- [x] Update README only if needed
- [x] Keep smoke coverage aligned for `/api/v1/dashboard/resource-history`
- [x] Record completed items, changed files, tests, and remaining issues here after Stage 3

Stage 3 completed items:

- Persisted runtime telemetry snapshots and `/api/v1/dashboard/resource-history` are present and verified.
- The live in-memory resource profile remains intact alongside persisted history.
- Dashboard home renders a minimal history view without redesigning unrelated sections.

Stage 3 changed files in this turn:

- No additional Stage 3 source edits were required beyond verification and fixture cleanup already captured above.

Stage 3 tests added/updated in effect:

- Existing persisted history backend coverage in `tests/test_runtime_api.py`
- Existing smoke coverage in `tests/api_smoke_registry/runtime_workers_cases.py`
- Existing dashboard unit coverage in `ui/src/dashboard/__tests__/dashboard-app.test.tsx`
- Existing dashboard browser coverage in `ui/e2e/dashboard.spec.ts`

Stage 3 remaining issues:

- `./scripts/test-full.sh` still fails outside dashboard scope because unrelated `ui/e2e/automations-builder.spec.ts` connector-dropdown expectations do not match the current app state across Chromium, Firefox, and WebKit.

## Tests Required

### Stage 2

- `tests/test_runtime_api.py`
  - dashboard logs normalization
  - malformed line handling
  - missing log file behavior
- `tests/test_api_smoke_matrix.py`
  - indirect verification via smoke registry alignment
- `ui/src/dashboard/__tests__/dashboard-app.test.tsx`
  - dashboard logs fetch and filtering behavior against backend payload shape
- `ui/e2e/dashboard.spec.ts`
  - dashboard logs route/filter/detail workflow using backend route fixture

### Stage 3

- `tests/test_runtime_api.py`
  - persisted resource history endpoint and snapshot shape
- `tests/test_api_smoke_matrix.py`
  - indirect verification via smoke registry alignment
- `ui/src/dashboard/__tests__/dashboard-app.test.tsx`
  - home dashboard resource history summary rendering
- `ui/e2e/dashboard.spec.ts`
  - home dashboard resource profile/history workflow

## Final Cleanup Checklist

- [ ] Move any lasting findings into code/docs/tests
- [ ] Remove merge-state leftovers from relevant files
- [ ] Run smallest relevant verification first
- [ ] Run broader verification required by changed backend routes and dashboard UI
- [ ] Remove `agents-temp.md`
- [ ] `git add .`
- [ ] `git commit -m "add backend dashboard logs and persisted resource telemetry"`
- [ ] `git push`
