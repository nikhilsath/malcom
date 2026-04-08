# Test Impact Report - TASK-011

## Coverage map and gate changes

- `ui/e2e/coverage-route-map.json` now assigns every served UI route in `ui/page-registry.json` to at least one owning Playwright spec and test ID.
- `scripts/check-playwright-route-coverage.mjs` validates the route map before broad browser execution.
- `scripts/test-precommit.sh`, `scripts/test-full.sh`, and `ui/package.json` now run the coverage-map check through `npm --prefix ui run test:e2e:coverage`.

## Affected Playwright specs

- `ui/e2e/settings.spec.ts`
  Replacement and ownership: now owns `/settings/access.html` with `saves access controls and restores the defaults`, alongside the existing workspace, logging, notifications, and data settings coverage.
- `ui/e2e/shell.spec.ts`
  Replacement and ownership: kept as the redirect assertion owner for legacy dashboard and settings routes; no retirement in this task.
- `ui/e2e/dashboard.spec.ts`
  Replacement and ownership: continues to own the dashboard home workflow and the redirect-backed devices, logs, and queue workflows listed in the coverage map.
- `ui/e2e/connectors.spec.ts`
  Replacement and ownership: owns `/settings/connectors.html` for guided OAuth, credential setup, and callback handling.
- `ui/e2e/automations-overview.spec.ts`
  Replacement and ownership: owns `/automations/overview.html`.
- `ui/e2e/automations-library.spec.ts`
  Replacement and ownership: owns `/automations/library.html`.
- `ui/e2e/automations-builder.spec.ts`
  Replacement and ownership: shares `/automations/builder.html` ownership with `ui/e2e/automation-write-step.spec.ts`.
- `ui/e2e/automation-write-step.spec.ts`
  Replacement and ownership: supplements `/automations/builder.html` with write-step storage assertions.
- `ui/e2e/automations-data.spec.ts`
  Replacement and ownership: owns `/automations/data.html`.
- `ui/e2e/apis-registry.spec.ts`
  Replacement and ownership: owns `/apis/registry.html`.
- `ui/e2e/apis-incoming.spec.ts`
  Replacement and ownership: owns `/apis/incoming.html`.
- `ui/e2e/apis-outgoing.spec.ts`
  Replacement and ownership: owns `/apis/outgoing.html`.
- `ui/e2e/apis-webhooks.spec.ts`
  Replacement and ownership: owns `/apis/webhooks.html`.
- `ui/e2e/tools-catalog.spec.ts`
  Replacement and ownership: owns `/tools/catalog.html`.
- `ui/e2e/tools-coqui-tts.spec.ts`
  Replacement and ownership: owns `/tools/coqui-tts.html`.
- `ui/e2e/tools-llm-deepl.spec.ts`
  Replacement and ownership: owns `/tools/llm-deepl.html`.
- `ui/e2e/tools-smtp.spec.ts`
  Replacement and ownership: owns `/tools/smtp.html`.
- `ui/e2e/tools-image-magic.spec.ts`
  Replacement and ownership: owns `/tools/image-magic.html`.
- `ui/e2e/scripts-library.spec.ts`
  Replacement and ownership: owns `/scripts/library.html`.

## Retirement rule for this task

- No Playwright specs were retired in `TASK-011`.
- Future deletions are blocked until the replacement spec path and test IDs are present in `ui/e2e/coverage-route-map.json` and the replacement coverage passes through the route-coverage gate.
