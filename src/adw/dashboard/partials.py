"""Dashboard partial routes.

HTML fragments returned for HTMX sub-requests.  These routes always
return a fragment — they never wrap in the full page layout.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from adw.core.constants import PHASE_SEQUENCE
from adw.core.context_manager import ContextManager
from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
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
        "cost_strip_tokens_display": _format_tokens(  # type: ignore[union-attr]
            stats.tokens_this_week.total_tokens,
        ),
        "daily_bars": daily_bars,
    }


def build_analytics_context(
    stats_aggregator: object,
    project_name: str | None,
    range_key: str,
    range_days: dict[str, int | None],
    sort: str = "cost_desc",
) -> dict:
    """Build template context for the analytics page stat cards.

    Fetches stats for the selected time range and computes delta values
    by comparing against the previous equivalent period.

    Args:
        stats_aggregator: A StatsAggregator instance.
        project_name: Current project filter value or None.
        range_key: Selected range key (e.g., "7d", "30d", "90d", "all").
        range_days: Mapping of range keys to day counts (None = all time).
        sort: Sort key for breakdown table (e.g., "cost_desc", "runs_asc").

    Returns:
        Dict with analytics stat card values and delta indicators.
    """
    now = datetime.now(UTC)
    days = range_days.get(range_key)

    # Current period
    since = (now - timedelta(days=days)) if days is not None else None
    current_stats = stats_aggregator.get_global_stats(  # type: ignore[union-attr]
        project_name=project_name, since=since, force_refresh=True,
    )

    # Previous equivalent period for delta comparison
    prev_since = now - timedelta(days=days * 2) if days is not None else None

    has_data = current_stats.total_runs > 0

    # Compute current period values
    total_tokens = current_stats.tokens.total_tokens
    total_cost = current_stats.estimated_cost
    total_runs = current_stats.total_runs
    avg_tokens_per_run = total_tokens // total_runs if total_runs > 0 else 0

    # Compute previous period values for deltas
    tokens_delta = 0
    cost_delta = 0.0
    runs_delta = 0
    avg_tokens_delta = 0

    if days is not None:
        # Fetch stats for the previous equivalent period
        prev_stats = stats_aggregator.get_global_stats(  # type: ignore[union-attr]
            project_name=project_name, since=prev_since, force_refresh=True,
        )
        # The prev_stats includes ALL runs since prev_since.
        # We need only runs between prev_since and prev_until.
        # Since get_global_stats doesn't support an "until" param,
        # compute: prev_period = prev_all - current_period
        prev_total_runs = max(0, prev_stats.total_runs - current_stats.total_runs)
        prev_total_tokens = max(
            0, prev_stats.tokens.total_tokens - current_stats.tokens.total_tokens,
        )
        prev_total_cost = max(
            0.0, prev_stats.estimated_cost - current_stats.estimated_cost,
        )
        prev_avg_tokens = (
            prev_total_tokens // prev_total_runs if prev_total_runs > 0 else 0
        )

        tokens_delta = total_tokens - prev_total_tokens
        cost_delta = total_cost - prev_total_cost
        runs_delta = total_runs - prev_total_runs
        avg_tokens_delta = avg_tokens_per_run - prev_avg_tokens

    # ── Daily chart bars ──
    daily_chart_bars: list[dict] = []
    if has_data:
        daily_counts = stats_aggregator.get_daily_token_counts(  # type: ignore[union-attr]
            project_name=project_name, days=days or 30,
        )
        max_daily = max(
            (d["input_tokens"] + d["output_tokens"] for d in daily_counts),
            default=0,
        )
        for d in daily_counts:
            inp = d["input_tokens"]
            out = d["output_tokens"]
            total = inp + out
            if max_daily > 0:
                out_h = int((out / max_daily) * 100)
                inp_h = int((inp / max_daily) * 100)
                # Ensure the tallest bar sums to exactly 100
                if total == max_daily:
                    inp_h = 100 - out_h
            else:
                out_h = 0
                inp_h = 0
            daily_chart_bars.append({
                "day_label": _DAY_LABELS[d["date"].weekday()],
                "output_height": out_h,
                "input_height": inp_h,
                "tokens": total,
            })

    # ── Project breakdown ──
    project_breakdown: list[dict] = []
    if has_data:
        proj_stats = current_stats.projects
        proj_total = sum(p.tokens.total_tokens for p in proj_stats)
        sorted_projects = sorted(
            proj_stats, key=lambda p: p.tokens.total_tokens, reverse=True,
        )
        for proj in sorted_projects:
            proj_tok = proj.tokens.total_tokens
            pct = int((proj_tok / proj_total) * 100) if proj_total else 0
            project_breakdown.append({
                "name": proj.name,
                "percentage": pct,
            })

    # ── Phase breakdown ──
    canonical_phases = ["plan", "build", "validate", "document", "ship"]
    phase_display = {
        "plan": "Plan", "build": "Build", "validate": "Validate",
        "document": "Document", "ship": "Ship",
    }
    phase_breakdown: list[dict] = []
    if has_data:
        phase_data = stats_aggregator.get_phase_breakdown(  # type: ignore[union-attr]
            project_name=project_name, since=since,
        )
        phase_total = sum(
            phase_data.get(p, 0) for p in canonical_phases
        )
        for phase_key in canonical_phases:
            tokens_val = phase_data.get(phase_key, 0)
            if tokens_val > 0:
                pct = int((tokens_val / phase_total) * 100) if phase_total > 0 else 0
                phase_breakdown.append({
                    "name": phase_display.get(phase_key, phase_key.capitalize()),
                    "percentage": pct,
                })

    # ── Model breakdown ──
    from adw.models.stats import TokenUsage as _TokenUsage

    model_breakdown: list[dict] = []
    if has_data:
        model_data = stats_aggregator.get_model_breakdown(  # type: ignore[union-attr]
            project_name=project_name, since=since,
        )
        model_total_tokens = sum(
            v["input_tokens"] + v["output_tokens"] for v in model_data.values()
        )
        sorted_models = sorted(
            model_data.items(),
            key=lambda kv: kv[1]["input_tokens"] + kv[1]["output_tokens"],
            reverse=True,
        )
        for model_name, model_tokens in sorted_models:
            total_m = model_tokens["input_tokens"] + model_tokens["output_tokens"]
            pct = int((total_m / model_total_tokens) * 100) if model_total_tokens else 0
            cost = stats_aggregator.calculate_cost(  # type: ignore[union-attr]
                _TokenUsage(
                    input_tokens=model_tokens["input_tokens"],
                    output_tokens=model_tokens["output_tokens"],
                ),
                model=model_name,
            )
            model_breakdown.append({
                "name": model_name,
                "percentage": pct,
                "cost_display": f"${cost:.2f}",
            })

    # ── Budget section ──
    budget_env = os.environ.get("ADW_MONTHLY_BUDGET")
    has_budget = False
    budget_amount = 0.0
    budget_spent = "$0.00"
    budget_percentage = 0.0
    budget_progress_class = "progress-primary"
    budget_days_remaining: int | None = None

    if budget_env:
        try:
            budget_amount = float(budget_env)
            if budget_amount > 0:
                has_budget = True
                budget_spent = f"${total_cost:.2f}"
                budget_percentage = round((total_cost / budget_amount) * 100, 1)

                if budget_percentage > 90:
                    budget_progress_class = "progress-error"
                elif budget_percentage >= 70:
                    budget_progress_class = "progress-warning"

                # Estimate days remaining based on daily average
                if days is not None and total_cost > 0:
                    remaining = budget_amount - total_cost
                    if remaining > 0:
                        daily_avg_cost = total_cost / days
                        budget_days_remaining = int(remaining / daily_avg_cost)
                    else:
                        budget_days_remaining = 0
        except ValueError:
            pass

    # ── Detailed breakdown table ──
    breakdown_table: list[dict] = []
    if has_data:
        for proj in current_stats.projects:
            proj_tokens = proj.tokens.total_tokens
            proj_cost = stats_aggregator.calculate_cost(proj.tokens)  # type: ignore[union-attr]
            proj_runs = proj.total_runs
            avg_tok = proj_tokens // proj_runs if proj_runs > 0 else 0
            breakdown_table.append({
                "name": proj.name,
                "runs": proj_runs,
                "tokens_display": _format_tokens(proj_tokens),
                "cost_display": f"${proj_cost:.2f}",
                "avg_tokens_display": _format_tokens(avg_tok),
                "tokens_raw": proj_tokens,
                "cost_raw": proj_cost,
                "runs_raw": proj_runs,
                "avg_tokens_raw": avg_tok,
            })

        # Sort breakdown table
        sort_key_map: dict[str, str] = {
            "cost": "cost_raw",
            "tokens": "tokens_raw",
            "runs": "runs_raw",
            "project": "name",
            "avg": "avg_tokens_raw",
        }
        parts = sort.rsplit("_", 1)
        col = parts[0] if len(parts) == 2 else "cost"
        direction = parts[1] if len(parts) == 2 else "desc"
        sort_field = sort_key_map.get(col, "cost_raw")
        reverse = direction == "desc"
        breakdown_table.sort(key=lambda r: r[sort_field], reverse=reverse)

    return {
        "has_analytics_data": has_data,
        # Stat card values
        "analytics_total_tokens": _format_tokens(total_tokens),
        "analytics_total_cost": f"${total_cost:.2f}",
        "analytics_avg_tokens": _format_tokens(avg_tokens_per_run),
        "analytics_total_runs": total_runs,
        # Delta values
        "tokens_delta": tokens_delta,
        "tokens_delta_display": _format_tokens(abs(tokens_delta)),
        "cost_delta": cost_delta,
        "cost_delta_display": f"${abs(cost_delta):.2f}",
        "runs_delta": runs_delta,
        "avg_tokens_delta": avg_tokens_delta,
        "avg_tokens_delta_display": _format_tokens(abs(avg_tokens_delta)),
        # Chart and breakdown data
        "daily_chart_bars": daily_chart_bars,
        "project_breakdown": project_breakdown,
        "phase_breakdown": phase_breakdown,
        "model_breakdown": model_breakdown,
        # Budget section
        "has_budget": has_budget,
        "budget_amount": budget_amount,
        "budget_spent": budget_spent,
        "budget_percentage": budget_percentage,
        "budget_progress_class": budget_progress_class,
        "budget_days_remaining": budget_days_remaining,
        # Breakdown table
        "breakdown_table": breakdown_table,
        "breakdown_sort": sort,
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


# ── Keyboard Help Modal ──────────────────────────────────────────


@router.get("/keyboard-help", response_class=HTMLResponse)
async def keyboard_help(request: Request) -> HTMLResponse:
    """Return the keyboard shortcut overlay modal HTML fragment."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "partials/keyboard_help.html", {"request": request}
    )


# ── New Run Modal ────────────────────────────────────────────────


@router.get("/new-run", response_class=HTMLResponse)
async def new_run_modal(
    request: Request,
    from_run: str = Query("", alias="from"),
    project_registry: object = Depends(get_project_registry),
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return the new run modal HTML fragment.

    When ``from`` query parameter is provided with a valid run_id,
    the modal is pre-populated with the source run's project and
    feature description for re-run context.
    """
    templates = request.app.state.templates

    all_projects = project_registry.get_all()  # type: ignore[union-attr]
    project_list = [{"path": p.path, "name": p.name} for p in all_projects]
    csrf_token = generate_csrf_token(request)

    # Re-run context defaults
    is_rerun = False
    rerun_project_path = ""
    rerun_project_name = ""
    rerun_feature = ""

    if from_run:
        # Look up the source run in the global index
        recent_runs = index_manager.get_recent_runs(limit=10000)  # type: ignore[union-attr]
        source_entry = next(
            (r for r in recent_runs if r.run_id == from_run), None
        )
        if source_entry is not None:
            is_rerun = True
            rerun_project_path = source_entry.project_path
            rerun_project_name = source_entry.project_name
            rerun_feature = source_entry.feature_description

    context = {
        "request": request,
        "projects": project_list,
        "csrf_token": csrf_token,
        "errors": {},
        "form_project": rerun_project_path if is_rerun else "",
        "form_feature": rerun_feature if is_rerun else "",
        "is_rerun": is_rerun,
        "rerun_project_path": rerun_project_path,
        "rerun_project_name": rerun_project_name,
        "rerun_feature": rerun_feature,
        "from_run": from_run if is_rerun else "",
    }

    return templates.TemplateResponse(
        request, "partials/new_run_modal.html", context
    )


# ── Abort Modal ──────────────────────────────────────────────────


@router.get("/abort/{run_id}", response_class=HTMLResponse)
async def abort_modal(
    request: Request,
    run_id: str,
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    """Return the abort confirmation modal HTML fragment.

    Validates the run exists and is active before rendering the modal.
    Falls back to IndexEntry data if RunContext is unavailable.
    """
    templates = request.app.state.templates

    # Look up the run in the index
    all_runs = index_manager.get_recent_runs(limit=100000)  # type: ignore[union-attr]
    run_entry = None
    for entry in all_runs:
        if entry.run_id == run_id:
            run_entry = entry
            break

    if run_entry is None:
        return HTMLResponse(
            content='<p class="text-error text-sm">Run not found</p>',
            status_code=404,
        )

    # Validate run is active
    if run_entry.status != "running":
        return HTMLResponse(
            content='<p class="text-error text-sm">Run cannot be aborted — it is not active</p>',
            status_code=400,
        )

    # Load current phase from RunContext (live data), fall back to IndexEntry
    current_phase = run_entry.phase_reached
    try:
        project_path = Path(run_entry.project_path)
        runs_dir = project_path / ".adw" / "runs"
        cm = ContextManager(runs_dir)
        ctx = cm.load(run_id)
        current_phase = ctx.current_phase
        # Verify live status in case index is stale
        if ctx.status != "running":
            return HTMLResponse(
                content='<p class="text-error text-sm">Run cannot be aborted — it is no longer active</p>',
                status_code=400,
            )
    except (StateError, OSError):
        logger.debug(
            "RunContext unavailable for abort modal, using IndexEntry fallback",
            extra={"run_id": run_id},
        )

    run_id_short = run_id[:8] + "…"
    csrf_token = generate_csrf_token(request)

    context = {
        "request": request,
        "run_id": run_id,
        "run_id_short": run_id_short,
        "current_phase": current_phase,
        "csrf_token": csrf_token,
    }

    return templates.TemplateResponse(
        request, "partials/abort_modal.html", context
    )
