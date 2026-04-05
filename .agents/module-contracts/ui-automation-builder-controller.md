# Module Contract: useAutomationBuilderController (UI)

## Owner
ui/src/automation/useAutomationBuilderController.ts

## Responsibilities
- Central state machine for the automation builder: step selection, drawer open/close, validation, save/run, URL sync
- Exposes a single typed controller object consumed by `app.tsx`

## Public API

| Export | Notes |
|---|---|
| `useAutomationBuilderController()` | Returns controller object with step state, handlers, and derived state |

## Test obligations
Unit tests: `ui/src/automation/__tests__/automation-app.test.tsx`

## Allowed callers
- `ui/src/automation/app.tsx` only.

## Migration rules
New builder concerns (e.g., multi-select, run history) must be added as additional hooks composed into the controller; do not put rendering logic in this hook.
