"""Dashboard page routes.

Full HTML pages served when the browser navigates directly to a URL
(i.e., without ``HX-Request`` header). HTMX partial responses are
handled in ``partials.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
    get_stats_aggregator,
)

router = APIRouter()


def _relative_time(dt: datetime | None) -> str:
    """Return a human-readable relative time string like '5s ago'."""
    if dt is None:
        return "—"
    now = datetime.now(UTC)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _build_page_context(
    request: Request,
    page: str,
    *,
    index_manager: object,
    project_registry: object,
    project: str,
) -> dict:
    """Build the shared template context used by all page routes."""
    csrf_token = generate_csrf_token(request)

    # Project list for filter dropdown
    all_projects = project_registry.get_all()  # type: ignore[union-attr]
    project_names = [p.name for p in all_projects]

    # Status bar data (for full-page renders that include the footer)
    active_runs = index_manager.get_recent_runs(status="running")  # type: ignore[union-attr]
    active_run_count = len(active_runs)

    recent = index_manager.get_recent_runs(limit=1)  # type: ignore[union-attr]
    last_updated_dt = None
    if recent:
        last_updated_dt = recent[0].completed_at or recent[0].started_at

    return {
        "request": request,
        "csrf_token": csrf_token,
        "page": page,
        "projects": project_names,
        "selected_project": project or None,
        "active_run_count": active_run_count,
        "last_updated_ago": _relative_time(last_updated_dt),
    }


@router.get("/", response_class=HTMLResponse)
async def overview(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the overview / home page.

    Returns the full page or just the ``#main`` partial depending on
    whether the request came from HTMX.
    """
    templates = request.app.state.templates
    context = _build_page_context(
        request, "overview",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/overview.html", context)
    return templates.TemplateResponse(request, "pages/overview.html", context)


@router.get("/runs", response_class=HTMLResponse)
async def runs_list(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the runs list page.

    Returns the full page or just the ``#main`` partial depending on
    whether the request came from HTMX.
    """
    templates = request.app.state.templates
    context = _build_page_context(
        request, "runs",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/runs_list.html", context)
    return templates.TemplateResponse(request, "pages/runs_list.html", context)


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the analytics page.

    Returns the full page or just the ``#main`` partial depending on
    whether the request came from HTMX.
    """
    templates = request.app.state.templates
    context = _build_page_context(
        request, "analytics",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/analytics.html", context)
    return templates.TemplateResponse(request, "pages/analytics.html", context)


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "healthy", "service": "dashboard"}
