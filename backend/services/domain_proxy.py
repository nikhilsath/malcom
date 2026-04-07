from __future__ import annotations

import json
import socket
import os
import tempfile
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from typing import Any

from .utils import utc_now_iso


def get_caddy_runtime_path(root_dir: Path) -> Path:
    return root_dir / "data" / "caddy" / "public_proxy_runtime.json"


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


def _probe_proxy_endpoint(domain: str, port: int, scheme: str, timeout_seconds: float) -> dict[str, Any]:
    target = f"{domain}:{port}"
    detail = None
    status_code = None
    reachable = False
    connection = None

    try:
        if scheme == "https":
            connection = HTTPSConnection(domain, port=port, timeout=timeout_seconds)
        else:
            connection = HTTPConnection(domain, port=port, timeout=timeout_seconds)
        connection.request("HEAD", "/")
        response = connection.getresponse()
        status_code = int(response.status)
        reachable = True
    except OSError as exc:
        detail = str(exc)
    finally:
        try:
            connection.close()
        except Exception:
            pass

    return {
        "scheme": scheme,
        "target": target,
        "reachable": reachable,
        "status_code": status_code,
        "detail": detail,
    }


def test_proxy_connection(proxy_settings: dict[str, Any], timeout_seconds: float = 3.0) -> dict[str, Any]:
    domain = str(proxy_settings.get("domain") or "").strip()
    enabled = bool(proxy_settings.get("enabled", False))

    if not domain:
        return {
            "ok": False,
            "message": "Enter a domain before testing the proxy connection.",
            "checks": [
                {
                    "scheme": "dns",
                    "target": "",
                    "reachable": False,
                    "status_code": None,
                    "detail": "No domain configured.",
                }
            ],
        }

    checks: list[dict[str, Any]] = []
    try:
        addresses = socket.getaddrinfo(domain, None)
        ips = sorted({addr[-1][0] for addr in addresses if addr and addr[-1]})
        checks.append(
            {
                "scheme": "dns",
                "target": domain,
                "reachable": bool(ips),
                "status_code": None,
                "detail": f"Resolved to {', '.join(ips)}" if ips else "No DNS records found.",
            }
        )
    except OSError as exc:
        checks.append(
            {
                "scheme": "dns",
                "target": domain,
                "reachable": False,
                "status_code": None,
                "detail": str(exc),
            }
        )
        return {
            "ok": False,
            "message": "Domain DNS resolution failed.",
            "checks": checks,
        }

    if not enabled:
        return {
            "ok": False,
            "message": "Proxy is disabled. Enable it to run endpoint connectivity checks.",
            "checks": checks,
        }

    http_port = int(proxy_settings.get("http_port") or 80)
    https_port = int(proxy_settings.get("https_port") or 443)
    checks.append(_probe_proxy_endpoint(domain, http_port, "http", timeout_seconds))
    checks.append(_probe_proxy_endpoint(domain, https_port, "https", timeout_seconds))

    http_reachable = bool(checks[-2]["reachable"])
    https_reachable = bool(checks[-1]["reachable"])
    if http_reachable and https_reachable:
        message = "HTTP and HTTPS endpoints are reachable."
        ok = True
    elif http_reachable or https_reachable:
        message = "Domain resolved and one endpoint is reachable."
        ok = True
    else:
        message = "Domain resolved, but neither endpoint responded."
        ok = False

    return {
        "ok": ok,
        "message": message,
        "checks": checks,
    }


__all__ = ["get_caddy_runtime_path", "sync_proxy_to_caddy_runtime", "test_proxy_connection"]
