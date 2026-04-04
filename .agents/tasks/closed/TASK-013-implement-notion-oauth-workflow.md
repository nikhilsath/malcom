Execution steps

1. [ ] [backend]
Files: backend/services/connector_oauth.py, backend/services/connector_oauth_provider_clients.py, backend/routes/connectors.py, tests/test_connectors_api.py
Action: Finish and harden Notion OAuth workflow (use Google as an example for error messages, PKCE, refresh behavior).
- Review existing Notion exchange and refresh helpers in `backend/services/connector_oauth_provider_clients.py` and ensure they fully support PKCE/code_verifier and `demo` code paths for test harnesses.
- Ensure `connector_oauth.complete_connector_oauth` and `refresh_oauth_token` treat Notion identically to GitHub/Google where appropriate (clear errors, require client_secret when needed).
- Add missing revoke behavior (if not present) or verify `revoke_notion_token` is called on revoke path in `backend/routes/connectors.py`.
Completion check: Notion exchange, refresh, and revoke helpers exist and are invoked by routes/service orchestration.

2. [ ] [ui]
Files: ui/e2e/fixtures/connectors/, ui/e2e/automations-builder.spec.ts (or connectors.spec.ts), ui/src/settings/connectors.js or relevant React/TS files
Action: Add or update Playwright e2e coverage for Notion OAuth onboarding.
- Add fixture for Notion OAuth demo response(s) if needed in `ui/e2e/fixtures/connectors/`.
- Add an e2e test that simulates the OAuth start, performs callback to `/api/v1/connectors/notion/oauth/callback?state=...&code=demo-notion` and verifies UI shows connected state.
Completion check: e2e fixture and test added; `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts` passes for the Notion scenario locally.

3. [ ] [test]
Files: tests/test_connectors_api.py
Action: Confirm Notion unit tests exist for start/callback/refresh (they do). Add any additional assertions to check `revoke` behavior and `has_refresh_token` masking.
Completion check: `pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase::test_notion_oauth_start_callback_and_refresh_flow` passes.

4. [ ] [docs]
Files: README.md or backend/AGENTS.md
Action: Update docs to call out Notion OAuth caveats (client_secret required, redirect URI behavior) and example env vars (`MALCOM_NOTION_OAUTH_CLIENT_ID`, `MALCOM_NOTION_OAUTH_CLIENT_SECRET`).
Completion check: docs updated with a short section for Notion OAuth.


Test impact review

1. tests/test_connectors_api.py — keep/update
- Intent: Notion tests already exist and exercise start/callback/refresh flows.
- Recommended action: keep and run; add revoke assertions if missing.
- Validation command: `pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase::test_notion_oauth_start_callback_and_refresh_flow`

2. ui e2e tests — add
- Intent: Add UI-level validation of Notion onboarding flow.
- Recommended action: add new e2e test and fixtures.
- Validation command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`

Testing steps

1. [ ] [test]
Files: none (run)
Action: Run unit tests for connectors and Notion-specific tests.
Command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py::ConnectorsApiTestCase::test_notion_oauth_start_callback_and_refresh_flow`
Completion check: tests pass locally.

2. [ ] [test]
Files: none (run)
Action: Run UI e2e test(s) for Notion.
Command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`
Completion check: e2e test for Notion passes locally.

Documentation review

1. [ ] [docs]
Files: README.md, backend/AGENTS.md
Action: Add short notes and example env vars for Notion OAuth; reference Google example flow.
Completion check: docs file updated with Notion OAuth example.

GitHub update

1. [ ] [github]
Files: stage only changed backend service files, e2e fixtures/tests, unit tests, docs
Action: Commit with a focused message and push. Move this task file to `.agents/tasks/closed/TASK-013-implement-notion-oauth-workflow.md` in the same commit.
Completion check: `git add <changed-files> && git commit -m "Harden Notion OAuth flow and add e2e coverage" && git push` completes successfully.
