"""Tool configuration defaults, normalization, and persistence helpers.

Primary identifiers: default config constants, get/load/save helpers, and normalization
functions for SMTP, local LLM, Coqui TTS, Image Magic, and retry settings.
"""

from __future__ import annotations

from backend.services.tool_runtime import (
    COQUI_TTS_TOOL_SETTINGS_KEY,
    DEFAULT_COQUI_TTS_TOOL_CONFIG,
    DEFAULT_IMAGE_MAGIC_TOOL_CONFIG,
    DEFAULT_LOCAL_LLM_TOOL_CONFIG,
    DEFAULT_SMTP_TOOL_CONFIG,
    DEFAULT_TOOL_RETRY_SETTINGS,
    IMAGE_MAGIC_TOOL_SETTINGS_KEY,
    LOCAL_LLM_ENDPOINT_PRESETS,
    LOCAL_LLM_TOOL_SETTINGS_KEY,
    SMTP_TOOL_SETTINGS_KEY,
    get_coqui_tts_tool_config,
    get_default_coqui_tts_tool_config,
    get_default_image_magic_tool_config,
    get_default_local_llm_tool_config,
    get_default_smtp_tool_config,
    get_default_tool_retries,
    get_image_magic_tool_config,
    get_local_llm_endpoint_presets,
    get_local_llm_tool_config,
    get_smtp_tool_config,
    normalize_coqui_tts_tool_config,
    normalize_image_magic_tool_config,
    normalize_local_llm_tool_config,
    normalize_smtp_tool_config,
    save_coqui_tts_tool_config,
    save_image_magic_tool_config,
    save_local_llm_tool_config,
    save_smtp_tool_config,
)

__all__ = [name for name in globals() if not name.startswith("_")]
