# Module Contract: automation-step-editors (UI)

## Owner
ui/src/automation/step-editors/

## Responsibilities
- Single dispatch point for step-type-specific editor rendering in the automation builder
- Per-step editor components (Condition, LlmChat, etc.)

## Public API

| Export | File | Notes |
|---|---|---|
| `StepEditorDispatcher` | `index.tsx` | Selects and renders the correct step editor; default re-export alias `StepEditor` |
| `ConditionStepEditor` | `ConditionStepEditor.tsx` | Editor for `condition` step type |
| `LlmChatStepEditor` | `LlmChatStepEditor.tsx` | Editor for `llm_chat` step type |

## Required props (StepEditorDispatcher)
- `step` — `AutomationStepDefinition`
- `context` — current step context for read-only display
- `onChange` — callback for step mutations

## Test selectors
All interactive elements must use `data-testid` prefixed with `step-editor-`.

## Test obligations
Unit tests: `ui/src/automation/__tests__/step-editors.test.tsx`
E2e: `ui/e2e/` automation builder flows.

## Allowed callers
- `ui/src/automation/app.tsx` only — no direct use in other sections.

## Migration rules
New step types must add a corresponding editor component and register it in `StepEditorDispatcher`.
