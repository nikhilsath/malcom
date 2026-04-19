## Execution steps

1. [ ] [tools]
Files: app/backend/routes/tools.py, app/backend/schemas/tools.py, app/backend/services/tool_runtime.py, app/backend/services/coqui_tts_runtime.py, app/backend/services/coqui_tts_installation.py
Action: Follow AGENTS.md#implementation-quality-and-source-of-truth (R-CODE-001, R-FIX-001) — add a dedicated Coqui installation service that installs and removes the runtime inside the repo virtualenv, extend the Coqui tool response schema/runtime payload with installation action state, and expose thin `/api/v1/tools/coqui-tts/install` plus `/api/v1/tools/coqui-tts/remove` handlers from `app/backend/routes/tools.py`.
Completion check: `app/backend/routes/tools.py` contains install/remove Coqui endpoints, install/remove subprocess ownership lives in `app/backend/services/coqui_tts_installation.py` rather than inline in the route file, and `app/backend/schemas/tools.py` plus `app/backend/services/tool_runtime.py` expose the added installation state used by the UI.

2. [ ] [ui]
Files: app/ui/tools/coqui-tts.html, app/ui/scripts/tools/coqui-tts.js
Action: Add deterministic install/remove controls and loading/error states to the Coqui page, wire them to the new Coqui install/remove API actions, and replace the current static unfinished note with live workflow guidance per app/ui/AGENTS.md.
Completion check: `app/ui/tools/coqui-tts.html` defines install/remove control IDs, `app/ui/scripts/tools/coqui-tts.js` sends install/remove requests to `/api/v1/tools/coqui-tts/install` and `/api/v1/tools/coqui-tts/remove`, and the page no longer renders the “not implemented yet” note.

3. [ ] [test]
Files: app/tests/test_tools_api.py, app/tests/api_smoke_registry/tools_cases.py
Action: Update backend API coverage for Coqui install/remove and keep `/api/v1/tools/**` smoke coverage aligned with AGENTS.md (R-TEST-003) by adding smoke cases for the new routes.
Completion check: `app/tests/test_tools_api.py` asserts install/remove behavior and error paths, and `app/tests/api_smoke_registry/tools_cases.py` includes smoke entries for both new Coqui routes.

4. [ ] [test]
Files: app/ui/e2e/tools-coqui-tts.spec.ts
Action: Replace the current stubbed Coqui Playwright coverage with a real backend workflow assertion for install/remove plus runtime-backed configuration save, following app/tests/AGENTS.md frontend rules against first-party route interception.
Completion check: `app/ui/e2e/tools-coqui-tts.spec.ts` no longer imports or calls `stubCoquiTtsTool` / `stubToolSettings`, and the spec asserts the install/remove workflow against the served app.

5. [ ] [docs]
Files: README.md
Action: Remove the unfinished Coqui note and document the implemented install/remove flow once the runtime management workflow is available, following AGENTS.md#documentation-ownership-model (R-DOC-001).
Completion check: README no longer states that Coqui install and removal are not implemented in the app.

## Test impact review

1. [ ] [test]
Files: app/tests/test_tools_api.py
Action: Intent: verify Coqui install/remove route contracts, runtime-state reporting, and config persistence behavior; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_tools_api.py -k coqui`.
Completion check: Targeted API coverage includes install/remove success and failure paths.

2. [ ] [test]
Files: app/tests/api_smoke_registry/tools_cases.py
Action: Intent: keep internal API smoke coverage aligned with new `/api/v1/tools/coqui-tts/install` and `/api/v1/tools/coqui-tts/remove` routes; Recommended action: update; Validation command: `./.venv/bin/pytest -c app/pytest.ini app/tests/test_api_smoke_matrix.py`.
Completion check: The smoke registry includes both new Coqui routes and the smoke matrix stays in sync.

3. [ ] [test]
Files: app/ui/e2e/tools-coqui-tts.spec.ts
Action: Intent: replace stubbed browser coverage with a real-system assertion for the Coqui install/remove workflow and saved runtime selections; Recommended action: replace; Validation command: `npm run test:e2e -- e2e/tools-coqui-tts.spec.ts`.
Completion check: Browser coverage exercises the real backend workflow instead of intercepted first-party API responses.

## Testing

1. [ ] [test]
Files: app/scripts/test-real-failfast.sh
Action: Run `bash app/scripts/test-real-failfast.sh` as the required first-pass real-system gate before additional targeted coverage, following AGENTS.md#real-test-first-pass-policy (R-TEST-009).
Completion check: Command exits with status 0.

2. [ ] [test]
Files: app/tests/test_tools_api.py, app/tests/test_api_smoke_matrix.py
Action: Run `./.venv/bin/pytest -c app/pytest.ini app/tests/test_tools_api.py app/tests/test_api_smoke_matrix.py -k coqui`.
Completion check: Command exits with status 0.

3. [ ] [test]
Files: app/ui/tools/coqui-tts.html, app/ui/scripts/tools/coqui-tts.js
Action: Run `npm run build` in `app/ui/` to verify the Coqui page wiring and bundled assets after the new install/remove controls are added.
Completion check: Command exits with status 0.

4. [ ] [test]
Files: app/ui/e2e/tools-coqui-tts.spec.ts
Action: Run `npm run test:e2e -- e2e/tools-coqui-tts.spec.ts` in `app/ui/`.
Completion check: Command exits with status 0.

## GitHub update

1. [ ] [github]
Files: .github/tasks/open/TASK-041-add-coqui-tool-install-remove-flow.md, app/backend/routes/tools.py, app/backend/schemas/tools.py, app/backend/services/tool_runtime.py, app/backend/services/coqui_tts_runtime.py, app/backend/services/coqui_tts_installation.py, app/ui/tools/coqui-tts.html, app/ui/scripts/tools/coqui-tts.js, app/tests/test_tools_api.py, app/tests/api_smoke_registry/tools_cases.py, app/ui/e2e/tools-coqui-tts.spec.ts, README.md
Action: Stage only the Coqui task and implementation files, then run `git add <files> && git commit -m "Add Coqui install and remove workflow" && git push` following AGENTS.md#github-update-workflow.
Completion check: `git log -1 --oneline` shows the new commit, and `git status --short` is clean for the listed files.
