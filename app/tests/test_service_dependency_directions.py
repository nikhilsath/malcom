from __future__ import annotations

import ast
from pathlib import Path


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
    return modules


def test_runtime_worker_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/runtime_workers.py"))
    assert "backend.services.helpers" not in modules


def test_automation_executor_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/automation_executor.py"))
    assert "backend.services.helpers" not in modules


def test_automation_run_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/automation_runs.py"))
    assert "backend.services.helpers" not in modules


def test_serialization_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/serialization.py"))
    assert "backend.services.helpers" not in modules


def test_connectors_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/connectors.py"))
    assert "backend.services.helpers" not in modules


def test_workflow_builder_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/workflow_builder.py"))
    assert "backend.services.helpers" not in modules


def test_tool_runtime_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/tool_runtime.py"))
    assert "backend.services.helpers" not in modules


def test_api_resources_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("app/backend/services/api_resources.py"))
    assert "backend.services.helpers" not in modules


def test_tool_configs_module_does_not_import_automation_execution() -> None:
    modules = _imported_modules(Path("app/backend/services/tool_configs.py"))
    assert "backend.services.automation_execution" not in modules


def test_tool_execution_module_does_not_import_automation_execution() -> None:
    modules = _imported_modules(Path("app/backend/services/tool_execution.py"))
    assert "backend.services.automation_execution" not in modules


def test_tool_integration_module_does_not_import_automation_execution() -> None:
    modules = _imported_modules(Path("app/backend/services/tool_integration.py"))
    assert "backend.services.automation_execution" not in modules
