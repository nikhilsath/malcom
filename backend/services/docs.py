"""Docs service: article CRUD helpers backed by the docs_articles / docs_tags tables."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from backend.services.utils import utc_now_iso


def _safe_resolve_in_docs(root_dir: Path, source_path: str) -> Path:
    """Resolve source_path and verify it stays within the docs/ subdirectory."""
    resolved = (root_dir / source_path).resolve()
    docs_dir = (root_dir / "docs").resolve()
    if not resolved.is_relative_to(docs_dir):
        raise ValueError(f"Resolved path escapes docs directory: {source_path}")
    return resolved


def _slug_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[^a-z0-9\-]", "-", stem.lower()).strip("-")


def _title_from_markdown(content: str, fallback: str) -> str:
    """Extract the first H1 heading from markdown content, or return fallback."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _get_article_tags(connection: Any, article_id: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT dt.tag
        FROM docs_tags dt
        JOIN docs_article_tags dat ON dat.tag_id = dt.id
        WHERE dat.article_id = ?
        ORDER BY dt.tag ASC
        """,
        (article_id,),
    ).fetchall()
    return [row["tag"] for row in rows]


def _ensure_tag(connection: Any, tag: str) -> str:
    """Return tag id, inserting the tag if it does not exist."""
    row = connection.execute(
        "SELECT id FROM docs_tags WHERE tag = ?",
        (tag,),
    ).fetchone()
    if row is not None:
        return row["id"]
    tag_id = f"tag_{uuid4().hex[:12]}"
    connection.execute(
        "INSERT INTO docs_tags (id, tag, kind, created_at) VALUES (?, ?, ?, ?)",
        (tag_id, tag, "freeform", utc_now_iso()),
    )
    return tag_id


def _set_article_tags(connection: Any, article_id: str, tags: list[str]) -> None:
    connection.execute("DELETE FROM docs_article_tags WHERE article_id = ?", (article_id,))
    for tag in tags:
        tag_id = _ensure_tag(connection, tag.strip())
        connection.execute(
            "INSERT INTO docs_article_tags (article_id, tag_id) VALUES (?, ?)",
            (article_id, tag_id),
        )


def row_to_article_summary(row: Mapping[str, Any], tags: list[str]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "summary": row["summary"] or "",
        "tags": tags,
        "is_ai_created": bool(row["is_ai_created"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def row_to_article_response(row: Mapping[str, Any], tags: list[str], content: str) -> dict[str, Any]:
    base = row_to_article_summary(row, tags)
    base["content"] = content
    return base


def list_docs_articles(connection: Any, query: str = "", tags: list[str] | None = None) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, slug, title, summary, is_ai_created, created_at, updated_at
        FROM docs_articles
        ORDER BY updated_at DESC, lower(title) ASC
        """,
    ).fetchall()
    results = []
    for row in rows:
        article_tags = _get_article_tags(connection, row["id"])
        if query:
            q = query.lower()
            title_match = q in row["title"].lower()
            tag_match = any(q in t.lower() for t in article_tags)
            summary_match = q in (row["summary"] or "").lower()
            if not (title_match or tag_match or summary_match):
                continue
        if tags:
            tag_set = {t.lower() for t in article_tags}
            if not all(t.lower() in tag_set for t in tags):
                continue
        results.append(row_to_article_summary(row, article_tags))
    return results


def get_docs_article(connection: Any, slug: str, root_dir: Path) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, slug, title, summary, source_path, is_ai_created, created_at, updated_at
        FROM docs_articles
        WHERE slug = ?
        """,
        (slug,),
    ).fetchone()
    if row is None:
        return None
    tags = _get_article_tags(connection, row["id"])
    content = ""
    if row["source_path"]:
        try:
            source_file = _safe_resolve_in_docs(root_dir, row["source_path"])
        except ValueError:
            source_file = None
        if source_file is not None and source_file.is_file():
            content = source_file.read_text(encoding="utf-8")
    return row_to_article_response(row, tags, content)


def update_docs_article(
    connection: Any,
    slug: str,
    root_dir: Path,
    title: str | None,
    summary: str | None,
    content: str | None,
    tags: list[str] | None,
    is_ai_created: bool | None,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, slug, title, summary, source_path, is_ai_created, created_at, updated_at
        FROM docs_articles
        WHERE slug = ?
        """,
        (slug,),
    ).fetchone()
    if row is None:
        return None

    next_title = title if title is not None else row["title"]
    next_summary = summary if summary is not None else (row["summary"] or "")
    next_is_ai_created = int(is_ai_created) if is_ai_created is not None else int(row["is_ai_created"])
    now = utc_now_iso()

    if content is not None and row["source_path"]:
        try:
            source_file = _safe_resolve_in_docs(root_dir, row["source_path"])
        except ValueError:
            source_file = None
        if source_file is not None:
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text(content, encoding="utf-8")

    connection.execute(
        """
        UPDATE docs_articles
        SET title = ?, summary = ?, is_ai_created = ?, updated_at = ?
        WHERE id = ?
        """,
        (next_title, next_summary, next_is_ai_created, now, row["id"]),
    )
    if tags is not None:
        _set_article_tags(connection, row["id"], tags)
    connection.commit()

    updated_row = connection.execute(
        """
        SELECT id, slug, title, summary, source_path, is_ai_created, created_at, updated_at
        FROM docs_articles
        WHERE id = ?
        """,
        (row["id"],),
    ).fetchone()
    updated_tags = _get_article_tags(connection, row["id"])
    if content is not None:
        saved_content = content
    elif row["source_path"]:
        try:
            fallback_file = _safe_resolve_in_docs(root_dir, row["source_path"])
            saved_content = fallback_file.read_text(encoding="utf-8") if fallback_file.is_file() else ""
        except ValueError:
            saved_content = ""
    else:
        saved_content = ""
    return row_to_article_response(updated_row, updated_tags, saved_content)


def create_docs_article(
    connection: Any,
    root_dir: Path,
    slug: str,
    title: str,
    summary: str,
    content: str,
    tags: list[str],
    is_ai_created: bool,
) -> dict[str, Any]:
    article_id = f"doc_{uuid4().hex[:12]}"
    now = utc_now_iso()
    source_path = f"docs/{slug}.md"
    source_file = _safe_resolve_in_docs(root_dir, source_path)
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(content, encoding="utf-8")

    connection.execute(
        """
        INSERT INTO docs_articles (id, slug, title, summary, source_path, is_ai_created, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (article_id, slug, title, summary, source_path, int(is_ai_created), now, now),
    )
    _set_article_tags(connection, article_id, tags)
    connection.commit()

    row = connection.execute(
        """
        SELECT id, slug, title, summary, source_path, is_ai_created, created_at, updated_at
        FROM docs_articles
        WHERE id = ?
        """,
        (article_id,),
    ).fetchone()
    saved_tags = _get_article_tags(connection, article_id)
    return row_to_article_response(row, saved_tags, content)


def sync_docs_from_repo(connection: Any, root_dir: Path) -> int:
    """Scan docs/ directory for *.md files and upsert metadata rows."""
    docs_dir = root_dir / "docs"
    if not docs_dir.is_dir():
        return 0
    synced = 0
    for md_file in sorted(docs_dir.glob("*.md")):
        slug = _slug_from_filename(md_file.name)
        if not slug:
            continue
        content = md_file.read_text(encoding="utf-8")
        title = _title_from_markdown(content, fallback=slug.replace("-", " ").title())
        source_path = str(md_file.relative_to(root_dir))
        now = utc_now_iso()
        existing = connection.execute(
            "SELECT id FROM docs_articles WHERE slug = ?", (slug,)
        ).fetchone()
        if existing is None:
            article_id = f"doc_{uuid4().hex[:12]}"
            connection.execute(
                """
                INSERT INTO docs_articles (id, slug, title, summary, source_path, is_ai_created, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (article_id, slug, title, "", source_path, now, now),
            )
        else:
            connection.execute(
                """
                UPDATE docs_articles
                SET title = ?, source_path = ?, updated_at = ?
                WHERE slug = ?
                """,
                (title, source_path, now, slug),
            )
        synced += 1
    connection.commit()
    return synced
