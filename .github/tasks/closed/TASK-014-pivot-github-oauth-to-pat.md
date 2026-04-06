Execution steps

1. [x] [backend]
Files: backend/services/connectors.py, backend/services/connector_oauth.py, backend/services/connector_oauth_provider_clients.py, backend/routes/connectors.py, backend/schemas/settings.py
Action: Pivot GitHub connector contract from OAuth app flow to Personal Access Token (PAT) flow as the canonical backend path.
- In provider catalog/metadata (`DEFAULT_CONNECTOR_CATALOG`, `DEFAULT_CONNECTOR_PROVIDER_METADATA`), change GitHub onboarding to token-based setup, disable OAuth callback/refresh expectations for GitHub, and update required/setup fields to PAT-oriented fields.
- Remove GitHub-specific OAuth exchange/refresh dependencies from OAuth service orchestration so GitHub no longer relies on `start -> callback -> refresh` for connection lifecycle.
- Keep GitHub runtime probe/testing logic (`_probe_github_access_token`) as the verification mechanism for saved PAT credentials.
- Ensure GitHub revoke behavior is local credential clearing only (no client secret dependency) with updated response copy.
- Keep Google/Notion/Trello OAuth behavior unchanged.
Completion check: `backend/services/connectors.py` no longer marks GitHub as OAuth onboarding, `backend/services/connector_oauth.py` no longer routes GitHub through OAuth exchange/refresh handlers, and `backend/routes/connectors.py` GitHub revoke branch no longer requires GitHub client secret.

2. [x] [ui]
Files: ui/settings/connectors.html, ui/scripts/settings/connectors/dom.js, ui/scripts/settings/connectors/state.js, ui/scripts/settings/connectors/form.js, ui/scripts/settings/connectors/render.js, ui/scripts/settings/connectors/page.js, ui/scripts/settings/connectors/oauth.js, ui/styles/pages/settings.css
Action: Implement a GitHub-specific PAT setup experience that is intentionally different from Google OAuth UI and not treated as a shared OAuth template flow.
- Replace GitHub detail form inputs from OAuth app fields (client ID, client secret, redirect URI) to PAT-centric fields (integration name + PAT credential entry and any GitHub-specific helper copy required by product direction).
- Ensure GitHub path uses save/test/revoke lifecycle and does not expose `Start OAuth`/`Refresh token` actions.
- Keep Google/Notion/Trello provider panels and OAuth behavior intact.
- Update provider-specific status text and action labels so GitHub copy references PAT setup, token rotation/replacement, and direct credential save.
Completion check: GitHub panel markup and DOM bindings no longer reference GitHub OAuth client/redirect fields, and GitHub connector flow can be driven through save/test/revoke controls without invoking OAuth start.

3. [x] [test]
Files: tests/test_connectors_api.py, tests/test_connector_oauth_service.py, tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py, ui/e2e/connectors.spec.ts, ui/e2e/support/api-response-builders.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/coverage-route-map.json
Action: Replace stale GitHub OAuth assumptions with PAT contract coverage before broad validation.
- Backend tests: replace GitHub OAuth start/callback/refresh assertions with PAT-oriented save/test/revoke expectations and explicit conflict assertions if GitHub OAuth start is now unsupported.
- Service tests: remove GitHub OAuth env-var and callback refresh scenarios; keep OAuth service coverage focused on providers that still use OAuth.
- Builder tests: update GitHub fixture expectations if auth type/status assumptions changed from OAuth-specific defaults.
- E2E tests and harness: rewrite GitHub scenario from guided OAuth redirect flow to PAT setup flow, update fixture metadata contract, and update route-map wording to reflect PAT behavior.
Completion check: no GitHub test in the edited files requires `/api/v1/connectors/github/oauth/start` success path, and E2E GitHub scenario text/assertions describe PAT setup lifecycle.

4. [x] [docs]
Files: README.md
Action: Update connector documentation to describe GitHub PAT onboarding instead of GitHub OAuth app credentials.
- Remove or rewrite references to `MALCOM_GITHUB_OAUTH_CLIENT_ID` and `MALCOM_GITHUB_OAUTH_CLIENT_SECRET` as the primary GitHub setup path.
- Add concise GitHub PAT guidance aligned with the new UI and backend behavior.
Completion check: `README.md` GitHub connector section no longer instructs OAuth app setup as the primary path.


Test impact review

1. [x] [test]
Files: tests/test_connectors_api.py
Action: Intent: validate connector API contract after GitHub pivot from OAuth to PAT. Recommended action: replace GitHub OAuth flow tests with PAT save/test/revoke and optional OAuth-start conflict assertions. Validation command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py -k github`.
Completion check: GitHub-focused connector API tests pass with PAT-based expectations.

2. [x] [test]
Files: tests/test_connector_oauth_service.py
Action: Intent: keep OAuth orchestration tests aligned to providers that still use OAuth. Recommended action: update by removing GitHub OAuth-specific cases and ensuring coverage remains for Google/Notion/Trello OAuth lifecycle. Validation command: `./.venv/bin/python -m pytest -q tests/test_connector_oauth_service.py`.
Completion check: OAuth service test suite passes without GitHub OAuth assumptions.

3. [x] [test]
Files: tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py
Action: Intent: keep workflow-builder connector listing assertions aligned with GitHub auth_type/source contract. Recommended action: update auth_type/provider assertions where they currently encode OAuth-specific GitHub defaults. Validation command: `./.venv/bin/python -m pytest -q tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py`.
Completion check: builder connector tests pass with updated GitHub fixture expectations.

4. [x] [test]
Files: ui/e2e/connectors.spec.ts, ui/e2e/support/api-response-builders.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/coverage-route-map.json
Action: Intent: preserve user-visible connector onboarding coverage while moving GitHub from OAuth redirect UX to PAT UX. Recommended action: replace GitHub OAuth e2e path and fixture metadata with PAT-specific workflow assertions. Validation command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`.
Completion check: GitHub connectors e2e coverage passes with PAT workflow assertions.


Testing steps

1. [x] [test]
Files: none (review-only)
Action: Run targeted backend connector API regression for GitHub contract updates: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py -k github`.
Completion check: command exits with code 0.

2. [x] [test]
Files: none (review-only)
Action: Run OAuth service regression to confirm non-GitHub OAuth providers remain healthy: `./.venv/bin/python -m pytest -q tests/test_connector_oauth_service.py`.
Completion check: command exits with code 0.

3. [x] [test]
Execution: parallel_ok
Files: none (review-only)
Action: Run connector builder regressions after GitHub auth contract updates: `./.venv/bin/python -m pytest -q tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py`.
Completion check: command exits with code 0.

4. [x] [test]
Files: none (review-only)
Action: Run browser workflow coverage for connector onboarding lifecycle: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`.
Completion check: command exits with code 0.

5. [x] [test]
Files: none (review-only)
Action: Run focused API smoke regression for connectors routes after contract changes: `./.venv/bin/python -m pytest -q tests/test_api_smoke_matrix.py -k connectors`.
Completion check: command exits with code 0.


Documentation review

1. [x] [docs]
Files: README.md
Action: Confirm GitHub setup documentation matches PAT-only onboarding behavior and does not leave stale OAuth-env guidance as primary setup instructions.
Completion check: README connector guidance reflects PAT setup language and matches UI/backend behavior.


GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-014-pivot-github-oauth-to-pat.md, backend/services/connectors.py, backend/services/connector_oauth.py, backend/services/connector_oauth_provider_clients.py, backend/routes/connectors.py, backend/schemas/settings.py, ui/settings/connectors.html, ui/scripts/settings/connectors/dom.js, ui/scripts/settings/connectors/state.js, ui/scripts/settings/connectors/form.js, ui/scripts/settings/connectors/render.js, ui/scripts/settings/connectors/page.js, ui/scripts/settings/connectors/oauth.js, ui/styles/pages/settings.css, tests/test_connectors_api.py, tests/test_connector_oauth_service.py, tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py, ui/e2e/connectors.spec.ts, ui/e2e/support/api-response-builders.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/coverage-route-map.json, README.md
Action: Stage only task-relevant files, commit with a focused message, push, and move this task file to `.github/tasks/closed/TASK-014-pivot-github-oauth-to-pat.md` in the same commit.
Completion check: `git add <task-relevant-files> && git mv .github/tasks/open/TASK-014-pivot-github-oauth-to-pat.md .github/tasks/closed/TASK-014-pivot-github-oauth-to-pat.md && git commit -m "Pivot GitHub connector from OAuth to PAT onboarding" && git push` completes successfully.