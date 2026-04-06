Execution steps

1. [x] [backend]
Files: backend/services/connectors.py, backend/services/connector_oauth.py, backend/services/connector_oauth_provider_clients.py, backend/services/connector_trello_oauth_client.py (new), tests/test_connectors_api.py
Action: Implement Trello OAuth support.
- Update `DEFAULT_CONNECTOR_PROVIDER_METADATA` entry for `trello` to set `oauth_supported=True`, `callback_supported=True`, set `default_redirect_path` to `/api/v1/connectors/trello/oauth/callback`, and add any `required_fields` (e.g., `client_id`/`client_secret` if required).
- Add a new provider client module `backend/services/connector_trello_oauth_client.py` with functions to exchange an authorization code for tokens and (if Trello supports it) refresh tokens. Provide a "demo" path (e.g., code starting with `demo`) that returns deterministic fake tokens compatible with existing tests.
- Wire the Trello exchange/refresh functions into `backend/services/connector_oauth_provider_clients.py` (or import from the new module) and ensure `connector_oauth._get_provider_oauth_handlers` and `complete_connector_oauth` / `refresh_oauth_token` can route Trello.
- Update `backend/services/connector_oauth.py` where provider-specific branches exist to handle Trello similar to `notion`/`github`.
Completion check: `backend/services/connector_trello_oauth_client.py` exists, a grep for `trello` in `DEFAULT_CONNECTOR_PROVIDER_METADATA` shows `"oauth_supported": True`, and `_get_provider_oauth_handlers` returns handlers for `trello`.

2. [x] [test]
Files: tests/test_connectors_api.py
Action: Update connector API tests to reflect Trello OAuth onboarding.
- Replace or adjust `test_trello_oauth_start_returns_provider_conflict` so it asserts the new OAuth start flow (start -> callback -> test -> refresh/revoke) or, if Trello does not support refresh, assert `refresh` returns 409 with proper message.
- Add a `demo`-based callback flow similar to `notion`/`github` tests so CI can exercise the end-to-end flow without external network calls.
Completion check: `tests/test_connectors_api.py` contains a Trello OAuth start/callback demo flow and assertions updated to expect OAuth onboarding.

3. [x] [backend]
Files: backend/routes/connectors.py, backend/services/connector_oauth_provider_clients.py
Action: Ensure routes import and call the new Trello provider helpers where appropriate (revoke, exchange, refresh). If Trello supports revoke, implement `revoke_trello_token` helper and call it from `revoke_connector` route branch.
Completion check: `revoke_trello_token` function present and `revoke_connector` references added/updated for `trello` provider.

4. [x] [docs]
Files: AGENTS.md (backend/AGENTS.md if present), README.md
Action: Record that Trello now supports OAuth and document required env vars (e.g., `MALCOM_TRELLO_OAUTH_CLIENT_ID` / `MALCOM_TRELLO_OAUTH_CLIENT_SECRET`) and default redirect path.
Completion check: short doc lines added to the connector docs referencing Trello OAuth.


Test impact review

1. tests/test_connectors_api.py — update
- Intent: adjust suite to exercise Trello OAuth start/callback and test/refresh flows.
- Recommended action: update
- Validation command: `pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase::test_trello_*`

2. tests/test_connectors_for_builder.py and ui e2e fixtures — inspect and update if UI expects Trello to be credentials-only
- Intent: UI builder tests may assume Trello is credentials-only.
- Recommended action: review & update
- Validation command: `pytest -q tests/test_connectors_for_builder.py` and `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`

Testing steps

1. [ ] [test]
Files: none (run)
Action: Run targeted unit tests for connectors and OAuth.
Command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase::test_trello_*`
Completion check: tests for Trello OAuth pass locally.

2. [ ] [test]
Files: none (run)
Action: Run connector builder tests and relevant e2e tests that may assume Trello credentials-only.
Command: `./.venv/bin/python -m pytest -q tests/test_connectors_for_builder.py` and `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`
Completion check: builder and e2e tests pass or are updated to the new contract.

Documentation review

1. [ ] [docs]
Files: AGENTS.md, backend/AGENTS.md, README.md
Action: Add brief notes that Trello now supports OAuth and list required config/env vars.
Completion check: files updated with a short paragraph and linked default redirect path.

GitHub update

1. [ ] [github]
Files: stage only the changed files from the steps above (provider client, connectors.py, connector_oauth.py, connector_oauth_provider_clients.py, tests/test_connectors_api.py, docs)
Action: Commit with a focused message and push. Move this task file to `.github/tasks/closed/TASK-012-implement-trello-oauth-workflow.md` in the same commit.
Completion check: `git add <changed-files> && git commit -m "Implement Trello OAuth onboarding and update tests" && git push` completes successfully.
