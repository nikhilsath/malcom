# Playwright Authoring

Use Playwright in this repo for workflow coverage, not route-load smoke alone.

## Defaults

- Run against the real FastAPI app and PostgreSQL test database.
- Stub only unstable boundaries such as third-party OAuth providers or local runtime side effects.
- Keep specs grouped by product area under `ui/e2e/`.
- Prefer shared helpers from `ui/e2e/support/` over one-off route stubs in each spec.

## Expectations

- Every user-visible workflow change should add or update Playwright coverage.
- Assert happy path plus a representative error, destructive, or keyboard/focus case when the flow supports it.
- For modal or drawer flows, assert open, action, close, and focus return behavior.
- For pages intentionally set to navigation-only, assert action CTAs and modals are absent so dead-click regressions are caught.
- Keep fixture data deterministic and name records with stable IDs.

## Verification

- Targeted iteration: `cd ui && npx playwright test <spec>`
- Full browser suite: `cd ui && npm run test:e2e`
- Repository completion gate: `./scripts/test-full.sh`

## Port handling

- Playwright defaults to port `4173` for its web server.
- If `4173` is busy, `ui/playwright.config.ts` automatically picks the next available port.
- You can force a port with `PLAYWRIGHT_PORT=<port>`, for example: `cd ui && PLAYWRIGHT_PORT=4190 npx playwright test <spec>`.
