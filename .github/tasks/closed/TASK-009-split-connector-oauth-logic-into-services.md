## Execution steps

1. [x] [backend]
Files: backend/services/connector_google_oauth_client.py
Action: Create a Google-specific OAuth client module and move `_exchange_google_oauth_code_for_tokens`, `_refresh_google_access_token`, and `_revoke_google_token` out of `backend/routes/connectors.py` into this module, keeping current request/response handling and error semantics unchanged.
Completion check: `backend/services/connector_google_oauth_client.py` defines all three Google OAuth token/revoke functions and `backend/routes/connectors.py` no longer defines them.

2. [x] [backend]
Files: backend/services/connector_oauth.py
Action: Create an OAuth service module that owns connector OAuth orchestration by moving route business logic from `start_connector_oauth`, `_complete_connector_oauth_result`, and `refresh_connector` into service functions that accept explicit dependencies (`connection`, `request app state`, `root_dir`, `protection_secret`, and payload args) and return route-ready response payloads.
Completion check: `backend/services/connector_oauth.py` contains service-level equivalents for start, callback completion, and refresh orchestration, and they call the Google OAuth client module for Google token exchange/refresh.

3. [x] [backend]
Files: backend/routes/connectors.py, backend/services/support.py
Action: Refactor connector OAuth routes into thin wrappers that perform only HTTP parameter extraction plus dependency wiring, then delegate to `backend/services/connector_oauth.py`; keep route paths, response models, and redirect behavior identical.
Completion check: `backend/routes/connectors.py` route handlers for `/api/v1/connectors/{provider}/oauth/start`, `/api/v1/connectors/{provider}/oauth/callback`, and `/api/v1/connectors/{connector_id}/refresh` primarily delegate to service functions and do not contain full OAuth business workflows inline.

4. [x] [backend]
Files: backend/routes/connectors.py, backend/services/connector_oauth.py, backend/services/connector_google_oauth_client.py
Action: Remove or relocate now-stale helper code in `backend/routes/connectors.py` that only supported moved OAuth flows, and update imports so OAuth logic has a single service source of truth without duplicating token handling across route and service layers.
Completion check: there is no duplicate implementation of moved OAuth logic between route and service modules, and imports resolve without wildcard-only coupling for the moved functions.

5. [x] [test]
Files: tests/test_connectors_api.py
Action: Update connector API tests to patch/assert against the new service/client boundaries where needed (instead of route-local Google OAuth helper symbols) while preserving existing API contract assertions for OAuth start/callback/refresh behavior.
Completion check: `tests/test_connectors_api.py` no longer depends on moved route-local Google OAuth helper symbols and still validates start/callback/refresh route contracts.

6. [x] [test]
Files: tests/test_connector_oauth_service.py
Action: Add a focused backend service test module for `backend/services/connector_oauth.py` covering start/callback/refresh orchestration paths and error handling at the service boundary (including Google token exchange and refresh failure propagation).
Completion check: `tests/test_connector_oauth_service.py` exists with service-level tests that execute OAuth orchestration logic without going through HTTP route dispatch.

## Test impact review

1. [x] [test]
Files: tests/test_connectors_api.py
Action: Intent: keep API route contracts stable while route internals are reduced to thin wrappers and OAuth logic moves to service modules. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py`
Completion check: The task records route-contract test updates for wrapper delegation refactor.

2. [x] [test]
Files: tests/test_connector_oauth_service.py
Action: Intent: add direct coverage for OAuth business logic now owned by service modules so behavior is verified independently of route glue. Recommended action: replace. Validation command: `./.venv/bin/python -m pytest -q tests/test_connector_oauth_service.py`
Completion check: The task records service-level coverage for start/callback/refresh orchestration.

3. [x] [test]
Files: tests/test_api_smoke_matrix.py, tests/api_smoke_registry/settings_connectors_cases.py
Action: Intent: ensure smoke coverage stays aligned for unchanged connector OAuth/refresh routes after internal refactor. Recommended action: keep.
Completion check: The task records smoke-matrix files as expected to remain unchanged unless route signatures change.

## Testing steps

1. [x] [test]
Files: tests/test_connector_oauth_service.py, tests/test_connectors_api.py
Action: Run targeted backend suites after test updates. Command: `./.venv/bin/python -m pytest -q tests/test_connector_oauth_service.py tests/test_connectors_api.py`
Completion check: The command exits 0.

2. [x] [test]
Files: tests/test_api_smoke_matrix.py
Action: Run connector route smoke regression checks. Command: `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k connectors`
Completion check: The command exits 0.

3. [ ] [test]
Files: scripts/check-policy.sh
Action: Run policy enforcement checks after AGENTS updates. Command: `./scripts/check-policy.sh`
Completion check: The command exits 0.

4. [x] [test]
Files: scripts/test-precommit.sh
Action: Run the precommit gate after targeted suites pass. Command: `./scripts/test-precommit.sh`
Completion check: The command exits 0.

Current verification note: targeted connector pytest suites passed, connector smoke coverage passed, and `scripts/test-precommit.sh` passed via `scripts/check-policy.sh`. `scripts/test-full.sh` is currently failing on the existing browser case `ui/e2e/automations-builder.spec.ts:68` in Chromium, Firefox, and WebKit, where the automation editor modal is not visible after double-clicking the canvas node.

## Documentation review

1. [x] [docs]
Files: AGENTS.md, scripts/check-policy.sh
Action: Add and enforce a connector architecture rule that future connector implementations keep provider-specific business logic in dedicated `backend/services/` modules (including OAuth token lifecycle handlers) while `backend/routes/connectors.py` remains thin route glue.
Completion check: `AGENTS.md` documents the service-module connector logic boundary for future connectors, and `scripts/check-policy.sh` is updated in the same change to enforce the new/updated rule text.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-009-split-connector-oauth-logic-into-services.md, backend/routes/connectors.py, backend/services/connector_oauth.py, backend/services/connector_google_oauth_client.py, backend/services/support.py, tests/test_connectors_api.py, tests/test_connector_oauth_service.py, AGENTS.md, scripts/check-policy.sh
Action: Stage only task-relevant files, commit with a focused message such as `Refactor connector OAuth logic into service modules`, move this task file to `.github/tasks/closed/` in the same commit, then push.
Completion check: The commit contains only relevant implementation/test/doc files plus the task file move to `.github/tasks/closed/`, and push succeeds.
