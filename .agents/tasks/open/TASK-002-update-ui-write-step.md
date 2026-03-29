Confirm and implement UI rename and full-option support for the Write step

Purpose: Rename the user-facing "Log" step to "Write" in the UI (keep non-breaking internals where possible), expose all write storage options in the UI (storage_type, target, new_file/append semantics, and any storage-specific settings), and add Playwright tests asserting the options are present and functional.

Goal: Deliver a UI-first change that is non-breaking for existing automations, makes the new write-storage options discoverable and editable, and includes automated Playwright coverage verifying the main flows.

Repository verification (quick scan results)

Files discovered that reference the Log / Write UI surface:
- `ui/src/automation/data-flow.ts` (step rendering logic; contains `if (step.type === "log")`)
- `ui/src/automation/add-step-modal.tsx` (step chooser; imports `LogStepForm`)
- `ui/src/automation/step-modals/log-step-form.tsx` (form component to edit log/write options)
- `ui/src/automation/types.ts` (StepType and presets; includes `{ value: "log", label: "Log" }`)
- `ui/src/automation/app.tsx` (renders step-specific forms)
- `ui/src/automation/step-modals/log-step-form.css` and `ui/styles/pages/automation-log-step.css` (styles)
- `ui/src/automation/*.tsx` other automation components referencing `LogStepForm` or `log` type
- `ui/e2e/` (Playwright tests directory — new tests should go here)

If any of these locations are different in your working tree, stop and notify the task owner before editing.

Execution steps

1. [ ] [Route: ui]
Action: Verify exact UI symbol locations and determine the safest rename strategy (copy-only label change vs. changing the step `type` value). Inspect `ui/src/automation/types.ts`, `ui/src/automation/add-step-modal.tsx`, `ui/src/automation/step-modals/log-step-form.tsx`, and `ui/src/automation/data-flow.ts` to ensure we can rename UI copy without breaking internal contracts.
Completion check: Documented decision: either (A) change labels/copy only and keep `type: "log"` internally, or (B) change type to `"write"` and add backend compatibility changes. Include the list of exact files and symbols to edit.

2. [ ] [Route: ui]
Action: Implement UI label changes: where user-facing labels/readable names say "Log" or "Log step", change them to "Write" or "Write step". Do not rename TypeScript symbol names or internal `type` values unless step 1 decided to change them. Update icons/alt text as needed (e.g., `add-step-type-log-icon` -> keep id but update accessible text to "Write").
Completion check: UI strings updated and app builds locally (`npm --prefix ui run build` or equivalent) without errors.

3. [ ] [Route: ui]
Action: Add UI inputs in `LogStepForm` to surface the full write options: `storage_type` (dropdown: `csv`, `table`, `json`, `other`), `target` (text/id selector), `storage_new_file` / `new_file` toggle, and an advanced collapsible section showing `storage_path` (read-only) and optional overrides. Validate form state and serialize into the step config payload that the backend expects.
Completion check: When saving the step in the UI, the outgoing API payload includes `config.storage_type`, `config.target`, and `config.new_file` (or equivalent names agreed with backend). Provide a sample payload in the run notes.

4. [ ] [Route: backend]
Action: Verify backend API and step-handling accept and interpret the UI-provided keys (`storage_type`, `target`, `new_file`). Inspect `backend/routes/automations.py` and the write-step executor in `backend/services/automation_execution.py` (or the module added earlier) to confirm compatibility. If a mismatch exists, add minimal server-side parsing to accept the UI fields without changing existing behavior.
Completion check: Backend accepts the new keys (via integration test or quick API call) and does not error when receiving them; documented mapping is created.

5. [ ] [Route: ui]
Action: Add Playwright end-to-end tests under `ui/e2e/automation-write-step.spec.ts` (or matching project naming) that:
- Open the automation editor, add the `Write` step via the add-step modal.
- For each `storage_type` (`csv`, `table`, `json`) configure the required fields and save.
- Assert the saved step payload is stored (either by intercepting the outgoing API request or by asserting the UI shows saved values). For `json`, assert the `new_file` toggle default is on and can be toggled off.
Completion check: New e2e tests exist and run locally with `npm --prefix ui run test:e2e` (or repo's Playwright script), able to pass against local test server or mock responses.

6. [ ] [Route: test]
Action: Run the Playwright tests and the unit tests that cover automation UI flows. Fix any test regressions. Use `npm --prefix ui run test:e2e` and the repository test helpers.
Completion check: Playwright tests for the write step pass locally in CI-like mode.

7. [ ] [Route: docs]
Action: Update documentation to reflect the UI rename and new options: update `ui/AGENTS.md` (if present), `AGENTS.md` quick-task references, and inline code comments in `ui/src/automation/types.ts` explaining `storage_type` semantics and matching backend behavior.
Completion check: Docs updated and include example screenshots or payload examples.

8. [ ] [Route: github]
Action: Stage only the changed UI, test, and doc files, commit with a focused message (`UI: rename Log->Write; expose write storage options; add e2e tests`), and push the branch. Move this task file to `.agents/tasks/closed/` as part of the GitHub update step.
Completion check: Changes pushed and the task file moved to `.agents/tasks/closed/` in the same commit.

Test impact review

- Affected UI files: `ui/src/automation/*` and `ui/styles/*`.
- New Playwright tests: `ui/e2e/automation-write-step.spec.ts` (or similar) — add to Playwright test set.
- Backend tests: minimal risk if we keep internal `type` as `log`; if changing internal `type` to `write`, update backend tests that assert step types (search `tests/test_ui_html_routes.py` / automation tests for `log` usages).
- Decide: prefer non-breaking UI-only copy changes to avoid extensive backend test churn.

Testing steps

1. [ ] [Route: ui]
Action: Run `npm --prefix ui install` (if needed) and run Playwright tests locally: 

```bash
npm --prefix ui install
npm --prefix ui run test:e2e -- --reporter=list
```

Completion check: New automation-write-step tests appear in Playwright output and pass.

2. [ ] [Route: test]
Action: Run backend unit test subset relevant to automations (`pytest tests/test_automations_api.py::...`) to ensure no regressions.
Completion check: Affected backend tests pass.

Documentation review

- Update `AGENTS.md` and `ui/AGENTS.md` with the UI rename note and the new write-step form fields mapping to backend keys.
- Add a short example of the step config JSON the UI produces.

GitHub update

- Stage only changed UI, tests, and docs files.
- Commit with message: `UI: rename Log->Write; expose write storage options; add e2e tests`.
- Push branch and move this task file to `.agents/tasks/closed/`.

Notes and hand-off

- Prefer non-breaking label-only changes unless you explicitly want to change the internal `step.type` string. If you decide to change `step.type`, convert this task into two coordinated tasks (one UI + backend migration, plus test updates).
- Keep UI IDs (e.g., `add-step-type-log-icon`) only if renaming would break CSS/automation selectors; update selectors in Playwright tests accordingly.
- If you want, I can implement the UI changes and tests in a follow-up task-executor run — tell me if you want me to proceed to implement now, or just create this task for your team to pick up.
