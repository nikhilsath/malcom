# Repo Scan Index

Source of truth for `[AREA: audit]` progress across repo-wide review batches.

## Status Keys

- `pending` - not yet reviewed for the current audit scope
- `in_progress` - partially reviewed in the current audit scope
- `reviewed` - opened and assessed for the current audit scope
- `needs_followup` - reviewed once but needs a second pass
- `blocked` - could not be completed because of a concrete blocker
- `skip_generated` - intentionally excluded generated or forbidden path

## Index

| path | status | last_reviewed | scope | notes |
|---|---|---|---|---|
| AGENTS.md | reviewed | 2026-04-03 | mapping-layer audit | root routing and audit rules reviewed |
| backend/services/workflow_builder.py | reviewed | 2026-04-03 | mapping-layer audit | workflow-builder connector resolver reviewed for source-of-truth and duplication |
| backend/routes/automations.py | reviewed | 2026-04-03 | mapping-layer audit | workflow-connectors API route reviewed |
| backend/services/connectors.py | reviewed | 2026-04-03 | mapping-layer audit | provider catalog, connector storage split, and fallback behavior reviewed |
| backend/services/automation_execution.py | reviewed | 2026-04-03 | mapping-layer audit | settings payload assembly and fallback normalization reviewed |
| backend/routes/settings.py | reviewed | 2026-04-03 | mapping-layer audit | settings patch and backup routes reviewed for connector/settings persistence flow |
| backend/routes/connectors.py | reviewed | 2026-04-03 | mapping-layer audit | connector-specific API surface reviewed for dedicated boundary and hardcoded presets |
| ui/src/automation/builder-api.ts | reviewed | 2026-04-03 | mapping-layer audit | builder support data loading reviewed for duplicated option sources |
| ui/src/automation/useAutomationBuilderController.ts | reviewed | 2026-04-03 | mapping-layer audit | builder state consumption reviewed |
| ui/scripts/settings.js | reviewed | 2026-04-03 | mapping-layer audit | settings page still uses broad settings payload and fallback handling |
| ui/scripts/settings/connectors/page.js | reviewed | 2026-04-03 | mapping-layer audit | connectors page load path reviewed |
| ui/scripts/settings/connectors/render.js | reviewed | 2026-04-03 | mapping-layer audit | connector catalog and metadata rendering reviewed |
| ui/scripts/settings/connectors/form.js | reviewed | 2026-04-03 | mapping-layer audit | connector record shaping reviewed |
| ui/scripts/log-store.js | reviewed | 2026-04-03 | mapping-layer audit | shared settings store fallback and whole-payload mutation reviewed |
| ui/scripts/settings/data.js | reviewed | 2026-04-03 | mapping-layer audit | data page reviewed for local storage location constants and connector-derived options |
| ui/src/automation/constants.ts | reviewed | 2026-04-03 | mapping-layer audit | reviewed; mostly UI labels/templates rather than backend-duplicated option catalogs |
| ui/src/dashboard/constants.ts | reviewed | 2026-04-03 | mapping-layer audit | reviewed; time-window UI constant is isolated and not tied to backend source-of-truth |
| tests/test_connectors_for_builder.py | reviewed | 2026-04-03 | mapping-layer audit | builder connector contract tests reviewed |
| tests/test_connectors_for_builder_extra.py | reviewed | 2026-04-03 | mapping-layer audit | extra builder connector normalization and failure-path tests reviewed |
| tests/test_automations_api.py | reviewed | 2026-04-03 | mapping-layer audit | builder metadata and workflow-connectors API coverage reviewed |
| tests/test_settings_api.py | reviewed | 2026-04-03 | mapping-layer audit | settings/connectors API contract tests reviewed |
| ui/src/automation/__tests__/automation-app.test.tsx | reviewed | 2026-04-03 | mapping-layer audit | builder test harness reviewed for mock payload fidelity |
| ui/e2e/support/dashboard-settings.ts | reviewed | 2026-04-03 | mapping-layer audit | shared settings fixture reviewed for API-shape drift risk |
| ui/e2e/fixtures/connectors/success.json | reviewed | 2026-04-03 | mapping-layer audit | connector fixture reviewed against workflow-connectors response shape |
| ui/e2e/support/automations-scripts.ts | reviewed | 2026-04-03 | mapping-layer audit | builder Playwright route harness reviewed for synthetic metadata and connector payload shaping |
| ui/e2e/support/connectors-apis-routes.ts | reviewed | 2026-04-03 | mapping-layer audit | connectors Playwright route harness reviewed for settings/connectors response shaping |
| backend/services/connector_activities_catalog.py | pending | - | mapping-layer audit | next batch: code-defined connector activity catalog ownership |
| backend/services/http_presets.py | pending | - | mapping-layer audit | next batch: hardcoded HTTP preset catalog ownership |
| tests/test_connector_activities_api.py | pending | - | mapping-layer audit | next batch: connector activity API contract coverage |
| tests/test_http_presets.py | pending | - | mapping-layer audit | next batch: HTTP preset contract coverage |
| ui/src/automation/step-modals/connector-activity-step-form.tsx | pending | - | mapping-layer audit | next batch: frontend consumer of connector activity catalog |
| ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx | pending | - | mapping-layer audit | next batch: fixture fidelity for connector activity dropdown |
