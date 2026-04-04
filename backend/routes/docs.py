from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *
from backend.services.docs import (
    create_docs_article,
    get_docs_article,
    list_docs_articles,
    update_docs_article,
)

router = APIRouter()


@router.get("/api/v1/docs", response_model=list[DocArticleSummaryResponse])
def list_docs(
    request: Request,
    q: str = "",
    tags: str = "",
) -> list[DocArticleSummaryResponse]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    rows = list_docs_articles(get_connection(request), query=q, tags=tag_list)
    return [DocArticleSummaryResponse(**row) for row in rows]


@router.get("/api/v1/docs/{slug}", response_model=DocArticleResponse)
def get_doc(slug: str, request: Request) -> DocArticleResponse:
    article = get_docs_article(get_connection(request), slug, get_root_dir(request))
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
    return DocArticleResponse(**article)


@router.put("/api/v1/docs/{slug}", response_model=DocArticleResponse)
def update_doc(slug: str, payload: DocArticleUpdate, request: Request) -> DocArticleResponse:
    article = update_docs_article(
        get_connection(request),
        slug,
        get_root_dir(request),
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        tags=payload.tags,
        is_ai_created=payload.is_ai_created,
    )
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
    return DocArticleResponse(**article)


@router.post("/api/v1/docs", response_model=DocArticleResponse, status_code=status.HTTP_201_CREATED)
def create_doc(payload: DocArticleCreate, request: Request) -> DocArticleResponse:
    article = create_docs_article(
        get_connection(request),
        get_root_dir(request),
        slug=payload.slug,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        tags=payload.tags,
        is_ai_created=payload.is_ai_created,
    )
    return DocArticleResponse(**article)
