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
    modules = _imported_modules(Path("backend/services/runtime_workers.py"))
    assert "backend.services.helpers" not in modules


def test_automation_executor_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/automation_executor.py"))
    assert "backend.services.helpers" not in modules


def test_automation_run_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/automation_runs.py"))
    assert "backend.services.helpers" not in modules


def test_serialization_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/serialization.py"))
    assert "backend.services.helpers" not in modules


def test_connectors_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/connectors.py"))
    assert "backend.services.helpers" not in modules


def test_workflow_builder_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/workflow_builder.py"))
    assert "backend.services.helpers" not in modules


def test_tool_runtime_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/tool_runtime.py"))
    assert "backend.services.helpers" not in modules


def test_api_resources_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/api_resources.py"))
    assert "backend.services.helpers" not in modules
