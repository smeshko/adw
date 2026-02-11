"""Dashboard page routes.

Full HTML pages served when the browser navigates directly to a URL
(i.e., without ``HX-Request`` header). HTMX partial responses are
handled in ``partials.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
    get_stats_aggregator,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def overview(
    request: Request,
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the overview / home page.

    Returns the full page or just the ``#main`` partial depending on
    whether the request came from HTMX.
    """
    csrf_token = generate_csrf_token(request)
    templates = request.app.state.templates

    context = {
        "request": request,
        "csrf_token": csrf_token,
        "page": "overview",
    }

    # HTMX partial vs full page
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/overview.html", context)
    return templates.TemplateResponse(request, "pages/overview.html", context)


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "healthy", "service": "dashboard"}
