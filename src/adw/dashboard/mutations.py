"""Dashboard mutation routes (POST endpoints).

All state-changing operations go through this module. Every route
requires CSRF validation via ``Depends(validate_csrf)``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_project_registry,
    get_run_trigger,
    validate_csrf,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/runs/start", response_class=HTMLResponse, dependencies=[Depends(validate_csrf)])
async def start_run(
    request: Request,
    project: str = Form(""),
    feature: str = Form(""),
    project_registry: object = Depends(get_project_registry),
    run_trigger: object = Depends(get_run_trigger),
) -> HTMLResponse:
    """Start a new ADW run from the dashboard.

    Validates the form data, starts the run via :class:`RunTrigger`,
    and returns either a success view or the modal with errors.
    """
    templates = request.app.state.templates

    # Strip whitespace
    project = project.strip()
    feature = feature.strip()

    # Validate inputs
    errors: dict[str, str] = {}
    if not project:
        errors["project"] = "Please select a project."
    if not feature:
        errors["feature"] = "Please describe the feature to build."

    # Validate project exists in registry
    registered_project = None
    if project and not errors.get("project"):
        registered_project = project_registry.get_by_path(Path(project))  # type: ignore[union-attr]
        if registered_project is None:
            errors["project"] = "Project not found or not registered."

    # On validation failure, re-render the modal with errors
    if errors:
        all_projects = project_registry.get_all()  # type: ignore[union-attr]
        project_list = [{"path": p.path, "name": p.name} for p in all_projects]
        csrf_token = generate_csrf_token(request)

        context = {
            "request": request,
            "projects": project_list,
            "csrf_token": csrf_token,
            "errors": errors,
            "form_project": project,
            "form_feature": feature,
        }
        response = templates.TemplateResponse(
            request, "partials/new_run_modal.html", context,
        )
        # Retarget to modal container so the modal re-renders in place
        response.headers["HX-Retarget"] = "#modal-container"
        response.headers["HX-Reswap"] = "innerHTML"
        return response

    # Start the run
    result = await run_trigger.start_run(  # type: ignore[union-attr]
        project_path=project,
        feature=feature,
    )

    if not result.success:
        # Trigger failure – re-render modal with error
        all_projects = project_registry.get_all()  # type: ignore[union-attr]
        project_list = [{"path": p.path, "name": p.name} for p in all_projects]
        csrf_token = generate_csrf_token(request)

        context = {
            "request": request,
            "projects": project_list,
            "csrf_token": csrf_token,
            "errors": {"feature": f"Failed to start run: {result.error}"},
            "form_project": project,
            "form_feature": feature,
        }
        response = templates.TemplateResponse(
            request, "partials/new_run_modal.html", context,
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
        request, "partials/run_started.html", context,
    )
    response.headers["HX-Push-Url"] = "/"
    return response
