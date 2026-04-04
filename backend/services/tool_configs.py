"""Managed tool configuration constants, defaults, and read/write helpers.

This module owns the canonical implementations for tool config storage.
It is the source of truth for all tool configuration concerns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.database import fetch_one
from backend.services.settings import read_stored_settings_section
from backend.services.utils import utc_now_iso

DatabaseConnection = Any

# ---------------------------------------------------------------------------
# Settings keys (legacy migration anchors)
# ---------------------------------------------------------------------------

SMTP_TOOL_SETTINGS_KEY = "smtp_tool"
LOCAL_LLM_TOOL_SETTINGS_KEY = "local_llm_tool"
COQUI_TTS_TOOL_SETTINGS_KEY = "coqui_tts_tool"
IMAGE_MAGIC_TOOL_SETTINGS_KEY = "image_magic_tool"

# ---------------------------------------------------------------------------
# Default configs
# ---------------------------------------------------------------------------

DEFAULT_SMTP_TOOL_CONFIG: dict[str, Any] = {
    "enabled": False,
    "target_worker_id": None,
    "bind_host": "127.0.0.1",
    "port": 2525,
    "recipient_email": None,
}
DEFAULT_LOCAL_LLM_TOOL_CONFIG: dict[str, Any] = {
    "enabled": False,
    "provider": "custom",
    "server_base_url": "",
    "model_identifier": "",
    "endpoints": {
        "models": "",
        "chat": "",
        "model_load": "",
        "model_download": "",
        "model_download_status": "",
    },
}
DEFAULT_COQUI_TTS_TOOL_CONFIG: dict[str, Any] = {
    "enabled": False,
    "command": "tts",
    "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
    "speaker": "",
    "language": "",
    "output_directory": "backend/data/generated/coqui-tts",
}
DEFAULT_IMAGE_MAGIC_TOOL_CONFIG: dict[str, Any] = {
    "enabled": False,
    "target_worker_id": None,
    "command": "magick",
}
DEFAULT_TOOL_RETRY_SETTINGS: dict[str, Any] = {
    "default_tool_retries": 2,
}

LOCAL_LLM_ENDPOINT_PRESETS: dict[str, dict[str, Any]] = {
    "custom": {
        "label": "Custom",
        "server_base_url": "",
        "endpoints": {
            "models": "",
            "chat": "",
            "model_load": "",
            "model_download": "",
            "model_download_status": "",
        },
    },
    "lm_studio_api_v1": {
        "label": "LM Studio API v1",
        "server_base_url": "http://127.0.0.1:1234",
        "endpoints": {
            "models": "/api/v1/models",
            "chat": "/api/v1/chat",
            "model_load": "/api/v1/models/load",
            "model_download": "/api/v1/models/download",
            "model_download_status": "/api/v1/models/download/status/:job_id",
        },
    },
}

# ---------------------------------------------------------------------------
# Private DB helpers
# ---------------------------------------------------------------------------


def _get_managed_tool_enabled_state(
    connection: DatabaseConnection,
    tool_id: str,
    *,
    default: bool = False,
) -> bool:
    row = fetch_one(
        connection,
        """
        SELECT enabled
        FROM tools
        WHERE id = ?
        """,
        (tool_id,),
    )
    if row is None:
        return default
    return bool(row["enabled"])


def _save_managed_tool_enabled_state(
    connection: DatabaseConnection,
    tool_id: str,
    enabled: bool,
    *,
    commit: bool = True,
) -> None:
    connection.execute(
        """
        UPDATE tools
        SET enabled = ?, updated_at = ?
        WHERE id = ?
        """,
        (int(enabled), utc_now_iso(), tool_id),
    )
    if commit:
        connection.commit()


def _read_managed_tool_config_row(connection: DatabaseConnection, tool_id: str) -> dict[str, Any] | None:
    row = fetch_one(
        connection,
        """
        SELECT config_json
        FROM tool_configs
        WHERE tool_id = ?
        """,
        (tool_id,),
    )
    if row is None:
        return None

    try:
        parsed = json.loads(row["config_json"])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _save_managed_tool_config_row(
    connection: DatabaseConnection,
    tool_id: str,
    config: dict[str, Any],
    *,
    legacy_settings_key: str | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO tool_configs (tool_id, config_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tool_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = excluded.updated_at
        """,
        (tool_id, json.dumps(config), now, now),
    )
    if legacy_settings_key:
        connection.execute("DELETE FROM settings WHERE key = ?", (legacy_settings_key,))
    connection.commit()
    return config


def _load_managed_tool_config_payload(
    connection: DatabaseConnection,
    *,
    tool_id: str,
    legacy_settings_key: str,
) -> dict[str, Any]:
    stored_config = _read_managed_tool_config_row(connection, tool_id)
    if stored_config is not None:
        return stored_config

    legacy_value = read_stored_settings_section(connection, legacy_settings_key)
    if not isinstance(legacy_value, dict):
        return {}

    migrated_config = dict(legacy_value)
    legacy_enabled = migrated_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        tool_id,
        migrated_config,
        legacy_settings_key=legacy_settings_key,
    )
    if legacy_enabled is not None:
        _save_managed_tool_enabled_state(connection, tool_id, bool(legacy_enabled))
    return migrated_config


# ---------------------------------------------------------------------------
# Tool retries
# ---------------------------------------------------------------------------


def get_default_tool_retries(connection: DatabaseConnection) -> int:
    automation_settings = read_stored_settings_section(connection, "automation") or {}
    try:
        retries = int(automation_settings.get("default_tool_retries", DEFAULT_TOOL_RETRY_SETTINGS["default_tool_retries"]))
    except (TypeError, ValueError):
        retries = DEFAULT_TOOL_RETRY_SETTINGS["default_tool_retries"]
    return max(0, min(10, retries))


# ---------------------------------------------------------------------------
# SMTP tool config
# ---------------------------------------------------------------------------


def get_default_smtp_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SMTP_TOOL_CONFIG))


def get_smtp_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_smtp_tool_config()
    config.update(
        _load_managed_tool_config_payload(
            connection,
            tool_id="smtp",
            legacy_settings_key=SMTP_TOOL_SETTINGS_KEY,
        )
    )
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "smtp",
        default=bool(config.get("enabled")),
    )
    return config


def save_smtp_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "smtp",
        next_config,
        legacy_settings_key=SMTP_TOOL_SETTINGS_KEY,
    )
    return get_smtp_tool_config(connection)


def normalize_smtp_tool_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = get_default_smtp_tool_config()
    normalized.update(config)
    normalized["target_worker_id"] = normalized.get("target_worker_id") or None
    normalized["bind_host"] = str(normalized.get("bind_host") or DEFAULT_SMTP_TOOL_CONFIG["bind_host"])
    raw_port = normalized.get("port")
    normalized["port"] = int(DEFAULT_SMTP_TOOL_CONFIG["port"] if raw_port is None else raw_port)
    normalized["enabled"] = bool(normalized.get("enabled"))
    recipient_email = str(normalized.get("recipient_email") or "").strip().lower()
    normalized["recipient_email"] = recipient_email or None
    return normalized


# ---------------------------------------------------------------------------
# Local LLM tool config
# ---------------------------------------------------------------------------


def get_default_local_llm_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_LOCAL_LLM_TOOL_CONFIG))


def get_local_llm_endpoint_presets() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(LOCAL_LLM_ENDPOINT_PRESETS))


def get_local_llm_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_local_llm_tool_config()
    stored_value = _load_managed_tool_config_payload(
        connection,
        tool_id="llm-deepl",
        legacy_settings_key=LOCAL_LLM_TOOL_SETTINGS_KEY,
    )
    if isinstance(stored_value, dict):
        config.update(stored_value)
        if isinstance(stored_value.get("endpoints"), dict):
            config["endpoints"].update(stored_value["endpoints"])
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "llm-deepl",
        default=bool(config.get("enabled")),
    )
    return config


def save_local_llm_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "llm-deepl",
        next_config,
        legacy_settings_key=LOCAL_LLM_TOOL_SETTINGS_KEY,
    )
    return get_local_llm_tool_config(connection)


def normalize_local_llm_tool_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = get_default_local_llm_tool_config()
    normalized.update(config or {})
    stored_endpoints = config.get("endpoints") if isinstance(config, dict) else None
    if isinstance(stored_endpoints, dict):
        normalized["endpoints"].update(stored_endpoints)

    provider = str(normalized.get("provider") or DEFAULT_LOCAL_LLM_TOOL_CONFIG["provider"]).strip()
    if provider not in LOCAL_LLM_ENDPOINT_PRESETS:
        provider = DEFAULT_LOCAL_LLM_TOOL_CONFIG["provider"]
    normalized["provider"] = provider
    normalized["enabled"] = bool(normalized.get("enabled"))
    normalized["server_base_url"] = str(normalized.get("server_base_url") or "").strip()
    normalized["model_identifier"] = str(normalized.get("model_identifier") or "").strip()
    normalized["endpoints"] = {
        "models": str(normalized["endpoints"].get("models") or "").strip(),
        "chat": str(normalized["endpoints"].get("chat") or "").strip(),
        "model_load": str(normalized["endpoints"].get("model_load") or "").strip(),
        "model_download": str(normalized["endpoints"].get("model_download") or "").strip(),
        "model_download_status": str(normalized["endpoints"].get("model_download_status") or "").strip(),
    }
    return normalized


# ---------------------------------------------------------------------------
# Coqui TTS tool config
# ---------------------------------------------------------------------------


def get_default_coqui_tts_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_COQUI_TTS_TOOL_CONFIG))


def get_coqui_tts_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_coqui_tts_tool_config()
    config.update(
        _load_managed_tool_config_payload(
            connection,
            tool_id="coqui-tts",
            legacy_settings_key=COQUI_TTS_TOOL_SETTINGS_KEY,
        )
    )
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "coqui-tts",
        default=bool(config.get("enabled")),
    )
    return config


def save_coqui_tts_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "coqui-tts",
        next_config,
        legacy_settings_key=COQUI_TTS_TOOL_SETTINGS_KEY,
    )
    return get_coqui_tts_tool_config(connection)


def normalize_coqui_tts_tool_config(config: dict[str, Any], *, root_dir: Path | None = None) -> dict[str, Any]:
    normalized = get_default_coqui_tts_tool_config()
    normalized.update(config or {})
    normalized["enabled"] = bool(normalized.get("enabled"))
    normalized["command"] = str(normalized.get("command") or DEFAULT_COQUI_TTS_TOOL_CONFIG["command"]).strip()
    normalized["model_name"] = str(normalized.get("model_name") or DEFAULT_COQUI_TTS_TOOL_CONFIG["model_name"]).strip()
    normalized["speaker"] = str(normalized.get("speaker") or "").strip()
    normalized["language"] = str(normalized.get("language") or "").strip()
    output_directory = str(normalized.get("output_directory") or DEFAULT_COQUI_TTS_TOOL_CONFIG["output_directory"]).strip()
    if root_dir is not None and not Path(output_directory).is_absolute():
        output_directory = str((root_dir / output_directory).resolve())
    normalized["output_directory"] = output_directory
    return normalized


# ---------------------------------------------------------------------------
# Image Magic tool config
# ---------------------------------------------------------------------------


def get_default_image_magic_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_IMAGE_MAGIC_TOOL_CONFIG))


def get_image_magic_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_image_magic_tool_config()
    config.update(
        _load_managed_tool_config_payload(
            connection,
            tool_id="image-magic",
            legacy_settings_key=IMAGE_MAGIC_TOOL_SETTINGS_KEY,
        )
    )
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "image-magic",
        default=bool(config.get("enabled")),
    )
    return config


def save_image_magic_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "image-magic",
        next_config,
        legacy_settings_key=IMAGE_MAGIC_TOOL_SETTINGS_KEY,
    )
    return get_image_magic_tool_config(connection)


def normalize_image_magic_tool_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = get_default_image_magic_tool_config()
    normalized.update(config or {})
    normalized["enabled"] = bool(normalized.get("enabled"))
    normalized["target_worker_id"] = str(normalized.get("target_worker_id") or "").strip() or None
    normalized["command"] = str(normalized.get("command") or DEFAULT_IMAGE_MAGIC_TOOL_CONFIG["command"]).strip()
    return normalized


__all__ = [name for name in globals() if not name.startswith("_")]
