## Execution steps

1. [x] [connector]
Files: app/backend/services/connector_trello_oauth_client.py, app/backend/services/connector_oauth_provider_clients.py
Action: Replace the demo-only Trello callback exchange contract with a real provider token exchange implementation and add a Trello refresh-token flow helper, while keeping provider-specific lifecycle logic in service modules per AGENTS.md#connector-route-service-boundary (R-CONN-005).
Completion check: `exchange_trello_oauth_code_for_tokens` no longer hard-fails non-demo codes with the current demo-only message, and a Trello refresh helper exists in provider OAuth clients.

2. [x] [connector]
Files: app/backend/services/connector_oauth.py, app/backend/services/connectors.py
Action: Update Trello OAuth orchestration metadata and refresh path to support refresh tokens when available (state transitions, `has_refresh_token`, expiry updates, refresh endpoint behavior), while preserving canonical connector resolver flow.
Completion check: Trello provider metadata indicates refresh support where applicable, and `refresh_oauth_token` no longer unconditionally returns `409` for connected Trello OAuth connectors.

3. [x] [test]
Files: app/tests/test_connectors_api.py, app/tests/test_connector_oauth_service.py
Action: Update Trello OAuth tests from demo/refresh-rejected expectations to real callback + refresh-capable behavior, including revoke/test follow-through after refresh.
Completion check: Trello test cases assert successful refresh behavior (when refresh token is present) instead of asserting the previous `does not support token refresh` contract.

4. [x] [docs]
Files: README.md, app/backend/AGENTS.md
Action: Update docs to remove the Trello demo-contract/refresh-token limitation notes after implementation (keep documentation aligned with actual provider behavior).
Completion check: README unfinished-features bullet and backend OAuth notes no longer describe Trello as demo-only without refresh support.
Blocker: none.

## Test impact review

1. [x] [test]
Files: app/tests/test_connectors_api.py
Action: Intent: verify Trello OAuth start/callback/test/refresh/revoke API lifecycle contract; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_connectors_api.py -k trello`.
Completion check: Trello API tests validate successful refresh path for refresh-capable records.

2. [x] [test]
Files: app/tests/test_connector_oauth_service.py
Action: Intent: verify service-level Trello callback and refresh behavior without route wrappers; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_connector_oauth_service.py -k trello`.
Completion check: Service tests assert Trello refresh behavior and token-state updates.

3. [x] [test]
Files: app/tests/test_connector_revoker_and_tester.py
Action: Intent: preserve revoke/test behavior expectations while refresh flow changes; Recommended action: keep.
Completion check: Existing revoke/test assertions remain valid or are intentionally updated only if contract changed.

## Testing

1. [x] [test]
Files: app/tests/test_connectors_api.py, app/tests/test_connector_oauth_service.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_connectors_api.py app/tests/test_connector_oauth_service.py -k trello`.
Completion check: Command exits with status 0.

2. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as required first-pass real-system validation.
Completion check: Command exits with status 0.
Blocker: none.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-035-complete-trello-oauth-refresh-contract.md, app/backend/services/connector_trello_oauth_client.py, app/backend/services/connector_oauth_provider_clients.py, app/backend/services/connector_oauth.py, app/backend/services/connectors.py, app/tests/test_connectors_api.py, app/tests/test_connector_oauth_service.py, README.md, app/backend/AGENTS.md
Action: Stage only relevant files and run `git add <files> && git commit -m "Complete Trello OAuth callback and refresh contract" && git push` following AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit and `git status --short` is clean for the listed files.
