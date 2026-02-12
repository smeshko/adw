"""Dashboard page routes.

Full HTML pages served when the browser navigates directly to a URL
(i.e., without ``HX-Request`` header). HTMX partial responses are
handled in ``partials.py``.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from adw.core.artifact_manager import ArtifactManager
from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
    get_stats_aggregator,
    resolve_project_filter,
)
from adw.exceptions import StateError

logger = logging.getLogger(__name__)

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
        project_path_str, _ = resolve_project_filter(project_registry, project)
        active_runs = index_manager.get_recent_runs(  # type: ignore[union-attr]
            status="running",
            **({"project_path": Path(project_path_str)} if project_path_str else {}),
        )
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
    project_path_str, _ = resolve_project_filter(project_registry, project_name)

    # Build path→name map for display name resolution
    all_projects = project_registry.get_all()  # type: ignore[union-attr]
    name_map = {str(p.path): p.name for p in all_projects}
    has_projects = len(all_projects) > 0
    context["has_projects"] = has_projects

    if has_projects:
        # Check for runs and load stats with error resilience
        context["data_error"] = False
        context["data_error_message"] = ""
        try:
            recent_check = index_manager.get_recent_runs(  # type: ignore[union-attr]
                limit=1,
                project_path=Path(project_path_str) if project_path_str else None,
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

    # Add recent runs, project breakdown, and active runs data
    # Skip if data layer is already in error state
    if not context.get("data_error"):
        try:
            entries = index_manager.get_recent_runs(  # type: ignore[union-attr]
                limit=5,
                project_path=Path(project_path_str) if project_path_str else None,
            )
            context["recent_runs"] = build_recent_runs_context(entries, name_map)

            all_stats = stats_aggregator.get_global_stats(project_name=None)  # type: ignore[union-attr]
            context["project_stats"] = all_stats.projects  # type: ignore[union-attr]

            active_entries = index_manager.get_recent_runs(  # type: ignore[union-attr]
                status="running",
                project_path=Path(project_path_str) if project_path_str else None,
            )
            context["active_runs"] = _load_active_run_details(active_entries, name_map)
        except Exception:
            context["data_error"] = True
            context["data_error_message"] = (
                "Unable to load run data. The index file may be corrupted or locked."
            )
            context.setdefault("recent_runs", [])
            context.setdefault("project_stats", [])
            context.setdefault("active_runs", [])
    else:
        context.setdefault("recent_runs", [])
        context.setdefault("project_stats", [])
        context.setdefault("active_runs", [])

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/overview.html", context)
    return templates.TemplateResponse(request, "pages/overview.html", context)


@router.get("/runs", response_class=HTMLResponse)
async def runs_list(
    request: Request,
    project: str = Query("", alias="project"),
    status_filter: str = Query("", alias="status"),
    from_date: str = Query("", alias="from"),
    to_date: str = Query("", alias="to"),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the runs list page.

    Returns the full page or just the ``#main`` partial depending on
    whether the request came from HTMX.  When the HX-Request header
    targets ``#runs-content`` (sort/pagination change), only the table
    partial is returned.
    """
    from adw.dashboard.partials import build_recent_runs_context

    templates = request.app.state.templates
    context = _build_page_context(
        request, "runs",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )

    # Parse date filters
    since = None
    until = None
    if from_date:
        try:
            since = datetime.fromisoformat(from_date)
            if since.tzinfo is None:
                since = since.replace(tzinfo=UTC)
        except ValueError:
            since = None
    if to_date:
        try:
            until = datetime.fromisoformat(to_date)
            if until.tzinfo is None:
                until = until.replace(tzinfo=UTC)
            # If date-only input (no 'T' separator), expand to end of day
            if "T" not in to_date:
                until = until.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            until = None

    # Resolve project filter
    project_path_str, _ = resolve_project_filter(project_registry, project or None)

    # Fetch paginated runs with graceful degradation
    try:
        paginated = index_manager.get_paginated_runs(  # type: ignore[union-attr]
            page=page,
            page_size=15,
            status=status_filter or None,
            project_path=Path(project_path_str) if project_path_str else None,
            since=since,
            until=until,
            sort=sort,
        )
    except Exception:
        paginated = {
            "entries": [],
            "total_count": 0,
            "page": 1,
            "page_size": 15,
            "total_pages": 0,
        }

    # Build path→name map for display name resolution
    all_proj = project_registry.get_all()  # type: ignore[union-attr]
    name_map = {str(p.path): p.name for p in all_proj}
    context["runs"] = build_recent_runs_context(paginated["entries"], name_map)
    context["total_count"] = paginated["total_count"]
    context["current_page"] = paginated["page"]
    context["total_pages"] = paginated["total_pages"]
    context["sort"] = sort
    context["status_filter"] = status_filter
    context["project_filter"] = project or ""
    context["from_date"] = from_date
    context["to_date"] = to_date

    # Determine response template based on request type
    hx_target = request.headers.get("HX-Target", "")
    if request.headers.get("HX-Request"):
        if hx_target == "runs-content":
            return templates.TemplateResponse(
                request, "partials/runs_table.html", context,
            )
        return templates.TemplateResponse(request, "partials/runs_list.html", context)
    return templates.TemplateResponse(request, "pages/runs_list.html", context)


_RANGE_DAYS: dict[str, int | None] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "all": None,
}

_VALID_RANGES = list(_RANGE_DAYS.keys())

_VALID_SORTS = {
    "cost_desc", "cost_asc", "tokens_desc", "tokens_asc",
    "runs_desc", "runs_asc", "project_desc", "project_asc",
    "avg_desc", "avg_asc",
}


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(
    request: Request,
    project: str = Query("", alias="project"),
    range_: str = Query("7d", alias="range"),
    sort: str = Query("cost_desc"),
    index_manager: object = Depends(get_index_manager),
    stats_aggregator: object = Depends(get_stats_aggregator),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render the analytics page.

    Returns the full page or just the ``#analytics-content`` partial
    depending on whether the request came from HTMX.
    """
    from adw.dashboard.partials import build_analytics_context

    # Normalise range and sort
    if range_ not in _RANGE_DAYS:
        range_ = "7d"
    if sort not in _VALID_SORTS:
        sort = "cost_desc"

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
                sort=sort,
            )
        )
    except Exception:
        context["has_analytics_data"] = False

    context["selected_range"] = range_
    context["valid_ranges"] = _VALID_RANGES
    context["breakdown_sort"] = context.get("breakdown_sort", sort)

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


# Display labels for each phase in the pipeline
_PHASE_LABELS: dict[str, str] = {
    "plan": "Plan",
    "build": "Build",
    "validate": "Valid",
    "document": "Doc",
    "ship": "Ship",
}


def _build_detail_phase_pipeline(
    *,
    phases_completed: list[str],
    current_phase: str | None,
    status: str,
    phase_durations: dict[str, int] | None = None,
) -> list[dict[str, str]]:
    """Build phase pipeline data for the run detail page.

    Includes duration information for each phase when available.

    Args:
        phases_completed: List of phase names that completed successfully.
        current_phase: The currently active phase name.
        status: The run status (used to determine failed phase).
        phase_durations: Optional mapping of phase name to duration in ms.

    Returns:
        List of dicts with 'name', 'status', and 'duration' for each phase.
    """
    completed_set = set(phases_completed)
    durations = phase_durations or {}
    pipeline: list[dict[str, str]] = []

    for phase in PHASE_SEQUENCE:
        if phase in completed_set:
            phase_status = "completed"
        elif phase == current_phase:
            if status == "running":
                phase_status = "active"
            elif status in ("failed", "aborted"):
                phase_status = "failed"
            else:
                # completed/interrupted: treat current phase as completed
                phase_status = "completed"
        else:
            phase_status = "pending"

        duration_ms = durations.get(phase)
        if duration_ms is not None:
            total_seconds = duration_ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration_display = f"{minutes}m {seconds}s"
        else:
            duration_display = ""

        pipeline.append({
            "name": _PHASE_LABELS.get(phase, phase.capitalize()),
            "status": phase_status,
            "duration": duration_display,
        })
    return pipeline


def _format_duration_from_seconds(total_seconds: int) -> str:
    """Format seconds as 'Xs', 'Xm Ys', or 'Xh Ym'."""
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"


def _build_run_detail_context(
    run_entry: object,
    request: Request,
    name_map: dict[str, str] | None = None,
) -> dict:
    """Build the template context for the run detail page.

    Attempts to load RunContext from disk for enriched data.
    Falls back to IndexEntry data if RunContext is unavailable.

    Args:
        run_entry: An IndexEntry from the global index.
        request: The current FastAPI request.
        name_map: Optional mapping of project_path -> display_name.

    Returns:
        Dict with all template variables for run_detail.html.
    """
    from adw.dashboard.partials import _format_tokens

    run_id = run_entry.run_id  # type: ignore[union-attr]
    project_name = run_entry.project_name  # type: ignore[union-attr]
    if name_map:
        project_name = name_map.get(
            run_entry.project_path, project_name,  # type: ignore[union-attr]
        )
    feature = run_entry.feature_description  # type: ignore[union-attr]
    status = run_entry.status  # type: ignore[union-attr]
    started_at = run_entry.started_at  # type: ignore[union-attr]
    completed_at = run_entry.completed_at  # type: ignore[union-attr]
    phases_completed = list(run_entry.phases_completed)  # type: ignore[union-attr]
    current_phase = run_entry.phase_reached  # type: ignore[union-attr]

    # Enriched data from RunContext (populated below if available)
    branch_name: str | None = None
    total_tokens: int = 0
    estimated_cost: float = 0.0
    pr_url: str | None = None
    task_id: str | None = None
    task_manager: str | None = None
    artifacts_path: str | None = None
    phase_tokens: dict[str, int] = {}

    # Try loading RunContext for enriched data
    try:
        project_path = Path(run_entry.project_path)  # type: ignore[union-attr]
        runs_dir = project_path / ".adw" / "runs"
        cm = ContextManager(runs_dir)
        ctx = cm.load(run_id)
        # Override with live data
        current_phase = ctx.current_phase
        phases_completed = list(ctx.phase_history)
        branch_name = ctx.branch_name
        total_tokens = ctx.total_tokens
        pr_url = ctx.pr_url
        task_id = ctx.task_id
        task_manager = ctx.task_manager
        phase_tokens = dict(ctx.phase_tokens)

        # Estimate cost at $3/$15 per 1M input/output tokens (approximate)
        estimated_cost = total_tokens * 0.000009  # rough average

        # Artifacts path
        if ctx.worktree_path:
            artifacts_path = str(ctx.worktree_path / ".adw" / "runs" / run_id / "artifacts")
        else:
            artifacts_path = str(runs_dir / run_id / "artifacts")
    except (StateError, OSError):
        logger.debug(
            "RunContext unavailable for detail page, using IndexEntry fallback",
            extra={"run_id": run_id},
        )

    # Duration
    if completed_at and started_at:
        delta_seconds = max(0, int((completed_at - started_at).total_seconds()))
        duration_display = _format_duration_from_seconds(delta_seconds)
    elif started_at:
        elapsed = int((datetime.now(UTC) - started_at).total_seconds())
        duration_display = _format_duration_from_seconds(elapsed)
    else:
        duration_display = "—"

    # Truncated run ID (first 8 chars)
    run_id_short = run_id[:8] + "…"

    # Back link: determine from Referer or ?from= param
    from_param = request.query_params.get("from", "")
    referer = request.headers.get("referer", "")

    if from_param == "runs":
        back_label = "Back to Runs"
        back_url = "/runs"
    elif "/runs" in referer and f"/runs/{run_id}" not in referer:
        back_label = "Back to Runs"
        back_url = "/runs"
    else:
        back_label = "Back to Overview"
        back_url = "/"

    # Build phase pipeline (phase durations not yet tracked in RunContext)
    phases = _build_detail_phase_pipeline(
        phases_completed=phases_completed,
        current_phase=current_phase,
        status=status,
    )

    # Build per-phase detail data for accordion section
    completed_set = set(phases_completed)
    all_phases_with_data = list(completed_set)
    if current_phase and current_phase not in completed_set:
        all_phases_with_data.append(current_phase)

    phases_detail: list[dict] = []
    for phase_key in PHASE_SEQUENCE:
        if phase_key not in all_phases_with_data:
            continue
        tokens = phase_tokens.get(phase_key, 0)
        cost = tokens * 0.000009
        phase_status = "completed" if phase_key in completed_set else (
            "active" if phase_key == current_phase and status == "running"
            else "failed" if phase_key == current_phase and status in ("failed", "aborted")
            else "completed"
        )
        # Status icon
        if phase_status == "completed":
            status_icon = "✓"
        elif phase_status == "active":
            status_icon = "●"
        elif phase_status == "failed":
            status_icon = "✗"
        else:
            status_icon = "—"

        phases_detail.append({
            "phase_key": phase_key,
            "name": _PHASE_LABELS.get(phase_key, phase_key.capitalize()),
            "status": phase_status,
            "status_icon": status_icon,
            "tokens": tokens,
            "tokens_display": _format_tokens(tokens) if tokens else "—",
            "cost_display": f"${cost:.2f}" if cost > 0 else "—",
            "duration": "",  # Duration per phase not yet tracked
        })

    # Linear link (if task_id present and task_manager is linear)
    linear_url: str | None = None
    if task_id and task_manager == "linear":
        # Extract team key from identifier (e.g., "ADW" from "ADW-17")
        team_key = task_id.split("-")[0].lower() if "-" in task_id else ""
        if team_key:
            linear_url = f"https://linear.app/{team_key}/issue/{task_id}"

    return {
        "run_id": run_id,
        "run_id_short": run_id_short,
        "project_name": project_name,
        "feature": feature,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "started_ago": _relative_time(started_at),
        "duration_display": duration_display,
        "branch_name": branch_name,
        "total_tokens": total_tokens,
        "tokens_display": _format_tokens(total_tokens) if total_tokens else "—",
        "estimated_cost": f"${estimated_cost:.2f}" if estimated_cost > 0 else "—",
        "pr_url": pr_url,
        "linear_url": linear_url,
        "task_id": task_id,
        "artifacts_path": artifacts_path,
        "phases": phases,
        "phases_detail": phases_detail,
        "back_label": back_label,
        "back_url": back_url,
        "is_active": status == "running",
    }


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
    try:
        all_runs = index_manager.get_recent_runs(limit=100000)  # type: ignore[union-attr]
    except Exception:
        logger.exception("Failed to query index for run detail", extra={"run_id": run_id})
        all_runs = []
    run_entry = None
    for entry in all_runs:
        if entry.run_id == run_id:
            run_entry = entry
            break

    if run_entry is None:
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

    # Build run detail context with display name resolution
    all_proj = project_registry.get_all()  # type: ignore[union-attr]
    detail_name_map = {str(p.path): p.name for p in all_proj}
    detail_context = _build_run_detail_context(run_entry, request, detail_name_map)

    if request.headers.get("HX-Request"):
        detail_context["request"] = request
        return templates.TemplateResponse(
            request, "partials/run_detail.html", detail_context,
        )

    # Full page: merge with base page context
    context = _build_page_context(
        request, "run_detail",
        index_manager=index_manager,
        project_registry=project_registry,
        project="",
    )
    context.update(detail_context)
    return templates.TemplateResponse(
        request, "pages/run_detail.html", context,
    )


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _find_run_entry(
    index_manager: object,
    run_id: str,
) -> object | None:
    """Look up a run entry by ID from the index.

    Args:
        index_manager: IndexManager instance.
        run_id: The run ID to find.

    Returns:
        IndexEntry or None if not found.
    """
    try:
        all_runs = index_manager.get_recent_runs(limit=100000)  # type: ignore[union-attr]
    except Exception:
        return None
    for entry in all_runs:
        if entry.run_id == run_id:
            return entry
    return None


def _load_llm_stats(
    runs_dir: Path,
    run_id: str,
    phase: str,
) -> dict | None:
    """Load LLM token stats for a phase from the response JSON file.

    Args:
        runs_dir: Path to the .adw/runs directory.
        run_id: The run ID.
        phase: The phase name.

    Returns:
        Dict with input_tokens and output_tokens, or None if unavailable.
    """
    llm_dir = runs_dir / run_id / "llm"
    if not llm_dir.exists():
        return None

    # Find the latest response file for this phase (e.g., 002_plan_response.json
    # takes precedence over 001_plan_response.json for retries).
    result: dict | None = None
    for f in sorted(llm_dir.iterdir()):
        if f.name.endswith(f"_{phase}_response.json") and f.is_file():
            try:
                data = json.loads(f.read_text())
                stats = data.get("stats", {})
                result = {
                    "input_tokens": stats.get("input_tokens", 0),
                    "output_tokens": stats.get("output_tokens", 0),
                }
            except (json.JSONDecodeError, OSError):
                continue
    return result


def _load_llm_content(
    runs_dir: Path,
    run_id: str,
    phase: str,
    content_type: str,
) -> str | None:
    """Load LLM prompt or response content for a phase.

    For 'response', reads the phase output artifact ({phase}_output.md).
    For 'prompt', reads {phase}_prompt.txt from the artifacts directory
    (if persisted by the phase runner).

    Args:
        runs_dir: Path to the .adw/runs directory.
        run_id: The run ID.
        phase: The phase name.
        content_type: Either 'prompt' or 'response'.

    Returns:
        Text content or None if not found.
    """
    artifacts_dir = runs_dir / run_id / "artifacts" / phase

    if content_type == "response":
        # LLM response is stored as {phase}_output.md
        response_file = artifacts_dir / f"{phase}_output.md"
        if response_file.exists():
            try:
                return response_file.read_text()
            except OSError:
                return None
    elif content_type == "prompt":
        # Prompt is stored as {phase}_prompt.txt if available
        prompt_file = artifacts_dir / f"{phase}_prompt.txt"
        if prompt_file.exists():
            try:
                return prompt_file.read_text()
            except OSError:
                return None

        # Fall back to LLM request JSON files (e.g., 001_plan_request.json)
        llm_dir = runs_dir / run_id / "llm"
        if llm_dir.exists():
            result: str | None = None
            for f in sorted(llm_dir.iterdir()):
                if f.name.endswith(f"_{phase}_request.json") and f.is_file():
                    try:
                        data = json.loads(f.read_text())
                        prompt = data.get("prompt")
                        if prompt:
                            result = prompt
                    except (json.JSONDecodeError, OSError):
                        continue
            if result is not None:
                return result

    return None


@router.get("/runs/{run_id}/phases/{phase}", response_class=HTMLResponse)
async def phase_detail(
    request: Request,
    run_id: str,
    phase: str,
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return phase detail HTML fragment for lazy-loaded accordion content.

    Loads hooks and artifacts data for the specified phase of a run.
    """
    templates = request.app.state.templates

    # Validate phase against known phases (NFR10: no arbitrary path access)
    if phase not in PHASE_SEQUENCE:
        return HTMLResponse(
            content='<p class="text-error text-sm">Invalid phase</p>',
            status_code=400,
        )

    # Find the run in the index
    run_entry = _find_run_entry(index_manager, run_id)
    if run_entry is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Run not found</p>',
            status_code=404,
        )

    # Load RunContext for phase data
    hooks: list[dict] = []
    artifacts_list: list[dict] = []
    llm_stats: dict | None = None

    try:
        project_path = Path(run_entry.project_path)  # type: ignore[union-attr]
        runs_dir = project_path / ".adw" / "runs"
    except (AttributeError, OSError):
        runs_dir = None

    if runs_dir is not None:
        # Load artifacts from disk
        try:
            am = ArtifactManager(runs_dir)
            raw_artifacts = am.list_artifacts(run_id, phase)
            for art in raw_artifacts:
                artifacts_list.append({
                    "name": art["name"],
                    "size": art["size"],
                    "size_display": _format_file_size(art["size"]),
                })
        except (StateError, OSError):
            logger.debug(
                "Failed to load artifacts for phase detail",
                extra={"run_id": run_id, "phase": phase},
            )

        # Load LLM token stats independently of artifacts
        try:
            llm_stats = _load_llm_stats(runs_dir, run_id, phase)
        except (StateError, OSError):
            logger.debug(
                "Failed to load LLM stats for phase detail",
                extra={"run_id": run_id, "phase": phase},
            )

    context = {
        "request": request,
        "run_id": run_id,
        "phase": phase,
        "hooks": hooks,
        "artifacts": artifacts_list,
        "llm_stats": llm_stats,
    }

    return templates.TemplateResponse(
        request, "partials/phase_detail.html", context,
    )


@router.get("/runs/{run_id}/phases/{phase}/prompt", response_class=HTMLResponse)
async def llm_prompt(
    request: Request,
    run_id: str,
    phase: str,
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return LLM prompt content HTML fragment for inline viewer."""
    # Validate phase
    if phase not in PHASE_SEQUENCE:
        return HTMLResponse(
            content='<p class="text-error text-sm">Invalid phase</p>',
            status_code=400,
        )

    run_entry = _find_run_entry(index_manager, run_id)
    if run_entry is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Run not found</p>',
            status_code=404,
        )

    try:
        project_path = Path(run_entry.project_path)  # type: ignore[union-attr]
        runs_dir = project_path / ".adw" / "runs"
        content = _load_llm_content(runs_dir, run_id, phase, "prompt")
    except OSError:
        content = None

    if content is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Prompt not found</p>',
            status_code=404,
        )

    # Escape HTML for safe rendering in pre block
    safe_content = (
        content.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    html = (
        f'<pre class="max-h-96 overflow-y-auto font-mono text-xs '
        f'bg-base-300 rounded-lg p-4 whitespace-pre-wrap">{safe_content}</pre>'
    )
    return HTMLResponse(content=html)


@router.get("/runs/{run_id}/phases/{phase}/response", response_class=HTMLResponse)
async def llm_response(
    request: Request,
    run_id: str,
    phase: str,
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return LLM response content HTML fragment for inline viewer."""
    # Validate phase
    if phase not in PHASE_SEQUENCE:
        return HTMLResponse(
            content='<p class="text-error text-sm">Invalid phase</p>',
            status_code=400,
        )

    run_entry = _find_run_entry(index_manager, run_id)
    if run_entry is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Run not found</p>',
            status_code=404,
        )

    try:
        project_path = Path(run_entry.project_path)  # type: ignore[union-attr]
        runs_dir = project_path / ".adw" / "runs"
        content = _load_llm_content(runs_dir, run_id, phase, "response")
    except OSError:
        content = None

    if content is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Response not found</p>',
            status_code=404,
        )

    # Escape HTML for safe rendering in pre block
    safe_content = (
        content.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    html = (
        f'<pre class="max-h-96 overflow-y-auto font-mono text-xs '
        f'bg-base-300 rounded-lg p-4 whitespace-pre-wrap">{safe_content}</pre>'
    )
    return HTMLResponse(content=html)


@router.get("/runs/{run_id}/artifacts/{phase}/{filename:path}", response_class=HTMLResponse)
async def artifact_viewer(
    request: Request,
    run_id: str,
    phase: str,
    filename: str,
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return artifact content HTML fragment for inline viewer.

    Renders markdown files as HTML; all other files in a pre block.
    """
    templates = request.app.state.templates

    # Validate phase against known phases (NFR10: no arbitrary path access)
    if phase not in PHASE_SEQUENCE:
        return HTMLResponse(
            content='<p class="text-error text-sm">Invalid phase</p>',
            status_code=400,
        )

    # Validate filename to prevent path traversal (NFR10)
    if ".." in filename or filename.startswith("/"):
        return HTMLResponse(
            content='<p class="text-error text-sm">Invalid filename</p>',
            status_code=400,
        )

    # Find the run in the index
    run_entry = _find_run_entry(index_manager, run_id)
    if run_entry is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Run not found</p>',
            status_code=404,
        )

    # Load artifact content
    content: str | None = None
    try:
        project_path = Path(run_entry.project_path)  # type: ignore[union-attr]
        runs_dir = project_path / ".adw" / "runs"
        am = ArtifactManager(runs_dir)
        content = am.get(run_id, phase, filename)  # type: ignore[assignment]
    except (StateError, OSError, UnicodeDecodeError):
        logger.debug(
            "Failed to load artifact",
            extra={"run_id": run_id, "phase": phase, "filename": filename},
        )

    if content is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Artifact not found</p>',
            status_code=404,
        )

    # Determine if markdown and render accordingly
    is_markdown = filename.endswith(".md")
    content_html = ""
    if is_markdown:
        try:
            import markdown
            # Escape raw HTML in source before rendering to prevent XSS (NFR10).
            # Only escape angle brackets and ampersand; preserve quotes for code.
            safe_content = (
                content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            content_html = markdown.markdown(
                safe_content, extensions=["fenced_code", "tables"],
            )
        except ImportError:
            # Fallback: just use pre block if markdown library not available
            is_markdown = False

    context = {
        "request": request,
        "filename": filename,
        "content": content,
        "content_html": content_html,
        "is_markdown": is_markdown,
    }

    return templates.TemplateResponse(
        request, "partials/artifact_viewer.html", context,
    )


def _load_log_entries(
    runs_dir: Path,
    run_id: str,
    *,
    phase: str | None = None,
) -> list[dict]:
    """Load and parse log entries from the live.log file.

    Parses lines in the format: [timestamp] [CATEGORY] message
    Maps categories to severity levels for display.

    Args:
        runs_dir: Path to the .adw/runs directory.
        run_id: The run ID.
        phase: Optional phase filter — only return entries mentioning this phase.

    Returns:
        List of dicts with timestamp, level, and message keys.
    """
    import re

    log_file = runs_dir / run_id / "live.log"
    if not log_file.exists():
        return []

    # Pattern: [timestamp] [CATEGORY] message
    line_pattern = re.compile(
        r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+\[(\w+)\]\s+(.*)"
    )

    # Strip ANSI escape codes
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")

    # Map log categories to severity levels
    error_categories = {"ERROR", "FATAL"}
    warn_categories = {"WARN", "WARNING"}

    entries: list[dict] = []
    try:
        content = log_file.read_text(errors="replace")
        for line in content.splitlines():
            # Strip ANSI codes
            clean_line = ansi_pattern.sub("", line).strip()
            if not clean_line:
                continue

            match = line_pattern.match(clean_line)
            if not match:
                continue

            timestamp = match.group(1)
            category = match.group(2).upper()
            message = match.group(3).strip()

            # Strip ANSI from message too
            message = ansi_pattern.sub("", message).strip()

            # Determine severity level
            if category in error_categories:
                level = "ERROR"
            elif category in warn_categories:
                level = "WARN"
            else:
                level = "INFO"

            entries.append({
                "timestamp": timestamp,
                "level": level,
                "message": message,
            })
    except OSError:
        return []

    # Apply phase filter using word-boundary matching to avoid false positives
    # (e.g., "plan" should not match "explain").
    if phase:
        phase_pattern = re.compile(rf"\b{re.escape(phase)}\b")
        entries = [e for e in entries if phase_pattern.search(e["message"])]

    return entries


@router.get("/runs/{run_id}/logs", response_class=HTMLResponse)
async def log_search(
    request: Request,
    run_id: str,
    q: str = Query(""),
    level: str = Query(""),
    phase: str = Query(""),
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return filtered log entries as HTML fragment.

    Supports filtering by keyword (q), severity level, and phase.
    Returns an HTML fragment for HTMX swap into the log content div.
    """
    run_entry = _find_run_entry(index_manager, run_id)
    if run_entry is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Run not found</p>',
            status_code=404,
        )

    try:
        project_path = Path(run_entry.project_path)  # type: ignore[union-attr]
        runs_dir = project_path / ".adw" / "runs"
        entries = _load_log_entries(runs_dir, run_id, phase=phase or None)
    except OSError:
        entries = []

    # Apply level filter
    if level:
        entries = [e for e in entries if e["level"] == level.upper()]

    # Apply keyword search filter
    if q:
        q_lower = q.lower()
        entries = [e for e in entries if q_lower in e["message"].lower()]

    # Build HTML fragment
    if not entries:
        return HTMLResponse(
            content='<p class="text-sm text-base-content/60 py-4">No log entries found</p>'
        )

    lines: list[str] = []
    lines.append(
        '<div class="bg-base-300 rounded-lg p-4 font-mono text-xs '
        'max-h-80 overflow-y-auto">'
    )
    for entry in entries:
        level_class = ""
        if entry["level"] == "WARN":
            level_class = " text-warning"
        elif entry["level"] == "ERROR":
            level_class = " text-error"

        # Escape HTML in message
        safe_msg = (
            entry["message"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        safe_ts = entry["timestamp"]
        safe_level = entry["level"]

        lines.append(
            f'<div class="py-0.5{level_class}">'
            f'<span class="text-base-content/50">{safe_ts}</span> '
            f'<span class="font-semibold">{safe_level}</span> '
            f'{safe_msg}'
            f'</div>'
        )
    lines.append('</div>')

    return HTMLResponse(content="\n".join(lines))


@router.get("/health")
async def health() -> dict[str, str]:
    """Dashboard health check."""
    return {"status": "healthy", "service": "dashboard"}
