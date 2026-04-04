## Execution steps

1. [x] [ui]
Files: ui/src/automation/app.tsx, ui/src/automation/step-editors/
Action: Extract the large inline step editor rendering in ui/src/automation/app.tsx into dedicated step-editor components under ui/src/automation/step-editors/ (for log/write, HTTP, connector activity, script, tool, condition, and LLM chat sections) while preserving existing element ids used by tests.
Completion check: ui/src/automation/app.tsx no longer defines the full inline step-editor branch tree, and step-editor components exist under ui/src/automation/step-editors/.

2. [x] [ui]
Files: ui/src/automation/app.tsx, ui/src/automation/step-editors/index.ts
Action: Introduce a single step-editor dispatch component/export that selects the correct editor by step type so app.tsx delegates to a focused renderer instead of embedding all conditional JSX branches.
Completion check: app.tsx uses the step-editor dispatcher component and does not directly contain per-step editor JSX branches.

3. [x] [ui]
Files: ui/src/automation/useAutomationBuilderController.ts, ui/src/automation/hooks/
Action: Extract URL synchronization and run-flash timer concerns from useAutomationBuilderController.ts into focused hooks under ui/src/automation/hooks/ to reduce controller responsibility without changing controller return contract.
Completion check: useAutomationBuilderController.ts delegates URL-sync and run-flash lifecycle logic to extracted hooks and keeps the same public return shape consumed by app.tsx.

4. [x] [test]
Files: ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Action: Update/add unit tests for the extracted editor components and ensure existing app tests still cover node selection, drawer behavior, and provider-aware connector action rendering after the split.
Completion check: unit tests reference extracted components/hooks where applicable and preserve prior behavior assertions.

## Test impact review

1. [ ] [test]
Files: ui/src/automation/__tests__/automation-app.test.tsx
Action: Intent: keep builder shell behavior stable while editor rendering is decomposed. Recommended action: update. Validation command: npm --prefix ui run test -- src/automation/__tests__/automation-app.test.tsx
Completion check: The task records app-level UI behavior assertions aligned to the refactored component structure.

2. [ ] [test]
Files: ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Action: Intent: keep provider-aware connector activity dropdown behavior and disabled-state messaging stable after component extraction. Recommended action: update. Validation command: npm --prefix ui run test -- src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Completion check: The task records connector activity dropdown assertions against the refactored editor surface.

3. [ ] [test]
Files: ui/e2e/automations-builder.spec.ts
Action: Intent: preserve end-to-end builder workflow behavior with unchanged route/UI contracts after structural refactor. Recommended action: keep.
Completion check: The task records e2e coverage as expected to remain unless selector contracts change.

## Testing steps

1. [ ] [test]
Files: ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Action: Run focused automation builder unit tests. Command: npm --prefix ui run test -- src/automation/__tests__/automation-app.test.tsx src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx
Completion check: The command exits 0.

2. [ ] [test]
Files: ui/e2e/automations-builder.spec.ts
Action: Run the builder workflow e2e regression test. Command: npm --prefix ui run test:e2e -- e2e/automations-builder.spec.ts
Completion check: The command exits 0.

## Documentation review

1. [ ] [docs]
Files: README.md
Action: Review automation builder implementation notes and update only if component/hook ownership references in docs become inaccurate after extraction.
Completion check: README.md reflects the current ownership layout or the task records that no documentation change was required.

## GitHub update

1. [x] [github]
Files: .agents/tasks/open/TASK-017-split-automation-builder-app-editor-components.md, ui/src/automation/app.tsx, ui/src/automation/step-editors/, ui/src/automation/hooks/, ui/src/automation/useAutomationBuilderController.ts, ui/src/automation/__tests__/automation-app.test.tsx, ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx, ui/e2e/automations-builder.spec.ts, README.md
Action: Stage only task-relevant files, commit with a focused message such as `Split automation builder editor rendering into focused components and hooks`, move this task file to .agents/tasks/closed/ in the same commit, then push.
Completion check: The commit includes only task-relevant files plus the task file move to .agents/tasks/closed/, and push succeeds.
