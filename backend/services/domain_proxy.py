from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .utils import utc_now_iso


def get_caddy_runtime_path(root_dir: Path) -> Path:
    return root_dir / "backend" / "data" / "caddy" / "public_proxy_runtime.json"


def sync_proxy_to_caddy_runtime(root_dir: Path, proxy_settings: dict[str, Any]) -> None:
    path = get_caddy_runtime_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    runtime_payload: dict[str, Any] = {
        "caddy_command": "caddy",
        "desired_enabled": False,
        "domain": "",
        "domain_configured": False,
        "http_port": 80,
        "https_port": 443,
        "last_error": None,
        "managed_by_launcher": True,
        "running": False,
        "updated_at": utc_now_iso(),
    }

    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                runtime_payload.update(existing)
        except (OSError, json.JSONDecodeError):
            # Keep defaults when existing file cannot be read or parsed.
            pass

    domain = str(proxy_settings.get("domain") or "").strip()
    enabled = bool(proxy_settings.get("enabled", False))

    http_port_raw = proxy_settings.get("http_port", 80)
    https_port_raw = proxy_settings.get("https_port", 443)

    try:
        http_port = int(http_port_raw)
    except (TypeError, ValueError):
        http_port = 80

    try:
        https_port = int(https_port_raw)
    except (TypeError, ValueError):
        https_port = 443

    runtime_payload.update(
        {
            "domain": domain,
            "desired_enabled": enabled,
            "domain_configured": bool(domain),
            "http_port": http_port,
            "https_port": https_port,
            "updated_at": utc_now_iso(),
        }
    )

    serialized = json.dumps(runtime_payload, indent=2, sort_keys=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as temporary_file:
        temporary_file.write(serialized)
        temporary_path = temporary_file.name
    os.replace(temporary_path, path)


__all__ = ["get_caddy_runtime_path", "sync_proxy_to_caddy_runtime"]
