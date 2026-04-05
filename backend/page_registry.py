from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

ServeMode = Literal["served", "redirect"]


@dataclass(frozen=True)
class UiPageEntry:
    route_path: str
    source_html_path: str
    serve_mode: ServeMode
    canonical_route_path: str
    redirect_target: str | None = None
    legacy_aliases: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_served(self) -> bool:
        return self.serve_mode == "served"

    @property
    def is_redirect_only(self) -> bool:
        return self.serve_mode == "redirect"


@lru_cache(maxsize=1)
def load_ui_page_registry() -> tuple[UiPageEntry, ...]:
    registry_path = Path(__file__).resolve().parents[1] / "ui" / "page-registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entries: list[UiPageEntry] = []

    for raw_entry in registry["pages"]:
        canonical_route_path = raw_entry.get("canonicalRoutePath", raw_entry["routePath"])
        entries.append(
            UiPageEntry(
                route_path=raw_entry["routePath"],
                source_html_path=raw_entry["sourceHtmlPath"],
                serve_mode=raw_entry["serveMode"],
                canonical_route_path=canonical_route_path,
                redirect_target=raw_entry.get("redirectTarget"),
                legacy_aliases=tuple(raw_entry.get("legacyAliases", [])),
            )
        )

    _validate_registry(entries)
    return tuple(entries)


def get_served_ui_pages() -> tuple[UiPageEntry, ...]:
    return tuple(entry for entry in load_ui_page_registry() if entry.is_served)


def get_redirect_ui_routes() -> tuple[tuple[str, str], ...]:
    redirect_routes: list[tuple[str, str]] = []
    for entry in load_ui_page_registry():
        if entry.is_served:
            redirect_routes.extend(
                (alias, entry.route_path)
                for alias in entry.legacy_aliases
                if alias not in {"/docs", "/docs/"}
            )
            continue
        if entry.route_path in {"/docs", "/docs/"}:
            continue
        if entry.redirect_target is None:
            raise ValueError(f"Redirect-only UI page '{entry.route_path}' is missing a redirect target.")
        redirect_routes.append((entry.route_path, entry.redirect_target))
    return tuple(redirect_routes)


def _validate_registry(entries: list[UiPageEntry]) -> None:
    route_paths = set()
    served_routes = {entry.route_path for entry in entries if entry.is_served}

    for entry in entries:
        if entry.route_path in route_paths:
            raise ValueError(f"Duplicate UI route path in registry: {entry.route_path}")
        route_paths.add(entry.route_path)
        if not entry.source_html_path.endswith(".html"):
            raise ValueError(f"UI page source must be an HTML path: {entry.source_html_path}")
        if entry.is_redirect_only and entry.redirect_target is None:
            raise ValueError(f"Redirect-only UI page '{entry.route_path}' must define redirect_target")

    for entry in entries:
        if entry.canonical_route_path not in served_routes:
            raise ValueError(
                f"UI page '{entry.route_path}' references missing canonical route '{entry.canonical_route_path}'"
            )
