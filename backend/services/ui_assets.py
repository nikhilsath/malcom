"""UI asset path helpers and built-asset validation.

Primary identifiers: ``get_ui_dir``, ``get_ui_dist_dir``, ``ensure_built_ui``, and
``get_built_ui_file`` for server startup and static asset routing.
"""

from __future__ import annotations

from pathlib import Path


def get_ui_dir(root_dir: Path) -> Path:
    return root_dir / "ui"


def get_ui_dist_dir(root_dir: Path) -> Path:
    return get_ui_dir(root_dir) / "dist"


def ensure_built_ui(root_dir: Path) -> None:
    dist_dir = get_ui_dist_dir(root_dir)
    required_paths = [
        dist_dir / "dashboard" / "home.html",
        dist_dir / "assets",
    ]
    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        missing_display = ", ".join(str(path.relative_to(root_dir)) for path in missing_paths)
        raise RuntimeError(
            "Built UI assets are missing. Run './malcom' or 'npm run build' in 'ui/' before starting the backend. "
            f"Missing: {missing_display}"
        )


def get_built_ui_file(root_dir: Path, relative_path: str) -> Path:
    return get_ui_dist_dir(root_dir) / relative_path.lstrip("/")


__all__ = ["ensure_built_ui", "get_built_ui_file", "get_ui_dir", "get_ui_dist_dir"]
