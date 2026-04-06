## Execution steps

1. [x] [backend]
Files: backend/services/connectors.py
Action: Add provider onboarding capability metadata for `github`, `notion`, and `trello` in the connector source of truth (OAuth support, required credential fields, scope defaults, redirect behavior, and provider display copy) so backend and UI can share one deterministic contract instead of hardcoded Google-only checks.
Completion check: `backend/services/connectors.py` exposes provider metadata for all four first-party providers (`google`, `github`, `notion`, `trello`) and no onboarding-critical requirement is encoded only inside Google-only branches.

2. [x] [backend]
Files: backend/routes/connectors.py, backend/services/connectors.py
Action: Refactor OAuth start validation to be provider-aware for OAuth-capable connectors: keep Google behavior intact, require client ID (and configured redirect URI) for GitHub and Notion, persist pending OAuth state consistently, and return a clear non-OAuth conflict response when OAuth start is attempted for Trello.
Completion check: `start_connector_oauth` no longer treats non-Google OAuth providers as permissive defaults, and provider-specific validation/error messages exist for GitHub/Notion/Trello.

3. [x] [backend]
Files: backend/routes/connectors.py
Action: Replace synthetic non-Google callback token stubs with provider-aware callback handling: implement GitHub and Notion authorization-code exchange paths, normalize stored token material/status updates/messages, and preserve Trello as non-callback-based setup.
Completion check: `_complete_connector_oauth_result` no longer falls back to generated `token_<code>` values for GitHub/Notion and uses explicit provider exchange logic.

4. [x] [backend]
Files: backend/routes/connectors.py
Action: Make connector lifecycle actions provider-aware for the new parity set: extend `/test`, `/refresh`, and `/revoke` behavior so GitHub/Notion responses match OAuth lifecycle expectations and Trello follows API-key/token lifecycle expectations with actionable status transitions.
Completion check: provider branches for `github`, `notion`, and `trello` exist in lifecycle handlers, and each branch sets explicit status/message outcomes instead of generic fallback messaging.

5. [x] [ui]
Files: ui/settings/connectors.html, ui/scripts/settings/connectors/dom.js, ui/scripts/settings/connectors/state.js
Action: Introduce provider-specific setup panel structure and element wiring for GitHub, Notion, and Trello equivalent to the existing guided Google setup pattern (status badge/message area plus provider-scoped credential inputs and action controls).
Completion check: connectors detail modal contains deterministic provider setup regions for GitHub/Notion/Trello with mapped IDs in `dom.js`, and state helpers can identify provider-specific setup mode without relying on Google-only checks.

6. [x] [ui]
Files: ui/scripts/settings/connectors/render.js, ui/scripts/settings/connectors/form.js, ui/scripts/settings/connectors/oauth.js, ui/scripts/settings/connectors/page.js
Action: Generalize Google-only setup logic into provider-aware onboarding orchestration: provider-specific field visibility, validation, CTA labels, OAuth start behavior for GitHub/Notion, and non-OAuth credential flow for Trello while preserving current Google UX quality and callback handling.
Completion check: these files no longer gate guided onboarding behavior behind only `isGoogleConnector`, and GitHub/Notion/Trello each have explicit setup-state rendering and action logic.

7. [x] [ui]
Files: ui/e2e/support/api-response-builders.ts, ui/e2e/support/connectors-apis-routes.ts
Action: Extend shared Playwright connector fixtures and route mocks so provider-specific OAuth start/callback and lifecycle actions can be exercised for GitHub/Notion plus Trello credential setup without ad hoc inline payloads in specs.
Completion check: support builders/routes include reusable GitHub, Notion, and Trello connector scenarios consumed by specs.

8. [x] [test]
Files: tests/test_connectors_api.py
Action: Add backend API coverage for provider onboarding parity: GitHub OAuth start/callback/refresh/revoke contracts, Notion OAuth start/callback contracts, Trello non-OAuth setup/test/revoke contracts, and provider-specific validation/error cases.
Completion check: `tests/test_connectors_api.py` contains explicit test cases for GitHub, Notion, and Trello onboarding/lifecycle flows beyond existing Google-focused assertions.

9. [x] [test]
Files: ui/e2e/connectors.spec.ts
Action: Expand the connectors browser workflow suite to assert guided provider setup parity: GitHub and Notion OAuth-oriented setup UX plus Trello credential setup UX, including status/message transitions and post-setup action controls.
Completion check: `ui/e2e/connectors.spec.ts` includes separate scenarios for GitHub, Notion, and Trello setup paths and asserts behavior changes (not just route load).

## Test impact review

1. [x] [test]
Files: tests/test_connectors_api.py
Action: Intent: verify backend provider-specific onboarding lifecycle for GitHub/Notion/Trello parity with existing Google behavior. Recommended action: update. Validation command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py`
Completion check: This task file records exact target file, intent, action, and command for the backend onboarding contract suite.

2. [x] [test]
Files: tests/test_connectors_for_builder.py, tests/test_connectors_for_builder_extra.py
Action: Intent: confirm workflow-builder connector option payloads remain stable after provider metadata/onboarding changes. Recommended action: keep.
Completion check: This task file records that builder option tests are expected to remain valid unless connector option contract changes during execution.

3. [x] [test]
Files: ui/e2e/connectors.spec.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/support/api-response-builders.ts
Action: Intent: verify end-to-end provider setup UX parity and shared harness consistency for GitHub/Notion/Trello. Recommended action: update. Validation command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`
Completion check: This task file records exact target files, intent, action, and command for provider onboarding e2e coverage.

## Testing steps

1. [x] [test]
Files: tests/test_connectors_api.py
Action: Run the targeted backend provider-onboarding contract suite after updating tests. Command: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py`
Completion check: The command exits 0.

2. [x] [test]
Files: ui/e2e/connectors.spec.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/support/api-response-builders.ts
Action: Run the targeted connectors browser workflow suite after route mocks and assertions are updated. Command: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts`
Completion check: The command exits 0.

3. [x] [test]
Files: scripts/test-precommit.sh
Action: Run the precommit gate after targeted suites pass to confirm no regression in shared checks. Command: `./scripts/test-precommit.sh`
Completion check: The command exits 0.

## Documentation review

1. [x] [docs]
Files: README.md
Action: Update connector onboarding documentation so provider-specific setup guidance includes GitHub, Notion, and Trello parity expectations (OAuth vs non-OAuth setup paths and where each flow starts in UI).
Completion check: `README.md` describes onboarding behavior for Google, GitHub, Notion, and Trello without leaving Google as the only documented guided flow.

Verification notes:

- Targeted backend contract suite: `./.venv/bin/python -m pytest -q tests/test_connectors_api.py` exited 0 with 15 skips in the current test environment.
- Targeted browser suite: `npm --prefix ui run test:e2e -- e2e/connectors.spec.ts` passed across Chromium, Firefox, and WebKit (`18 passed`).
- Fast gate: `./scripts/test-precommit.sh` passed after updating stale automation unit-test expectations to the current connector-action select flow.
- Full gate: `./scripts/test-full.sh` still reports broader Playwright failures outside the task-008 connector onboarding scenarios, including `ui/e2e/settings.spec.ts` across all browsers, `ui/e2e/apis-outgoing.spec.ts` create-from-connector across all browsers, and `ui/e2e/automations-builder.spec.ts` one WebKit-only context-menu case.

## GitHub update

1. [x] [github]
Files: .github/tasks/open/TASK-008-github-notion-trello-connector-onboarding-parity.md, backend/services/connectors.py, backend/routes/connectors.py, ui/settings/connectors.html, ui/scripts/settings/connectors/dom.js, ui/scripts/settings/connectors/state.js, ui/scripts/settings/connectors/render.js, ui/scripts/settings/connectors/form.js, ui/scripts/settings/connectors/oauth.js, ui/scripts/settings/connectors/page.js, ui/e2e/support/api-response-builders.ts, ui/e2e/support/connectors-apis-routes.ts, ui/e2e/connectors.spec.ts, tests/test_connectors_api.py, README.md
Action: Stage only task-relevant files, commit with a focused message such as `Add GitHub Notion Trello connector onboarding parity`, move this task file to `.github/tasks/closed/` in the same commit, then push.
Completion check: The commit includes only relevant files plus the task-file move to `.github/tasks/closed/`, and push succeeds.

Completion note:

- Follow-up UI cleanup removed the APIs page connector-settings cache fallback in favor of live `GET /api/v1/connectors` reads and connector-specific update events.
- Focused verification for that follow-up path passed with `npm --prefix ui run build` and `npm --prefix ui run test:e2e -- e2e/apis-outgoing.spec.ts`.
