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
| AGENTS.md | reviewed | 2026-04-10 | docs-refresh audit | root policy re-reviewed for audit guidance and schema-group alignment during docs refresh |
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
| backend/services/connector_activities_catalog.py | reviewed | 2026-04-04 | connector-catalog/readme audit | confirmed seeded builder activity coverage is limited to Google and GitHub; DB rows remain canonical when present |
| backend/services/http_presets.py | reviewed | 2026-04-04 | connector-catalog/readme audit | confirmed seeded HTTP preset coverage is limited to Google and GitHub; Notion/Trello have no preset definitions here |
| tests/test_connector_activities_api.py | reviewed | 2026-04-04 | connector-catalog/readme audit | activity API coverage asserts Google and GitHub actions but no Notion/Trello builder actions |
| tests/test_http_presets.py | reviewed | 2026-04-04 | connector-catalog/readme audit | preset coverage asserts Google and GitHub catalogs only |
| ui/src/automation/step-modals/connector-activity-step-form.tsx | reviewed | 2026-04-04 | connector-catalog/readme audit | UI disables providers with no compatible activity catalog and surfaces "No connector actions available for this provider yet." |
| ui/src/automation/__tests__/ConnectorActivityStepForm.dropdown.test.tsx | reviewed | 2026-04-04 | connector-catalog/readme audit | dropdown test remains minimal; current fixture use does not exercise unavailable-provider messaging |
| README.md | reviewed | 2026-04-10 | docs-refresh audit | full product README rewrite based on current routes, schema groups, runtime services, and unfinished feature audit |
| backend/database.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed current schema groups include docs articles/tags plus storage and repo checkout tables |
| backend/routes/api.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed current API surface aggregates runtime, automations, docs, log tables, scripts, settings, storage, workers, connectors, APIs, and tools |
| backend/routes/runtime.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed dashboard, queue, logs, resource history, scheduler, and debug resource-profile endpoints |
| backend/routes/storage.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed storage locations, usage, repo checkout CRUD, and repo sync endpoints |
| backend/routes/tools.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed current managed tool APIs are SMTP, Local LLM, Coqui TTS, and Image Magic |
| backend/routes/docs.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed docs article CRUD surface backed by docs tables and `data/docs/*.md` content |
| backend/routes/ui.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed served and redirect UI routes remain registry-driven |
| backend/services/tool_registry.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed current managed tool catalog and manifest source of truth |
| backend/services/connector_oauth.py | reviewed | 2026-04-10 | docs-refresh audit | confirmed Google, Notion, and Trello browser OAuth flow while GitHub remains credential-only |
| backend/services/github_webhook.py | needs_followup | 2026-04-10 | docs-refresh audit | normalization exists, but dispatch helper still logs placeholder work instead of enqueueing runtime execution |
| backend/services/automation_step_executors/storage.py | needs_followup | 2026-04-10 | docs-refresh audit | dedicated storage step executor still raises not implemented |
| scripts/dev.py | needs_followup | 2026-04-10 | docs-refresh audit | launcher script still references undefined `ROOT_DIR`, so README documents manual startup from `app/` instead |
| ui/settings/connectors.html | reviewed | 2026-04-10 | docs-refresh audit | confirmed connectors live under Settings and expose registry plus auth-policy workflows |
| ui/settings/data.html | reviewed | 2026-04-10 | docs-refresh audit | confirmed storage locations, backups, and log-table storage management; payload redaction still marked coming soon |
| ui/tools/catalog.html | reviewed | 2026-04-10 | docs-refresh audit | confirmed tool catalog remains a metadata and availability editor, not a runtime registry source |
| ui/src/docs/DocsApp.tsx | reviewed | 2026-04-10 | docs-refresh audit | confirmed docs library supports list, detail, create, and edit flows |
| ui/e2e/github-trigger.spec.ts | needs_followup | 2026-04-10 | docs-refresh audit | GitHub trigger browser coverage is still a smoke placeholder rather than an end-to-end workflow assertion |
| ui/page-registry.json | reviewed | 2026-04-04 | connector-catalog/readme audit | verified connectors page is served under Settings, not the APIs section |
| ui/scripts/shell-config.js | reviewed | 2026-04-04 | connector-catalog/readme audit | verified shell nav places Connectors under Settings and APIs includes only registry/incoming/outgoing/webhooks |
