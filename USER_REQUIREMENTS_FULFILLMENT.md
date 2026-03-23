# Connector Requirements Fulfillment

This note replaces the older Google-separation document that described a dedicated Google card and prompt-driven OAuth setup.

## Current Fulfillment Summary

- Google connector onboarding is provider-aware, but it runs through the shared connector modal/detail workflow instead of a separate page section.
- The active entry point is `ui/scripts/settings/connectors.js`, backed by page-local modules in `ui/scripts/settings/connectors/`.
- OAuth setup stays in the connector details modal, where the Google draft is prepared, credentials are captured, and the redirect URI remains editable.
- The shared connector registry continues to store Google alongside other provider records, while the backend keeps Google-specific OAuth endpoints and provider-aware activity definitions.

## Current Verification Targets

- `ui/settings/connectors.html`
- `ui/scripts/settings/connectors.js`
- `ui/scripts/settings/connectors/`
- `backend/routes/connectors.py`
- `tests/test_connectors_api.py`
- `tests/test_settings_api.py`
- `ui/e2e/smoke.spec.ts`
