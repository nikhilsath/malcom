from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse

from backend.page_registry import get_redirect_ui_routes, get_served_ui_pages
from backend.services.support import ensure_built_ui, get_built_ui_file, get_root_dir

router = APIRouter(include_in_schema=False)


def get_ui_html_response(relative_path: str, request: Request) -> FileResponse:
    root_dir = get_root_dir(request)
    ensure_built_ui(root_dir)
    html_path = get_built_ui_file(root_dir, relative_path)
    if not html_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UI page not found.")
    return FileResponse(html_path)


def build_ui_route(relative_path: str):
    def serve_ui_route(request: Request) -> FileResponse:
        return get_ui_html_response(relative_path, request)

    return serve_ui_route


def build_redirect_route(redirect_target: str):
    def redirect_ui_route() -> RedirectResponse:
        return RedirectResponse(url=redirect_target)

    return redirect_ui_route


@router.get("/favicon.ico")
def serve_favicon(request: Request) -> FileResponse:
    root_dir = get_root_dir(request)
    favicon_path = root_dir / "data" / "media" / "favicon.ico"
    if not favicon_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favicon not found.")
    return FileResponse(favicon_path)


def register_ui_routes(app: FastAPI) -> None:
    for entry in get_served_ui_pages():
        app.add_api_route(
            entry.route_path,
            build_ui_route(entry.source_html_path),
            methods=["GET"],
            include_in_schema=False,
        )

    for route_path, redirect_target in get_redirect_ui_routes():
        app.add_api_route(
            route_path,
            build_redirect_route(redirect_target),
            methods=["GET"],
            include_in_schema=False,
        )
