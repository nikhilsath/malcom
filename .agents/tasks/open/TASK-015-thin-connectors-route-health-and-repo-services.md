## Execution steps

1. [ ] [backend]
Files: backend/services/connector_health.py
Action: Create a connector health service module and move provider-specific connection-check helpers out of backend/routes/connectors.py, including `_google_probe_failure_message`, `_probe_google_access_token`, `_probe_github_access_token`, `_probe_notion_access_token`, `_probe_trello_credentials`, and `_inspect_github_scopes_from_payload`, while preserving existing return shapes and error semantics.
Completion check: backend/services/connector_health.py defines all moved helpers and backend/routes/connectors.py no longer defines these functions.

2. [ ] [backend]
Files: backend/services/connector_repositories.py
Action: Create a repository listing service module and move `_list_github_repositories` out of backend/routes/connectors.py into a service function that preserves current deterministic test fixture behavior for `token_`/`ghp_secret_` tokens.
Completion check: backend/services/connector_repositories.py owns GitHub repository listing logic and backend/routes/connectors.py no longer defines `_list_github_repositories`.

3. [ ] [backend]
Files: backend/services/connector_health.py, backend/services/connector_repositories.py, backend/routes/connectors.py
Action: Add route-facing service entrypoints for connector test/revoke/repository-list flows (for example `test_connector_record`, `revoke_connector_record`, and `list_connector_repositories`) and refactor connector routes to delegate business logic to service functions while keeping route paths, response models, and status codes unchanged.
Completion check: backend/routes/connectors.py connector test/revoke/repository routes primarily perform HTTP wiring and delegate business workflows to service functions.

4. [ ] [backend]
Files: backend/routes/connectors.py
Action: Remove stale direct imports and network helpers from the route module after delegation, keeping only route-level dependencies and provider-agnostic HTTP response shaping.
Completion check: backend/routes/connectors.py has no direct provider token probe implementations and no direct GitHub repository listing implementation.

5. [ ] [test]
Files: tests/test_connectors_api.py, tests/test_connector_health_service.py
Action: Update route tests to patch new service-module helper locations and add/expand service-level tests for connector probe/revoke/repository behaviors so moved logic remains covered outside HTTP dispatch.
Completion check: tests/test_connectors_api.py no longer imports `_probe_google_access_token` from backend.routes.connectors, and tests/test_connector_health_service.py exists with service-level coverage.

## Test impact review

1. [ ] [test]
Files: tests/test_connectors_api.py
Action: Intent: keep connector API contract assertions stable while moving business logic out of routes. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_connectors_api.py
Completion check: The task records that route-level tests are updated to assert unchanged contracts with new patch targets.

2. [ ] [test]
Files: tests/test_connector_health_service.py
Action: Intent: keep provider probe/revoke/repository logic covered at the new service boundary. Recommended action: replace. Validation command: ./.venv/bin/python -m pytest -q tests/test_connector_health_service.py
Completion check: The task records dedicated service-level coverage for moved connector health/repository logic.

3. [ ] [test]
Files: tests/test_api_smoke_matrix.py, tests/api_smoke_registry/settings_connectors_cases.py
Action: Intent: preserve smoke coverage for connector routes because route surfaces remain unchanged. Recommended action: keep.
Completion check: The task records smoke files as unchanged unless route signatures change.

## Testing steps

1. [ ] [test]
Files: tests/test_connector_health_service.py, tests/test_connectors_api.py
Action: Run focused connector suites after test updates. Command: ./.venv/bin/python -m pytest -q tests/test_connector_health_service.py tests/test_connectors_api.py
Completion check: The command exits 0.

2. [ ] [test]
Files: tests/test_api_smoke_matrix.py
Action: Run connector smoke regression checks. Command: ./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k connectors
Completion check: The command exits 0.

3. [ ] [test]
Files: scripts/test-precommit.sh
Action: Run the precommit gate after connector-targeted suites pass. Command: ./scripts/test-precommit.sh
Completion check: The command exits 0.

## Documentation review

1. [ ] [docs]
Files: README.md
Action: Review connector architecture wording and update only if route/service ownership descriptions or connector health/repository flow descriptions are now inaccurate after the refactor.
Completion check: README.md either contains any required connector boundary wording updates or the task records that no documentation changes were needed.

## GitHub update

1. [ ] [github]
Files: .agents/tasks/open/TASK-015-thin-connectors-route-health-and-repo-services.md, backend/routes/connectors.py, backend/services/connector_health.py, backend/services/connector_repositories.py, tests/test_connectors_api.py, tests/test_connector_health_service.py, README.md
Action: Stage only task-relevant files, commit with a focused message such as `Thin connector routes by moving health and repository logic into services`, move this task file to .agents/tasks/closed/ in the same commit, then push.
Completion check: The commit includes only task-relevant files plus the task file move to .agents/tasks/closed/, and push succeeds.
