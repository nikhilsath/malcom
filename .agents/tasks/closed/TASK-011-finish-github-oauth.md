## Closed

Completed on 2026-04-03.

Summary:
- Added GitHub OAuth environment-variable fallback support in the backend for `MALCOM_GITHUB_OAUTH_CLIENT_ID` and `MALCOM_GITHUB_OAUTH_CLIENT_SECRET`.
- Hardened GitHub OAuth token exchange/refresh helpers so GitHub responses normalize consistent token payload keys and keep PKCE + JSON error handling intact.
- Updated the Connectors UI and Playwright harness so GitHub OAuth uses the dedicated client-secret input path without prompt-style fallback.
- Added backend tests for GitHub env-var fallback and demo callback/refresh coverage.
- Documented GitHub OAuth env-var fallback plus the redirect URI requirement.

Verification:
- `./.venv/bin/pytest -q tests/test_connectors_api.py tests/test_connector_oauth_service.py tests/test_settings_api.py tests/test_startup_lifecycle.py tests/test_connectors_for_builder.py tests/test_connectors_for_builder_extra.py`
- `npm run build` in `ui/`
- `npm run test:e2e -- e2e/connectors.spec.ts` in `ui/`

