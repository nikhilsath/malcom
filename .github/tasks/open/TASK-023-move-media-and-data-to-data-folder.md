# TASK-023-move-media-and-data-to-data-folder

## Execution steps

1. [x] [backend]
Files: data/media/, data/backups/, data/logs/, data/workflows/, media/api_icon.png, media/bot_icon, media/conditional_icon.png, media/favicon.ico, media/google_logo.png, media/logo.png, media/logs_icon.png, media/script_icon.png, media/tools_icon.png, backend/data/backups/, backend/data/logs/, backend/data/workflows/
Action: Move media assets and runtime data directories into top-level data/ as the canonical location. Use tracked moves for tracked files. If compatibility symlinks exist from earlier attempts, remove them; this task uses direct code-path migration and must not rely on symlink shims.
Completion check: All listed media files exist under data/media, runtime directories exist under data/backups + data/logs + data/workflows, and neither media nor backend/data is a symlink.

2. [x] [backend]
Files: backend/main.py, backend/services/logging_service.py, backend/services/domain_proxy.py, backend/services/dashboard_logs.py, backend/services/connector_activities_github_repos.py, backend/services/settings_backup_restore.py
Action: Replace hardcoded filesystem references from backend/data or root media directory to the new canonical data/* paths. Keep the public URL contract at /media (only filesystem source changes), following AGENTS.md#implementation-quality-and-source-of-truth (R-FIX-001, R-SOT-001).
Completion check: These files resolve filesystem locations through root/data/* and no longer use root/backend/data/* or root/media for storage locations.

3. [ ] [backend]
Files: backend/schemas/settings.py, backend/services/helpers.py, backend/services/tool_configs.py, backend/services/automation_execution.py, backend/services/automation_step_executors/log.py
Action: Update default settings/config values from backend/data/* to data/* for workflow storage and generated output directories so new writes use canonical paths without compatibility indirection.
Completion check: No backend/data/* default literals remain in these files; defaults now point to data/workflows or data/generated/* as appropriate.

4. [ ] [ui]
Files: ui/tools/coqui-tts.html, ui/settings/data.html
Action: Update user-facing path placeholders/examples from backend/data/* to data/* so UI guidance matches runtime canonical paths.
Completion check: These UI files no longer reference backend/data/* placeholders.

5. [ ] [test]
Files: tests/test_ui_html_routes.py, tests/test_runtime_api.py, tests/test_tools_api.py, tests/api_smoke_registry/tools_cases.py, ui/e2e/tools-coqui-tts.spec.ts, ui/e2e/support/tools.ts
Action: Update stale tests and fixtures to reflect canonical data/* filesystem paths and new media fixture location under data/media. Apply stale-test cleanup before broader validation per AGENTS.md#task-file-construction (R-TASK-002).
Completion check: Updated test files contain data/* paths where applicable and no longer rely on backend/data/* path literals that changed in this task.

6. [ ] [docs]
Files: README.md, docs/settings-reference.md, docs/backup-process.md, AGENTS.md, backend/AGENTS.md, tests/AGENTS.md
Action: Align operator/developer documentation and policy references with the canonical data/* locations (backups, logs, workflows, caddy runtime paths), following AGENTS.md#documentation-ownership-model (R-DOC-001).
Completion check: These docs no longer claim backend/data/* as the canonical runtime location where this task migrated behavior to data/*.


## Test impact review

1. [ ] [test]
Files: tests/test_ui_html_routes.py
Action: Affected test: tests/test_ui_html_routes.py::UiHtmlRoutesTestCase::test_serves_favicon_from_media_directory. Intent: ensure favicon is still served via /favicon.ico after media filesystem source moved to data/media. Recommended action: update. Validation command: pytest tests/test_ui_html_routes.py::UiHtmlRoutesTestCase::test_serves_favicon_from_media_directory -q
Completion check: Test fixture writes favicon under the migrated media source path and the targeted command is listed for execution.

2. [ ] [test]
Files: tests/test_runtime_api.py
Action: Affected tests: tests/test_runtime_api.py::RuntimeApiTestCase::test_dashboard_logs_endpoint_returns_normalized_entries and tests/test_runtime_api.py::RuntimeApiTestCase::test_dashboard_logs_clear_endpoint_truncates_application_and_caddy_logs. Intent: verify dashboard log ingestion/clear behavior with logs now under data/logs and data/caddy. Recommended action: update. Validation command: pytest tests/test_runtime_api.py::RuntimeApiTestCase::test_dashboard_logs_endpoint_returns_normalized_entries tests/test_runtime_api.py::RuntimeApiTestCase::test_dashboard_logs_clear_endpoint_truncates_application_and_caddy_logs -q
Completion check: Runtime API tests build fixtures in migrated directories and command is listed for execution.

3. [ ] [test]
Files: tests/test_tools_api.py, tests/api_smoke_registry/tools_cases.py, ui/e2e/tools-coqui-tts.spec.ts, ui/e2e/support/tools.ts
Action: Affected tests: tool API and e2e fixtures that use backend/data/generated/* sample paths. Intent: keep tool contracts consistent with migrated default paths. Recommended action: update. Validation commands: pytest tests/test_tools_api.py -q and cd ui && npx playwright test e2e/tools-coqui-tts.spec.ts
Completion check: Sample/expected generated output paths in these tests use data/generated/* and both validation commands are listed.

4. [ ] [test]
Files: tests/test_main_app_factory.py, tests/test_settings_api.py
Action: Affected tests: tests/test_main_app_factory.py::MainAppFactoryTestCase::test_create_app_registers_core_routes_and_static_mounts and tests/test_settings_api.py::SettingsApiTestCase::test_get_settings_returns_seeded_defaults. Intent: verify unchanged API route surface (/media mount remains) and updated default settings payload contract. Recommended action: keep. Validation command: none (covered in Testing section).
Completion check: Keep decision documented with explicit intent.


## Testing

1. [ ] [test]
Files: tests/test_ui_html_routes.py, tests/test_main_app_factory.py, tests/test_runtime_api.py, tests/test_settings_api.py
Action: Run targeted backend verification after implementation edits:
- pytest tests/test_ui_html_routes.py::UiHtmlRoutesTestCase::test_serves_favicon_from_media_directory -q
- pytest tests/test_main_app_factory.py::MainAppFactoryTestCase::test_create_app_registers_core_routes_and_static_mounts -q
- pytest tests/test_runtime_api.py::RuntimeApiTestCase::test_dashboard_logs_endpoint_returns_normalized_entries tests/test_runtime_api.py::RuntimeApiTestCase::test_dashboard_logs_clear_endpoint_truncates_application_and_caddy_logs -q
- pytest tests/test_settings_api.py::SettingsApiTestCase::test_get_settings_returns_seeded_defaults -q
Completion check: All listed pytest commands complete successfully.

2. [ ] [test]
Files: tests/test_tools_api.py, tests/api_smoke_registry/tools_cases.py, ui/e2e/tools-coqui-tts.spec.ts, ui/e2e/support/tools.ts
Action: Run path-contract verification for tool defaults and e2e fixture usage:
- pytest tests/test_tools_api.py -q
- cd ui && npx playwright test e2e/tools-coqui-tts.spec.ts
Completion check: Tool API tests and the targeted Playwright spec pass with migrated data/* paths.

3. [ ] [test]
Files: ui/tools/coqui-tts.html, ui/settings/data.html
Action: Build UI to confirm updated placeholder/example text changes do not break bundle generation:
- cd ui && npm run build
Completion check: UI build succeeds.


## GitHub update

1. [ ] [github]
Files: data/media/*, data/backups/*, data/logs/*, data/workflows/*, backend/main.py, backend/services/logging_service.py, backend/services/domain_proxy.py, backend/services/dashboard_logs.py, backend/services/connector_activities_github_repos.py, backend/services/settings_backup_restore.py, backend/schemas/settings.py, backend/services/helpers.py, backend/services/tool_configs.py, backend/services/automation_execution.py, backend/services/automation_step_executors/log.py, ui/tools/coqui-tts.html, ui/settings/data.html, tests/test_ui_html_routes.py, tests/test_runtime_api.py, tests/test_tools_api.py, tests/api_smoke_registry/tools_cases.py, ui/e2e/tools-coqui-tts.spec.ts, ui/e2e/support/tools.ts, README.md, docs/settings-reference.md, docs/backup-process.md, AGENTS.md, backend/AGENTS.md, tests/AGENTS.md, .gitignore
Action: Stage only Task 23 migration files, commit with a task-specific message, and push following AGENTS.md#github-update-workflow.
Completion check: git log -1 --pretty=%B shows a Task 23 migration commit and git push completes for the current branch.
