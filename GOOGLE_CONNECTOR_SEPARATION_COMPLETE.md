# Google Connector Flow Status

This file supersedes the earlier completion note that described a dedicated Google-only settings card.

## Current Product State

- Google onboarding starts from the shared **Connect provider** flow on `ui/settings/connectors.html`.
- Selecting Google opens the shared connector detail modal with Google-specific OAuth fields and redirect guidance.
- The settings page entry is `ui/scripts/settings/connectors.js`, with page-local modules under `ui/scripts/settings/connectors/`.
- Google remains part of the connector provider catalog and is stored as a normal connector record with provider-aware OAuth behavior.

## No Longer Accurate

The earlier implementation note is obsolete because the product no longer uses:

- a dedicated `#settings-connectors-google-section`
- a Google-only standalone connect/disconnect card
- `ui/scripts/connectors.js` as the implementation source of truth
- provider catalog filtering that removes Google from the shared connector flow

## Verification Targets

- `ui/settings/connectors.html`
- `ui/scripts/settings/connectors.js`
- `ui/scripts/settings/connectors/`
- `tests/test_connectors_api.py`
- `ui/e2e/smoke.spec.ts`
