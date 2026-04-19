## Execution steps

1. [x] [backend]
Files: app/backend/services/platform_contracts.py, app/backend/routes/platform.py, app/backend/schemas/platform.py
Action: Replace the current hardcoded phase-1 plugin/catalog metadata with a backend-owned manifest contract that can express the real first-party feature surfaces and their mount requirements, keeping the hosted frontend contract in the canonical `/api/v1/platform/*` path.
Completion check: The platform contract files expose manifest data for the first-party plugins without relying on the current placeholder-only metadata shape.

2. [x] [ui]
Execution: parallel_ok
Files: frontend/apps/host/main.js, frontend/packages/host/src/plugin-runtime.mjs, frontend/plugins/dashboard/src/index.mjs, frontend/plugins/apis/src/index.mjs, frontend/plugins/tools/src/index.mjs, frontend/plugins/scripts/src/index.mjs, frontend/plugins/settings/src/index.mjs, frontend/plugins/docs/src/index.mjs
Action: Replace placeholder host/plugin rendering with real hosted frontend screens that load backend platform/bootstrap data, render plugin-owned navigation, and show feature-specific content instead of generic placeholder cards.
Completion check: The listed frontend plugin files no longer render the current placeholder copy-only panels, and the host runtime maps resolved routes to feature-specific plugin renderers.

3. [x] [automation]
Files: frontend/plugins/automations/src/index.mjs, frontend/apps/host/main.js
Action: Expand the automations plugin so the hosted frontend distinguishes native automations routes from the iframe-backed builder route and presents a real automation landing flow rather than a static compatibility note.
Completion check: The automations plugin exposes a native hosted route plus a distinct builder-launch path, and the host app routes both through the plugin registry.

4. [x] [test]
Files: frontend/packages/host/src/plugin-runtime.test.mjs, frontend/packages/sdk/src/index.test.mjs, app/tests/test_platform_api.py
Action: Update platform/package tests so they assert the richer plugin manifest and hosted route behavior instead of only structural presence.
Completion check: The updated tests assert concrete first-party plugin manifests and hosted route resolution for the real feature surfaces.

## Test impact review

1. [x] [test]
Files: app/tests/test_platform_api.py
Action: Intent: verify backend platform bootstrap/plugin catalog responses match the richer hosted frontend contract; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_platform_api.py`.
Completion check: Platform API tests assert the expanded plugin manifest and route data.

2. [x] [test]
Files: frontend/packages/host/src/plugin-runtime.test.mjs
Action: Intent: verify the host runtime resolves the richer first-party plugin route set and capability gating; Recommended action: update; Validation command: `cd frontend && npm test -- --test-name-pattern="createPluginRegistry|plugin"`.
Completion check: Host runtime tests cover the real plugin route/registry behavior instead of only the placeholder contract.
Execution note: Updated stale host runtime assertions for plugin count and builder route resolution; `cd frontend && npm test -- --test-name-pattern="createPluginRegistry|plugin"` passed.

3. [x] [test]
Files: frontend/packages/sdk/src/index.test.mjs
Action: Intent: verify the SDK still validates the manifest schema as it grows to support real first-party plugins; Recommended action: update; Validation command: `cd frontend && npm test -- --test-name-pattern="validatePluginManifest|normalizePluginManifest"`.
Completion check: SDK tests cover the updated manifest rules needed by the richer first-party plugin contract.
Execution note: `cd frontend && npm test -- --test-name-pattern="validatePluginManifest|normalizePluginManifest"` passed (11 tests, 0 failures).

## Testing steps

1. [x] [test]
Files: app/tests/test_platform_api.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_platform_api.py`.
Completion check: Command exits with status 0.
Execution note: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_platform_api.py` passed (2 tests, 0 failures) when rerun from the repository root.

2. [x] [test]
Files: frontend/package.json, frontend/packages/sdk/src/index.test.mjs, frontend/packages/host/src/plugin-runtime.test.mjs
Action: Run `cd frontend && npm test`.
Completion check: Command exits with status 0.
Execution note: `cd frontend && npm test` passed (11 tests, 0 failures).

3. [x] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the required first-pass real-system validation before any broader gate per AGENTS.md#real-test-first-pass-policy (R-TEST-009).
Completion check: Command exits with status 0.
Execution note: `bash app/scripts/test-real-failfast.sh` passed after hosted frontend platform and browser contract updates.

## Documentation review

1. [x] [docs]
Files: README.md, frontend/README.md, data/docs/frontend-plugin-sdk.md
Action: Document the first-party hosted frontend plugin contract, route ownership, and current migration boundaries using AGENTS.md#documentation-ownership-model (R-DOC-001).
Completion check: The docs describe real first-party plugin surfaces and no longer present the hosted frontend only as a shell/placeholder scaffold.
Execution note: Updated all three files to describe the seven first-party plugins and their real hosted routes; removed "phase-1", "placeholder", and "Incomplete feature" framing. Completion check grep confirmed zero matches.

