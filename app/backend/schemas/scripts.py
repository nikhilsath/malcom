"""Script domain schemas for script CRUD payloads and validation contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScriptValidationIssue(BaseModel):
    message: str
    line: int | None = None
    column: int | None = None


class ScriptValidationResult(BaseModel):
    valid: bool
    issues: list[ScriptValidationIssue]


class ScriptSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    language: Literal["python", "javascript"]
    sample_input: str
    expected_output: str
    validation_status: Literal["valid", "invalid", "unknown"]
    validation_message: str | None = None
    last_validated_at: str | None = None
    created_at: str
    updated_at: str


class ScriptResponse(ScriptSummaryResponse):
    code: str


class ScriptValidationRequest(BaseModel):
    language: Literal["python", "javascript"]
    code: str = Field(min_length=1, max_length=200000)


class ScriptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    language: Literal["python", "javascript"]
    sample_input: str = Field(default="", max_length=20000)
    expected_output: str = Field(default="{}", max_length=10000)
    code: str = Field(min_length=1, max_length=200000)


class ScriptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    language: Literal["python", "javascript"] | None = None
    sample_input: str | None = Field(default=None, max_length=20000)
    expected_output: str | None = Field(default=None, max_length=10000)
    code: str | None = Field(default=None, min_length=1, max_length=200000)


class ScriptLanguageOptionResponse(BaseModel):
    value: Literal["python", "javascript"]
    label: str
    description: str | None = None


class ScriptsMetadataResponse(BaseModel):
    languages: list[ScriptLanguageOptionResponse]


__all__ = [
    "ScriptCreate",
    "ScriptLanguageOptionResponse",
    "ScriptResponse",
    "ScriptsMetadataResponse",
    "ScriptSummaryResponse",
    "ScriptUpdate",
    "ScriptValidationIssue",
    "ScriptValidationRequest",
    "ScriptValidationResult",
]
