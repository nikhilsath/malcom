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
- Full browser suite: `cd app/ui && npm run test:e2e`
- Repository completion gate: `./app/scripts/test-full.sh`

## Port handling

- Playwright defaults to port `4173` for its web server.
- If `4173` is busy, `app/ui/playwright.config.ts` automatically picks the next available port.
- You can force a port with `PLAYWRIGHT_PORT=<port>`, for example: `cd app/ui && PLAYWRIGHT_PORT=4190 npx playwright test <spec>`.

## Test Classification

Specs are divided into two tiers based on whether they intercept API calls:

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
- `github-trigger.spec.ts`
- `scripts-library.spec.ts`
- `tools-catalog.spec.ts`
- `tools-coqui-tts.spec.ts`
- `tools-image-magic.spec.ts`
- `tools-llm-deepl.spec.ts`
- `tools-smtp.spec.ts`

### Stubbed

Specs that use `installDashboardSettingsFixtures` or `page.route()` to intercept API calls. These test UI logic and rendering under controlled state rather than end-to-end system behavior. **Stubbed specs are secondary to real specs and are not the primary proof for critical workflows.** Use them to verify isolated UI logic and rendering; use real specs (or the backend real-test runner) to prove that critical workflows function end-to-end.

- `settings.spec.ts` — fully stubbed via `installDashboardSettingsFixtures` and additional direct `page.route()` calls for `/api/v1/storage/locations`
- `dashboard.spec.ts` — fully stubbed via `installDashboardSettingsFixtures`
- `shell.spec.ts` — fully stubbed via `installDashboardSettingsFixtures`
- `automation-write-step.spec.ts` — partially stubbed via `page.route`
- `connectors.spec.ts` — partially stubbed via `page.route`

The `"stubbed"` Playwright project in `playwright.config.ts` targets the three fully-stubbed specs (`settings.spec.ts`, `dashboard.spec.ts`, `shell.spec.ts`) so they can be run in isolation: `cd app/ui && npx playwright test --project=stubbed`.

> **AI agent note:** `app/scripts/test-real-failfast.sh` runs only backend real tests (no Playwright) and is the recommended first-pass check for AI agents. It stops on the first failure and writes a machine-readable JSON artifact to `app/tests/test-artifacts/failfast-result.json`.

