## Execution steps

1. [x] [backend]
Files: app/backend/services/platform_auth.py, app/backend/services/platform_contracts.py, app/backend/routes/platform.py, app/backend/schemas/platform.py
Action: Productionize the hosted frontend session and embed contract by adding the missing lifecycle/metadata needed for long-running hosted sessions and iframe embeds, including explicit builder embed metadata instead of the current minimal compatibility payload.
Completion check: The platform auth/embed files expose session/embed fields beyond the current bootstrap-only contract, and the builder embed descriptor contains explicit lifecycle/handshake metadata required by the host runtime.
Execution note: Verified these files already expose refreshable session lifecycle metadata (`session_lifecycle`, token TTLs, rotation metadata) and explicit embed handshake/lifecycle contract fields (`handshake_channel`, `origin_policy`, lifecycle events, compatibility metadata), so no additional code edits were required for this step.

2. [x] [automation]
Files: frontend/apps/host/main.js, frontend/plugins/automations/src/index.mjs, app/ui/automations/builder.html, app/ui/src/automation/main.tsx
Action: Implement the hosted frontend builder embed flow so the shell can launch the compatibility builder route intentionally, pass/consume the platform metadata it needs, and preserve builder access while the migration remains in compatibility mode.
Completion check: The host app and automations plugin include explicit builder embed handling, and the legacy builder entry files expose the compatibility hooks referenced by the hosted frontend flow.
Execution note: Verified the host app now handles iframe builder embed lifecycle and handshake payloads (`frontend/apps/host/main.js`), the automations plugin exposes explicit native-versus-builder route handling (`frontend/plugins/automations/src/index.mjs`), and the legacy builder entry path exposes compatibility hooks through embed-compatible page metadata plus parent-postMessage handshake wiring (`app/ui/automations/builder.html`, `app/ui/src/automation/main.tsx`).

3. [x] [test]
Files: app/tests/test_platform_api.py, frontend/packages/host/src/plugin-runtime.test.mjs, app/ui/e2e/settings.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/coverage-route-map.json
Action: Rewrite browser/platform coverage to include the hosted frontend path and builder embed flow rather than only the backend-served UI route ownership map, following app/tests/AGENTS.md and AGENTS.md#task-file-construction (R-TASK-002, R-TEST-005, R-TEST-006).
Completion check: The listed tests and coverage map reference the hosted frontend/builder embed workflow and no longer treat backend-served shell coverage as the only browser proof for the migration.
Execution note: Verified the scoped files already encode hosted-frontend and builder-embed coverage: platform API tests assert builder iframe metadata and embed descriptor contract (`app/tests/test_platform_api.py`), host runtime tests preserve iframe/builder route metadata (`frontend/packages/host/src/plugin-runtime.test.mjs`), browser specs include hosted sign-in plus builder iframe flow (`app/ui/e2e/settings.spec.ts`, `app/ui/e2e/shell.spec.ts`), and the coverage map tracks hosted frontend ownership separately from backend-served routes (`app/ui/e2e/coverage-route-map.json`).

## Test impact review

1. [x] [test]
Files: app/tests/test_platform_api.py
Action: Intent: verify hosted frontend token lifecycle and builder embed metadata stay stable as the contract grows; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_platform_api.py`.
Completion check: Platform API tests cover the expanded session/embed contract.
Execution note: Verified `app/tests/test_platform_api.py` already asserts refreshable session lifecycle metadata and workflow-builder embed descriptor lifecycle/compatibility fields, so the test-impact update requirement is satisfied without additional test edits.
Execution note: Confirmed `app/tests/test_platform_api.py` already asserts refreshable session lifecycle metadata (`session_lifecycle`, access/refresh TTL parity, bootstrap token requirement) and explicit builder embed descriptor lifecycle fields (`session_binding`, `compatibility_mode`, `refreshes_session`, metadata compatibility mode).

2. [x] [test]
Files: frontend/packages/host/src/plugin-runtime.test.mjs
Action: Intent: verify the host runtime handles iframe builder routes and hosted session state transitions; Recommended action: update; Validation command: `cd frontend && npm test -- --test-name-pattern="iframe|builder|session"`.
Completion check: Host runtime tests cover builder embed and session-handling behavior.
Execution note: Updated `frontend/packages/host/src/plugin-runtime.test.mjs` to assert hosted builder iframe route metadata includes session lifecycle transition fields (`sessionBinding`, `sessionTransition`, `refreshesSession`) and to verify those fields are preserved in registry and route-card models.

3. [x] [test]
Files: app/ui/e2e/settings.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/coverage-route-map.json
Action: Intent: replace stale browser assumptions that only backend-served shell routes matter with migration-aware coverage for the hosted frontend and builder compatibility flow; Recommended action: update; Validation command: `cd app/ui && npm run test:e2e:coverage && npm run test:e2e:critical`.
Completion check: Browser coverage asserts the migration-aware workflow and the route ownership map reflects the updated intent.
Execution note: Verified `app/ui/e2e/settings.spec.ts` covers hosted-frontend sign-in and hosted settings shell rendering, `app/ui/e2e/shell.spec.ts` covers hosted shell sign-in plus workflow-builder iframe compatibility routing, and `app/ui/e2e/coverage-route-map.json` tracks hosted frontend ownership independently from backend-served routes.

## Testing steps

1. [x] [test]
Files: app/tests/test_platform_api.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_platform_api.py`.
Completion check: Command exits with status 0.
Execution note: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_platform_api.py` passed (2 tests, 0 failures).

2. [x] [test]
Files: frontend/package.json, frontend/packages/host/src/plugin-runtime.test.mjs
Action: Run `cd frontend && npm test`.
Completion check: Command exits with status 0.
Execution note: `cd frontend && npm test` passed (11 tests, 0 failures).

3. [x] [test]
Files: app/ui/e2e/settings.spec.ts, app/ui/e2e/shell.spec.ts, app/ui/e2e/coverage-route-map.json
Action: Run `cd app/ui && npm run test:e2e:coverage && npm run test:e2e:critical`.
Completion check: Command exits with status 0.
Execution note: `cd app/ui && npm run test:e2e:coverage && npm run test:e2e:critical` passed (coverage map OK; 13 critical tests passed).

4. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the required first-pass real-system validation before any broader gate per AGENTS.md#real-test-first-pass-policy (R-TEST-009).
Completion check: Command exits with status 0.
Execution note: `bash app/scripts/test-real-failfast.sh` passed with real startup lifecycle, backend suite, and critical browser checks.

## Documentation review

1. [x] [docs]
Files: README.md, frontend/README.md, data/docs/frontend-plugin-sdk.md
Action: Document the final phase-1 hosted session lifecycle, iframe builder contract, and browser validation path so developers can build for the ecosystem without inferring behavior from code.
Completion check: The docs describe the builder embed flow, hosted session lifecycle, and browser coverage path in concrete terms.
Execution note: Added "Hosted session lifecycle" (refreshable, rolling rotation, TTL env vars), "Builder embed flow" (full embed descriptor field table + handshake sequence), and "Browser validation path" (spec files + run command) to README.md. Added equivalent "Session lifecycle", "Builder embed contract", and "Browser validation" sections to frontend/README.md. Expanded data/docs/frontend-plugin-sdk.md with a full embed descriptor field table, handshake sequence, "Hosted session lifecycle" reference section (session_lifecycle fields, refresh/revoke endpoints), "Browser validation path" table, and additional TTL env vars. Completion check passes: all three files describe the builder embed flow, session lifecycle, and browser coverage path in concrete terms.

