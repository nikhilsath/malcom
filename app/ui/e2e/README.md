# Playwright Authoring

Use Playwright in this repo for workflow coverage, not route-load smoke alone.

## Defaults

- Run against the real FastAPI app and PostgreSQL test database.
- Do not use `installDashboardSettingsFixtures` or `page.route()` interception for first-party backend `/api/v1/**` workflows.
- Isolated frontend-only state/rendering checks belong in Vitest instead of Playwright.
- Keep specs grouped by product area under `app/ui/e2e/`.
- Prefer shared helpers from `app/ui/e2e/support/` for real-flow setup and deterministic assertions.

## Expectations

- Every user-visible workflow change should add or update Playwright coverage.
- Keep `app/ui/e2e/coverage-route-map.json` aligned with `app/ui/page-registry.json`: every served route belongs exactly once in `servedRoutes`, while redirect-only paths stay in `redirectRoutes`.
- Assert happy path plus a representative error, destructive, or keyboard/focus case when the flow supports it.
- For modal or drawer flows, assert open, action, close, and focus return behavior.
- For pages intentionally set to navigation-only, assert action CTAs and modals are absent so dead-click regressions are caught.
- Keep fixture data deterministic and name records with stable IDs.

## Route coverage map

- Validate the served-route ownership map with `cd app/ui && npm run test:e2e:coverage`.
- `servedRoutes` entries must include a workflow contract summary plus the owning spec path and test IDs.
- `redirectRoutes` documents redirect-only paths separately so they do not block served-route ownership checks.
- Retire or delete an older Playwright test only after its replacement spec and test IDs are present in `app/ui/e2e/coverage-route-map.json` and the replacement coverage is passing.

## Verification

- Route ownership gate: `cd app/ui && npm run test:e2e:coverage`
- Targeted iteration: `cd app/ui && npx playwright test <spec>`
- Critical browser subset (default in test-system.sh): `cd app/ui && npm run test:e2e:critical`
- Full browser suite: `cd app/ui && npm run test:e2e`
- **Repository completion gate (canonical):** `bash app/scripts/test-system.sh`

## Port handling

- Playwright defaults to port `4173` for its web server.
- If `4173` is busy, `app/ui/playwright.config.ts` automatically picks the next available port.
- You can force a port with `PLAYWRIGHT_PORT=<port>`, for example: `cd app/ui && PLAYWRIGHT_PORT=4190 npx playwright test <spec>`.

## Test Classification

### Critical

The `critical` Playwright project (`--project=critical`) runs a minimal real subset that always executes by default in `test-system.sh`. It proves the product boots, the backend is healthy, and at least one critical UI workflow works end-to-end against the real backend.

- `shell.spec.ts`
- `settings.spec.ts`

This is the primary browser proof for `bash app/scripts/test-system.sh`. Skip with `SKIP_BROWSER_SUITE=1` only in environments where Playwright browsers are not installed.

### Real

Specs listed here make no first-party `/api/v1/**` route interceptions and run against the live Playwright test server (reset DB). These are the current real end-to-end browser proofs:

- `connectors.spec.ts`
- `settings.spec.ts`
- `shell.spec.ts`

Legacy harness-based specs under `app/ui/e2e/` are not part of the real-browser inventory and should be migrated or retired instead of being documented as real coverage.

### Prohibited Coverage Pattern

Stubbed Playwright coverage for first-party backend workflows is prohibited.

- Do not use `installDashboardSettingsFixtures` in Playwright specs that validate first-party backend flows.
- Do not intercept first-party backend `/api/v1/**` routes with `page.route()` in Playwright specs.
- Keep Playwright for real browser + backend + DB proof only.
- Move UI-only state/rendering checks to Vitest.

> **AI agent note:** `app/scripts/test-real-failfast.sh` (which delegates to `app/scripts/test-system.sh`) is the recommended first-pass check for AI agents. It builds the environment from scratch, runs backend real tests and the critical browser subset, stops on the first failure, and writes a machine-readable JSON artifact to `app/tests/test-artifacts/system-result.json`. `bash app/scripts/test-system.sh` is the canonical single command for proving the product works end to end.
