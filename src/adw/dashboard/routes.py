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
    active_run_count = 0
    last_updated_dt = None
    try:
        active_runs = index_manager.get_recent_runs(status="running")  # type: ignore[union-attr]
        active_run_count = len(active_runs)

        recent = index_manager.get_recent_runs(limit=1)  # type: ignore[union-attr]
        if recent:
            last_updated_dt = recent[0].completed_at or recent[0].started_at
    except Exception:
        pass  # Graceful degradation — page renders with defaults

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
    from adw.dashboard.partials import (
        _load_active_run_details,
        build_cost_strip_context,
        build_recent_runs_context,
        build_stats_context,
    )

    templates = request.app.state.templates
    context = _build_page_context(
        request, "overview",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )

    project_name = project or None

    # Detect empty states
    all_projects = project_registry.get_all()  # type: ignore[union-attr]
    has_projects = len(all_projects) > 0
    context["has_projects"] = has_projects

    if has_projects:
        # Check for runs and load stats with error resilience
        context["data_error"] = False
        context["data_error_message"] = ""
        try:
            recent_check = index_manager.get_recent_runs(  # type: ignore[union-attr]
                limit=1, project_name=project_name,
            )
            has_runs = len(recent_check) > 0
        except Exception:
            has_runs = False
            context["data_error"] = True
            context["data_error_message"] = (
                "Unable to load run data. The index file may be corrupted or locked."
            )

        context["has_runs"] = has_runs

        if has_runs:
            try:
                stats = stats_aggregator.get_global_stats(project_name=project_name)  # type: ignore[union-attr]
                context.update(build_stats_context(stats, project_name))
                context.update(build_cost_strip_context(stats_aggregator, project_name))
            except Exception:
                context["data_error"] = True
                context["data_error_message"] = (
                    "Unable to load run data. The index file may be corrupted or locked."
                )
    else:
        context["has_runs"] = False

    # Add recent runs data for the recent runs partial
    entries = index_manager.get_recent_runs(limit=5, project_name=project_name)  # type: ignore[union-attr]
    context["recent_runs"] = build_recent_runs_context(entries)

    # Add project breakdown data — always unfiltered so all cards are visible
    all_stats = stats_aggregator.get_global_stats(project_name=None)  # type: ignore[union-attr]
    context["project_stats"] = all_stats.projects  # type: ignore[union-attr]

    # Add active runs data for the active runs section
    active_entries = index_manager.get_recent_runs(  # type: ignore[union-attr]
        status="running", project_name=project_name
    )
    context["active_runs"] = _load_active_run_details(active_entries)

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


_RANGE_DAYS: dict[str, int | None] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "all": None,
}

_VALID_RANGES = list(_RANGE_DAYS.keys())


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(
    request: Request,
    project: str = Query("", alias="project"),
    range_: str = Query("7d", alias="range"),
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the analytics page.

    Returns the full page or just the ``#analytics-content`` partial
    depending on whether the request came from HTMX.
    """
    from adw.dashboard.partials import build_analytics_context

    # Normalise range
    if range_ not in _RANGE_DAYS:
        range_ = "7d"

    templates = request.app.state.templates
    context = _build_page_context(
        request, "analytics",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )

    project_name = project or None

    # Build analytics-specific context
    try:
        context.update(
            build_analytics_context(
                stats_aggregator=stats_aggregator,
                project_name=project_name,
                range_key=range_,
                range_days=_RANGE_DAYS,
            )
        )
    except Exception:
        context["has_analytics_data"] = False

    context["selected_range"] = range_
    context["valid_ranges"] = _VALID_RANGES

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/analytics.html", context)
    return templates.TemplateResponse(request, "pages/analytics.html", context)


_RUN_NOT_FOUND_FRAGMENT = (
    '<div class="flex justify-center items-center min-h-[40vh]">'
    '<div class="card bg-base-100 shadow-sm p-8 text-center max-w-lg">'
    '<p class="text-base-content/70 mb-4">Run not found. It may have been deleted.</p>'
    '<a hx-get="/" hx-target="#main" hx-push-url="/" '
    'class="btn btn-ghost btn-sm">&larr; Back to Overview</a>'
    '</div></div>'
)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail(
    request: Request,
    run_id: str,
    index_manager: object = Depends(get_index_manager),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render run detail page, or a 404 message if not found."""
    templates = request.app.state.templates

    # Look up the run in the index
    all_runs = index_manager.get_recent_runs(limit=100000)  # type: ignore[union-attr]
    run_entry = None
    for entry in all_runs:
        if entry.run_id == run_id:
            run_entry = entry
            break

    if run_entry is None:
        if request.headers.get("HX-Request"):
            return HTMLResponse(content=_RUN_NOT_FOUND_FRAGMENT, status_code=404)
        # Full page: wrap in base template
        context = _build_page_context(
            request, "",
            index_manager=index_manager,
            project_registry=project_registry,
            project="",
        )
        context["run_not_found"] = True
        return templates.TemplateResponse(
            request, "pages/run_not_found.html", context, status_code=404,
        )

    # For now, redirect to runs list (run detail page is a later story)
    if request.headers.get("HX-Request"):
        return HTMLResponse(content=_RUN_NOT_FOUND_FRAGMENT, status_code=404)
    context = _build_page_context(
        request, "",
        index_manager=index_manager,
        project_registry=project_registry,
        project="",
    )
    context["run_not_found"] = True
    return templates.TemplateResponse(
        request, "pages/run_not_found.html", context, status_code=404,
    )


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "healthy", "service": "dashboard"}
