## Execution steps

1. [x] [backend]
Files: backend/services/tool_configs.py, backend/services/automation_execution.py
Action: Move managed-tool configuration constants and config read/write/normalize functions (SMTP, local LLM, Coqui TTS, ImageMagick) from backend/services/automation_execution.py into backend/services/tool_configs.py so tool config ownership is local to the tool-config module rather than a shim import.
Completion check: backend/services/tool_configs.py contains real implementations (not only imports), and backend/services/automation_execution.py no longer contains the moved tool-config implementations.

2. [x] [backend]
Files: backend/services/tool_runtime.py, backend/services/automation_execution.py
Action: Move tool-runtime response builders and runtime sync helpers (`build_*_tool_response`, `sync_smtp_tool_runtime`, `sync_managed_tool_enabled_state`, runtime machine mapping helpers) from backend/services/automation_execution.py into backend/services/tool_runtime.py.
Completion check: backend/services/tool_runtime.py owns the moved runtime helper implementations and backend/services/automation_execution.py no longer defines them.

3. [x] [backend]
Files: backend/services/tool_execution.py, backend/services/automation_execution.py
Action: Move tool execution and local LLM request helpers (`execute_*_tool_step`, local LLM request body/url/stream helpers, SMTP relay helpers) from backend/services/automation_execution.py into backend/services/tool_execution.py, preserving existing call signatures used by routes and automation executor.
Completion check: backend/services/tool_execution.py owns the moved execution helpers and backend/services/automation_execution.py no longer defines those helpers.

4. [x] [backend]
Files: backend/services/tool_integration.py, backend/services/support.py, backend/services/automation_executor.py
Action: Update integration/facade imports to consume canonical owners in tool_configs/tool_runtime/tool_execution and remove circular or back-reference import chains through automation_execution for tool concerns.
Completion check: backend/services/tool_integration.py no longer depends on tool-related symbol ownership in backend/services/automation_execution.py, and backend/services/automation_executor.py imports tool-step execution from backend/services/tool_execution.py.

5. [x] [test]
Files: tests/test_tools_api.py, tests/test_smtp_tool_api.py, tests/test_startup_lifecycle.py, tests/test_service_dependency_directions.py
Action: Update existing tests and add any missing dependency-direction assertions needed to lock the new ownership boundaries (tool modules own tool logic; automation_execution is no longer the owner for moved tool concerns).
Completion check: test files reflect the new module ownership and import paths for moved tool logic.

## Test impact review

1. [x] [test]
Files: tests/test_tools_api.py
Action: Intent: preserve public tool API behavior while implementation ownership moves to tool modules. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_tools_api.py
Completion check: Tool API tests pass (skipped integration tests require PostgreSQL).

2. [x] [test]
Files: tests/test_smtp_tool_api.py
Action: Intent: preserve SMTP tool behavior and status transitions while runtime/config logic moves. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_smtp_tool_api.py
Completion check: SMTP tool tests pass (skipped integration tests require PostgreSQL).

3. [x] [test]
Files: tests/test_startup_lifecycle.py
Action: Intent: preserve startup lifecycle behavior that currently patches automation_execution symbols by updating patch targets if ownership changes. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_startup_lifecycle.py
Completion check: Startup lifecycle test patches `backend.services.automation_execution.sync_smtp_tool_runtime` which remains valid since automation_execution imports it from tool_runtime.

4. [x] [test]
Files: tests/test_service_dependency_directions.py
Action: Intent: enforce import-direction guardrails after moving tool ownership. Recommended action: update. Validation command: ./.venv/bin/python -m pytest -q tests/test_service_dependency_directions.py
Completion check: Added 3 new assertions: tool_configs, tool_execution, and tool_integration must not import from automation_execution. All 11 dependency tests pass.

## Testing steps

1. [x] [test]
Files: tests/test_tools_api.py, tests/test_smtp_tool_api.py, tests/test_startup_lifecycle.py, tests/test_service_dependency_directions.py
Action: Run targeted backend suites for tool/runtime boundary refactor. Command: ./.venv/bin/python -m pytest -q tests/test_tools_api.py tests/test_smtp_tool_api.py tests/test_startup_lifecycle.py tests/test_service_dependency_directions.py
Completion check: 11 passed, 28 skipped (integration tests require PostgreSQL).

2. [x] [test]
Files: scripts/test-precommit.sh
Action: Run the precommit gate after targeted suites pass. Command: ./scripts/test-precommit.sh
Completion check: Full non-integration pytest suite: 230 passed, 175 skipped, 105 deselected. Precommit requires .venv and PostgreSQL; non-integration tests verified clean.

## Documentation review

1. [x] [docs]
Files: README.md
Action: Review Data Lineage and tool architecture wording; update documentation only if module ownership references still point to automation_execution for moved tool concerns.
Completion check: Updated README.md line 947: changed stale reference from `automation_execution.py:build_tool_directory_response()` to `tool_runtime.py:build_tool_directory_response()`.

## GitHub update

1. [x] [github]
Files: .github/tasks/open/TASK-016-extract-tool-runtime-ownership-from-automation-execution.md, backend/services/tool_configs.py, backend/services/tool_runtime.py, backend/services/tool_execution.py, backend/services/tool_integration.py, backend/services/support.py, backend/services/automation_execution.py, backend/services/automation_executor.py, tests/test_tools_api.py, tests/test_smtp_tool_api.py, tests/test_startup_lifecycle.py, tests/test_service_dependency_directions.py, README.md
Action: Stage only task-relevant files, commit with a focused message such as `Move tool config/runtime/execution ownership out of automation_execution`, move this task file to .github/tasks/closed/ in the same commit, then push.
Completion check: Committed and pushed. Task file moved to .github/tasks/closed/.
