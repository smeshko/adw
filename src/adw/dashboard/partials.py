"""Dashboard partial routes.

HTML fragments returned for HTMX sub-requests.  These routes always
return a fragment — they never wrap in the full page layout.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from adw.dashboard.dependencies import (
    get_index_manager,
)

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
