# Playwright Authoring

Use Playwright in this repo for workflow coverage, not route-load smoke alone.

## Defaults

- Run against the real FastAPI app and PostgreSQL test database.
- Stub only unstable boundaries such as third-party OAuth providers or local runtime side effects.
- Keep specs grouped by product area under `app/ui/e2e/`.
- Prefer shared helpers from `app/ui/e2e/support/` over one-off route stubs in each spec.

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

Specs are divided into tiers based on how they interact with the backend.

**Stubbed Playwright tests are prohibited.** Do not use `installDashboardSettingsFixtures` or `page.route()` to intercept first-party backend routes in any Playwright spec. Browser tests must run against the real FastAPI app and real PostgreSQL test database. Isolated frontend-only state tests that do not need browser/system proof belong in Vitest rather than Playwright. (→ R-TEST-010)

### Critical

The `critical` Playwright project (`--project=critical`) runs a minimal real subset that always executes by default in `test-system.sh`. It proves the product boots, the backend is healthy, and at least one critical UI workflow works end-to-end against the real backend.

- `apis-incoming.spec.ts`

This is the primary browser proof for `bash app/scripts/test-system.sh`. Skip with `SKIP_BROWSER_SUITE=1` only in environments where Playwright browsers are not installed.

### Real

Specs that make no `page.route()` intercepts and run against the live Playwright test server (reset DB). These test full end-to-end system behavior:

- `apis-incoming.spec.ts`
- `apis-outgoing.spec.ts`
- `apis-registry.spec.ts`
- `apis-webhooks.spec.ts`
- `automations-builder.spec.ts`
- `automations-data.spec.ts`
- `automations-library.spec.ts`
- `automations-overview.spec.ts`
- `dashboard.spec.ts`
- `github-trigger.spec.ts`
- `scripts-library.spec.ts`
- `settings.spec.ts`
- `shell.spec.ts`
- `tools-catalog.spec.ts`
- `tools-coqui-tts.spec.ts`
- `tools-image-magic.spec.ts`
- `tools-llm-deepl.spec.ts`
- `tools-smtp.spec.ts`

> **AI agent note:** `app/scripts/test-real-failfast.sh` (which delegates to `app/scripts/test-system.sh`) is the recommended first-pass check for AI agents. It builds the environment from scratch, runs backend real tests and the critical browser subset, stops on the first failure, and writes a machine-readable JSON artifact to `app/tests/test-artifacts/system-result.json` (also mirrored to `app/tests/test-artifacts/failfast-result.json`). `bash app/scripts/test-system.sh` is the canonical single command for proving the product works end to end.

