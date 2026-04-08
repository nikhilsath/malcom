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
