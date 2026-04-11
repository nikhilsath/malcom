"""Coqui TTS runtime discovery and validation helpers."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from backend.schemas import CoquiTtsOptionResponse, CoquiTtsToolRuntimeResponse

from .tool_command_utils import verify_local_command_ready

MODEL_NAME_PATTERN = re.compile(r"tts_models/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
OPTION_LINE_PATTERN = re.compile(r"^\s*(?:[-*]\s*)?([A-Za-z0-9_.-]+)\s*(?::.*)?$")
QUOTED_OPTION_PATTERN = re.compile(r"['\"]([^'\"]+)['\"]")


def _build_option(value: str) -> CoquiTtsOptionResponse:
    return CoquiTtsOptionResponse(value=value, label=value)


def _run_coqui_probe(command_parts: list[str], args: list[str], *, root_dir: Path) -> str:
    completed = subprocess.run(
        [*command_parts, *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root_dir),
    )
    return "\n".join(part for part in ((completed.stdout or "").strip(), (completed.stderr or "").strip()) if part).strip()


def _parse_coqui_model_options(output: str) -> list[CoquiTtsOptionResponse]:
    values: list[str] = []
    for value in MODEL_NAME_PATTERN.findall(output):
        if value not in values:
            values.append(value)
    return [_build_option(value) for value in values]


def _parse_simple_option_list(output: str) -> list[CoquiTtsOptionResponse]:
    values: list[str] = []
    for line in output.splitlines():
        quoted_values = [match.strip() for match in QUOTED_OPTION_PATTERN.findall(line)]
        if quoted_values:
            for candidate in quoted_values:
                if candidate and candidate.lower() not in {"speaker", "speakers", "language", "languages"} and candidate not in values:
                    values.append(candidate)
            continue

        line_match = OPTION_LINE_PATTERN.match(line)
        candidate = line_match.group(1).strip() if line_match else ""
        if candidate and candidate.lower() not in {"speaker", "speakers", "language", "languages"} and candidate not in values:
            values.append(candidate)
    return [_build_option(value) for value in values]


def _discover_model_options(command_parts: list[str], *, root_dir: Path) -> list[CoquiTtsOptionResponse]:
    try:
        output = _run_coqui_probe(command_parts, ["--list_models"], root_dir=root_dir)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return _parse_coqui_model_options(output)


def _discover_model_scoped_options(
    command_parts: list[str],
    *,
    model_name: str,
    probe_flag: str,
    root_dir: Path,
) -> list[CoquiTtsOptionResponse]:
    if not model_name:
        return []
    try:
        output = _run_coqui_probe(
            command_parts,
            ["--model_name", model_name, probe_flag],
            root_dir=root_dir,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return _parse_simple_option_list(output)


def discover_coqui_tts_runtime(*, command: str, selected_model_name: str, root_dir: Path) -> CoquiTtsToolRuntimeResponse:
    try:
        command_parts = verify_local_command_ready(command, working_dir=root_dir, tool_name="Coqui TTS")
    except RuntimeError as error:
        return CoquiTtsToolRuntimeResponse(
            ready=False,
            command_available=False,
            message=str(error),
            command_options=[],
            model_options=[],
            speaker_options=[],
            language_options=[],
        )

    command_options = [_build_option(command)]
    model_options = _discover_model_options(command_parts, root_dir=root_dir)
    selected_model = selected_model_name.strip()
    if not selected_model and model_options:
        selected_model = model_options[0].value

    speaker_options = _discover_model_scoped_options(
        command_parts,
        model_name=selected_model,
        probe_flag="--list_speaker_idxs",
        root_dir=root_dir,
    )
    language_options = _discover_model_scoped_options(
        command_parts,
        model_name=selected_model,
        probe_flag="--list_language_idxs",
        root_dir=root_dir,
    )

    if not model_options:
        return CoquiTtsToolRuntimeResponse(
            ready=False,
            command_available=True,
            message="Coqui TTS is installed, but no models were discovered for the configured runtime.",
            command_options=command_options,
            model_options=[],
            speaker_options=[],
            language_options=[],
        )

    return CoquiTtsToolRuntimeResponse(
        ready=True,
        command_available=True,
        message="Coqui TTS runtime is available for workflow steps.",
        command_options=command_options,
        model_options=model_options,
        speaker_options=speaker_options,
        language_options=language_options,
    )


def validate_coqui_tts_selection(*, runtime: CoquiTtsToolRuntimeResponse, model_name: str, speaker: str, language: str) -> None:
    if not runtime.command_available:
        raise RuntimeError(runtime.message)
    if not runtime.model_options:
        raise RuntimeError(runtime.message)

    available_model_names = {option.value for option in runtime.model_options}
    if model_name not in available_model_names:
        raise RuntimeError("Selected Coqui TTS model is not available in the detected runtime.")

    available_speakers = {option.value for option in runtime.speaker_options}
    if speaker and speaker not in available_speakers:
        raise RuntimeError("Selected Coqui speaker is not available for the chosen model.")

    available_languages = {option.value for option in runtime.language_options}
    if language and language not in available_languages:
        raise RuntimeError("Selected Coqui language is not available for the chosen model.")
