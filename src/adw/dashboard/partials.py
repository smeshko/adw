"""Dashboard partial routes.

HTML fragments returned for HTMX sub-requests.  These routes always
return a fragment — they never wrap in the full page layout.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.dashboard.dependencies import (
    get_index_manager,
    get_stats_aggregator,
)
from adw.exceptions import StateError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/partials")


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


@router.get("/status-bar", response_class=HTMLResponse)
async def status_bar(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return the status bar HTML fragment for polling updates."""
    templates = request.app.state.templates

    # Get active run count
    active_runs = index_manager.get_recent_runs(status="running")  # type: ignore[union-attr]
    active_run_count = len(active_runs)

    # Get last updated timestamp from most recent run
    recent = index_manager.get_recent_runs(limit=1)  # type: ignore[union-attr]
    last_updated_dt = None
    if recent:
        last_updated_dt = recent[0].completed_at or recent[0].started_at

    # Derive current page path from HX-Current-URL header (set by HTMX on
    # every request) so the refresh button targets the correct page.
    hx_current_url = request.headers.get("HX-Current-URL", "")
    current_path = urlparse(hx_current_url).path if hx_current_url else "/"

    context = {
        "request": request,
        "last_updated_ago": _relative_time(last_updated_dt),
        "active_run_count": active_run_count,
        "selected_project": project or None,
        "current_path": current_path or "/",
    }

    return templates.TemplateResponse(request, "partials/status_bar.html", context)


def _format_duration(ms: int) -> str:
    """Format milliseconds as 'Xm Ys'."""
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}m {seconds}s"


def _format_tokens(total: int) -> str:
    """Format token count with abbreviation (2.4M, 340K)."""
    if total >= 1_000_000:
        value = total / 1_000_000
        return f"{value:.1f}M" if value != int(value) else f"{int(value)}M"
    if total >= 1_000:
        value = total / 1_000
        return f"{value:.0f}K" if value >= 10 else f"{value:.1f}K"
    return str(total)


def build_stats_context(stats: object, selected_project: str | None) -> dict:
    """Build template context dict for the stats row partial.

    Args:
        stats: A GlobalStatistics instance from StatsAggregator.
        selected_project: Current project filter value or None.

    Returns:
        Dict of pre-formatted values ready for the stats_row.html template.
    """
    runs_trend = stats.runs_this_week - stats.previous_week_total_runs  # type: ignore[union-attr]
    success_trend = round(
        (stats.success_rate - stats.previous_week_success_rate) * 100, 1  # type: ignore[union-attr]
    )
    duration_trend_ms = (
        stats.average_duration_ms - stats.previous_week_average_duration_ms  # type: ignore[union-attr]
    )
    abs_duration_trend_ms = abs(duration_trend_ms)
    duration_trend_display = _format_duration(abs_duration_trend_ms)

    return {
        "selected_project": selected_project,
        # Stat values
        "total_runs": stats.total_runs,  # type: ignore[union-attr]
        "success_rate_display": f"{stats.success_rate * 100:.1f}%",  # type: ignore[union-attr]
        "duration_display": _format_duration(stats.average_duration_ms),  # type: ignore[union-attr]
        "tokens_display": _format_tokens(stats.tokens.total_tokens),  # type: ignore[union-attr]
        "cost_display": f"{stats.estimated_cost:.2f}",  # type: ignore[union-attr]
        # Trend data
        "runs_trend": runs_trend,
        "success_trend": success_trend,
        "success_trend_display": f"{abs(success_trend):.1f}",
        "duration_trend_ms": duration_trend_ms,
        "duration_trend_display": duration_trend_display,
        # This week totals
        "tokens_week_display": _format_tokens(stats.tokens_this_week.total_tokens),  # type: ignore[union-attr]
        "cost_week_display": f"{stats.cost_this_week:.2f}",  # type: ignore[union-attr]
    }


_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def build_cost_strip_context(
    stats_aggregator: object,
    project_name: str | None,
) -> dict:
    """Build template context for the cost summary strip.

    Args:
        stats_aggregator: A StatsAggregator instance.
        project_name: Current project filter value or None.

    Returns:
        Dict with cost_week_display, tokens_week_display, and daily_bars.
    """
    stats = stats_aggregator.get_global_stats(project_name=project_name)  # type: ignore[union-attr]
    daily_counts = stats_aggregator.get_daily_token_counts(project_name=project_name)  # type: ignore[union-attr]

    # Compute bar heights as percentages
    max_tokens = max((d["tokens"] for d in daily_counts), default=0)
    daily_bars = []
    for d in daily_counts:
        tokens: int = d["tokens"]  # type: ignore[assignment]
        height_pct = int((tokens / max_tokens) * 100) if max_tokens > 0 else 0
        day_label = _DAY_LABELS[d["date"].weekday()]  # type: ignore[union-attr]
        daily_bars.append({
            "date_label": day_label,
            "height_pct": height_pct,
            "tokens": tokens,
        })

    return {
        "cost_strip_cost_display": f"${stats.cost_this_week:.2f}",  # type: ignore[union-attr]
        "cost_strip_tokens_display": _format_tokens(stats.tokens_this_week.total_tokens),  # type: ignore[union-attr]
        "daily_bars": daily_bars,
    }


@router.get("/stats", response_class=HTMLResponse)
async def stats_partial(
    request: Request,
    project: str = Query("", alias="project"),
    stats_aggregator: object = Depends(get_stats_aggregator),
) -> HTMLResponse:
    """Return the stats row HTML fragment for polling updates."""
    templates = request.app.state.templates

    project_name = project or None
    stats = stats_aggregator.get_global_stats(project_name=project_name)  # type: ignore[union-attr]

    context = build_stats_context(stats, project_name)
    context["request"] = request

    return templates.TemplateResponse(request, "partials/stats_row.html", context)


def build_recent_runs_context(entries: list) -> list[dict]:
    """Transform IndexEntry objects into template-ready dicts.

    Args:
        entries: List of IndexEntry objects from IndexManager.

    Returns:
        List of dicts with run_id, project_name, feature_description,
        status, duration_display, and started_ago keys.
    """
    result = []
    for entry in entries:
        if entry.completed_at and entry.started_at:
            delta_seconds = (entry.completed_at - entry.started_at).total_seconds()
            duration_display = _format_duration(int(delta_seconds * 1000))
        else:
            duration_display = "—"

        result.append({
            "run_id": entry.run_id,
            "project_name": entry.project_name,
            "feature_description": entry.feature_description,
            "status": entry.status,
            "duration_display": duration_display,
            "started_ago": _relative_time(entry.started_at),
        })
    return result


@router.get("/recent-runs", response_class=HTMLResponse)
async def recent_runs(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return the recent runs table HTML fragment for polling updates."""
    templates = request.app.state.templates

    project_name = project or None
    entries = index_manager.get_recent_runs(limit=5, project_name=project_name)  # type: ignore[union-attr]

    context = {
        "request": request,
        "recent_runs": build_recent_runs_context(entries),
        "selected_project": project_name,
    }

    return templates.TemplateResponse(request, "partials/recent_runs.html", context)


@router.get("/projects", response_class=HTMLResponse)
async def project_breakdown(
    request: Request,
    project: str = Query("", alias="project"),
    stats_aggregator: object = Depends(get_stats_aggregator),
) -> HTMLResponse:
    """Return the project breakdown cards HTML fragment."""
    templates = request.app.state.templates

    project_name = project or None
    # Always fetch unfiltered stats so all project cards remain visible,
    # allowing the user to switch projects by clicking any card.
    stats = stats_aggregator.get_global_stats(project_name=None)  # type: ignore[union-attr]

    context = {
        "request": request,
        "project_stats": stats.projects,  # type: ignore[union-attr]
        "selected_project": project_name,
    }

    return templates.TemplateResponse(
        request, "partials/project_breakdown.html", context
    )


# ── Active Runs ─────────────────────────────────────────────────────

# Display labels for each phase in the pipeline
_PHASE_LABELS: dict[str, str] = {
    "plan": "Plan",
    "build": "Build",
    "validate": "Valid",
    "document": "Doc",
    "ship": "Ship",
}


def _format_elapsed(delta: timedelta) -> str:
    """Format a timedelta as 'Xm Ys'."""
    total_seconds = int(delta.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}m {seconds}s"


def _build_phase_pipeline(
    *,
    phases_completed: list[str],
    current_phase: str | None,
) -> list[dict[str, str]]:
    """Build phase pipeline data for template rendering.

    Args:
        phases_completed: List of phase names that completed successfully.
        current_phase: The currently active phase name.

    Returns:
        List of dicts with 'name' (display label) and 'status'
        ('completed', 'active', or 'pending') for each phase.
    """
    completed_set = set(phases_completed)
    pipeline: list[dict[str, str]] = []
    for phase in PHASE_SEQUENCE:
        if phase in completed_set:
            status = "completed"
        elif phase == current_phase:
            status = "active"
        else:
            status = "pending"
        pipeline.append({
            "name": _PHASE_LABELS.get(phase, phase.capitalize()),
            "status": status,
        })
    return pipeline


def _load_active_run_details(
    entries: list[object],
) -> list[dict]:
    """Load active run details from IndexEntry objects.

    For each running IndexEntry, attempts to load the RunContext from
    disk to get the live current_phase. Falls back to IndexEntry data
    if the RunContext cannot be loaded.

    Args:
        entries: List of IndexEntry objects with status="running".

    Returns:
        List of dicts with run display data for the template.
    """
    now = datetime.now(UTC)
    runs: list[dict] = []

    for entry in entries:
        current_phase = entry.phase_reached  # type: ignore[union-attr]
        phases_completed = list(entry.phases_completed)  # type: ignore[union-attr]

        # Try loading RunContext for live phase data
        try:
            project_path = Path(entry.project_path)  # type: ignore[union-attr]
            runs_dir = project_path / ".adw" / "runs"
            cm = ContextManager(runs_dir)
            ctx = cm.load(entry.run_id)  # type: ignore[union-attr]
            current_phase = ctx.current_phase
            phases_completed = list(ctx.phase_history)
        except (StateError, OSError):
            logger.debug(
                "RunContext unavailable, using IndexEntry fallback",
                extra={"run_id": entry.run_id},  # type: ignore[union-attr]
            )

        elapsed = now - entry.started_at  # type: ignore[union-attr]

        runs.append({
            "run_id": entry.run_id,  # type: ignore[union-attr]
            "project_name": entry.project_name,  # type: ignore[union-attr]
            "feature_description": entry.feature_description,  # type: ignore[union-attr]
            "elapsed": _format_elapsed(elapsed),
            "phases": _build_phase_pipeline(
                phases_completed=phases_completed,
                current_phase=current_phase,
            ),
            "started_at": entry.started_at,  # type: ignore[union-attr]
        })

    return runs


@router.get("/active-runs", response_class=HTMLResponse)
async def active_runs_partial(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return the active runs section HTML fragment for polling updates."""
    templates = request.app.state.templates

    project_name = project or None
    entries = index_manager.get_recent_runs(  # type: ignore[union-attr]
        status="running", project_name=project_name
    )

    active_runs = _load_active_run_details(entries)

    context = {
        "request": request,
        "active_runs": active_runs,
        "selected_project": project_name,
    }

    return templates.TemplateResponse(
        request, "partials/active_runs.html", context
    )
