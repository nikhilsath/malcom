"""Docs domain schemas for article CRUD and listing payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocArticleSummaryResponse(BaseModel):
    id: str
    slug: str
    title: str
    summary: str
    tags: list[str]
    is_ai_created: bool
    created_at: str
    updated_at: str


class DocArticleResponse(DocArticleSummaryResponse):
    content: str


class DocArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=1000)
    content: str | None = Field(default=None, max_length=500000)
    tags: list[str] | None = None
    is_ai_created: bool | None = None


class DocArticleCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(default="", max_length=1000)
    content: str = Field(default="", max_length=500000)
    tags: list[str] = Field(default_factory=list)
    is_ai_created: bool = False


__all__ = [
    "DocArticleCreate",
    "DocArticleResponse",
    "DocArticleSummaryResponse",
    "DocArticleUpdate",
]
