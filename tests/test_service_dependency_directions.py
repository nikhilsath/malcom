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


def test_automation_run_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/automation_runs.py"))
    assert "backend.services.helpers" not in modules


def test_serialization_module_avoids_helpers_dependency() -> None:
    modules = _imported_modules(Path("backend/services/serialization.py"))
    assert "backend.services.helpers" not in modules
