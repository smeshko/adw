"""Dashboard mutation routes (POST endpoints).

All state-changing operations go through this module. Every route
requires CSRF validation via ``Depends(validate_csrf)``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from adw.core.context_manager import ContextManager
from adw.core.interruption import InterruptionHandler
from adw.core.snapshot_manager import SnapshotManager
from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
    get_run_trigger,
    validate_csrf,
)
from adw.exceptions import StateError

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

    from adw.core.index_manager import IndexManager
    from adw.core.project_registry import ProjectRegistryManager
    from adw.core.run_trigger import RunTrigger

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_rerun_context(
    from_run: str,
    index_manager: IndexManager,
) -> dict[str, Any]:
    """Look up source run and build re-run template context.

    Args:
        from_run: The source run_id to look up.
        index_manager: IndexManager instance for run lookup.

    Returns:
        Dict with is_rerun, rerun_project_path, rerun_project_name,
        rerun_feature, and from_run keys.
    """
    if not from_run:
        return {
            "is_rerun": False,
            "rerun_project_path": "",
            "rerun_project_name": "",
            "rerun_feature": "",
            "from_run": "",
        }

    recent_runs = index_manager.get_recent_runs(limit=10000)
    source_entry = next((r for r in recent_runs if r.run_id == from_run), None)
    if source_entry is not None:
        return {
            "is_rerun": True,
            "rerun_project_path": source_entry.project_path,
            "rerun_project_name": source_entry.project_name,
            "rerun_feature": source_entry.feature_description,
            "from_run": from_run,
        }

    return {
        "is_rerun": False,
        "rerun_project_path": "",
        "rerun_project_name": "",
        "rerun_feature": "",
        "from_run": "",
    }


@router.post(
    "/runs/start", response_class=HTMLResponse, dependencies=[Depends(validate_csrf)]
)
async def start_run(
    request: Request,
    project: str = Form(""),
    feature: str = Form(""),
    from_run: str = Form(""),
    project_registry: ProjectRegistryManager = Depends(get_project_registry),
    run_trigger: RunTrigger = Depends(get_run_trigger),
    index_manager: IndexManager = Depends(get_index_manager),
) -> HTMLResponse:
    """Start a new ADW run from the dashboard.

    Validates the form data, starts the run via :class:`RunTrigger`,
    and returns either a success view or the modal with errors.
    """
    templates: Jinja2Templates = request.app.state.templates

    # Strip whitespace
    project = project.strip()
    feature = feature.strip()
    from_run = from_run.strip()

    # Validate inputs
    errors: dict[str, str] = {}
    if not project:
        errors["project"] = "Please select a project."
    if not feature:
        errors["feature"] = "Please describe the feature to build."

    # Validate project exists in registry
    registered_project = None
    if project and not errors.get("project"):
        registered_project = project_registry.get_by_path(Path(project))
        if registered_project is None:
            errors["project"] = "Project not found or not registered."

    # On validation failure, re-render the modal with errors
    if errors:
        all_projects = project_registry.get_all()
        project_list = [{"path": p.path, "name": p.name} for p in all_projects]
        csrf_token = generate_csrf_token(request)

        context = {
            "request": request,
            "projects": project_list,
            "csrf_token": csrf_token,
            "errors": errors,
            "form_project": project,
            "form_feature": feature,
            **_build_rerun_context(from_run, index_manager),
        }
        response = templates.TemplateResponse(
            request,
            "partials/new_run_modal.html",
            context,
        )
        # Retarget to modal container so the modal re-renders in place
        response.headers["HX-Retarget"] = "#modal-container"
        response.headers["HX-Reswap"] = "innerHTML"
        return response

    # Start the run
    result = await run_trigger.start_run(
        project_path=project,
        feature=feature,
    )

    if not result.success:
        # Trigger failure – re-render modal with error
        all_projects = project_registry.get_all()
        project_list = [{"path": p.path, "name": p.name} for p in all_projects]
        csrf_token = generate_csrf_token(request)

        context = {
            "request": request,
            "projects": project_list,
            "csrf_token": csrf_token,
            "errors": {"feature": f"Failed to start run: {result.error}"},
            "form_project": project,
            "form_feature": feature,
            **_build_rerun_context(from_run, index_manager),
        }
        response = templates.TemplateResponse(
            request,
            "partials/new_run_modal.html",
            context,
        )
        response.headers["HX-Retarget"] = "#modal-container"
        response.headers["HX-Reswap"] = "innerHTML"
        return response

    # Success – return confirmation view for #main and close modal
    context = {
        "request": request,
        "process_id": result.process_id,
        "project_name": registered_project.name if registered_project else project,
        "feature": feature,
    }
    response = templates.TemplateResponse(
        request,
        "partials/run_started.html",
        context,
    )
    response.headers["HX-Push-Url"] = "/"
    return response


@router.post(
    "/runs/{run_id}/abort",
    response_class=HTMLResponse,
    dependencies=[Depends(validate_csrf)],
)
async def abort_run(
    request: Request,
    run_id: str,
    index_manager: IndexManager = Depends(get_index_manager),
) -> HTMLResponse:
    """Abort an active run from the dashboard.

    Validates the run exists and is active, then uses InterruptionHandler
    to abort gracefully with state preservation and snapshot creation.
    Returns the refreshed run detail page with OOB modal clear.
    """
    from adw.dashboard.routes import _build_run_detail_context

    templates: Jinja2Templates = request.app.state.templates

    # Look up the run in the index
    all_runs = index_manager.get_recent_runs(limit=100000)
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
            content=(
                '<p class="text-error text-sm">'
                "Run cannot be aborted — it is not active</p>"
            ),
            status_code=400,
        )

    # Instantiate core managers for this run's project
    project_path = Path(run_entry.project_path)
    runs_dir = project_path / ".adw" / "runs"
    cm = ContextManager(runs_dir)
    sm = SnapshotManager(runs_dir)

    # Load context and perform abort
    try:
        context = cm.load(run_id)
    except (StateError, OSError) as e:
        logger.error(
            "Failed to load context for abort",
            extra={"run_id": run_id, "error": str(e)},
        )
        return HTMLResponse(
            content='<p class="text-error text-sm">Failed to load run context</p>',
            status_code=500,
        )

    if context.status != "running":
        return HTMLResponse(
            content=(
                '<p class="text-error text-sm">'
                "Run cannot be aborted — it is not active</p>"
            ),
            status_code=400,
        )

    try:
        handler = InterruptionHandler(
            context_manager=cm,
            snapshot_manager=sm,
        )
        aborted_ctx = handler.abort_gracefully(context, reason="dashboard_abort")
    except (StateError, OSError) as e:
        logger.error("Failed to abort run", extra={"run_id": run_id, "error": str(e)})
        return HTMLResponse(
            content=(
                '<p class="text-error text-sm">'
                "Failed to abort run — another process may be using it</p>"
            ),
            status_code=500,
        )

    # Update the index entry to reflect the abort
    run_entry.status = "aborted"  # type: ignore[assignment]
    run_entry.completed_at = aborted_ctx.completed_at  # type: ignore[assignment]

    # Persist the status change to the global index
    try:
        index_manager.update_run(
            run_id,
            status="aborted",
            completed_at=aborted_ctx.completed_at,
        )
    except (StateError, OSError):
        logger.warning("Failed to update index after abort", extra={"run_id": run_id})

    # Build refreshed run detail context
    detail_context = _build_run_detail_context(run_entry, request)
    detail_context["request"] = request

    # Render OOB modal clear + run detail
    modal_clear = '<div id="modal-container" hx-swap-oob="innerHTML"></div>\n'
    detail_html = templates.get_template("partials/run_detail.html").render(
        detail_context
    )
    response = HTMLResponse(content=modal_clear + detail_html)
    response.headers["HX-Push-Url"] = f"/runs/{run_id}"
    return response
