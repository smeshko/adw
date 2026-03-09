"""Dashboard mutation routes (POST endpoints).

All state-changing operations go through this module. Every route
requires CSRF validation via ``Depends(validate_csrf)``.
"""

from __future__ import annotations

import html
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError as PydanticValidationError

from adw.core.context_manager import ContextManager
from adw.core.interruption import InterruptionHandler
from adw.core.snapshot_manager import SnapshotManager
from adw.dashboard.dependencies import (
    generate_csrf_token,
    get_index_manager,
    get_project_registry,
    get_run_trigger,
    resolve_project_filter,
    validate_csrf,
)
from adw.exceptions import StateError
from adw.models.config import ProjectConfig

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


# ── Settings save ───────────────────────────────────────────────────────────

# Mapping of form field names to nested config dict paths per section.
_SECTION_FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "project": {
        "language": ["language"],
        "platform": ["platform"],
        "test_command": ["test_command"],
        "build_command": ["build_command"],
    },
    "git": {
        "branch_prefix": ["git", "branch_prefix"],
        "skip_hooks": ["git", "skip_hooks"],
        "base_branch": ["git", "base_branch"],
    },
    "worktree": {
        "backend_start": ["worktree", "port_range", "backend_start"],
        "frontend_start": ["worktree", "port_range", "frontend_start"],
    },
    "llm": {
        "max_retries": ["llm", "retry", "max_retries"],
        "base_delay_seconds": ["llm", "retry", "base_delay_seconds"],
        "max_delay_seconds": ["llm", "retry", "max_delay_seconds"],
        "multiplier": ["llm", "retry", "multiplier"],
    },
    "task_manager": {
        "type": ["task_manager", "type"],
        "team_key": ["task_manager", "team_key"],
        "sync_comments": ["task_manager", "sync_comments"],
        "auto_close": ["task_manager", "auto_close"],
        "labels_enabled": ["task_manager", "labels", "enabled"],
        "label_prefix": ["task_manager", "labels", "prefix"],
    },
    "security": {},
}

# Fields that should be parsed as integers.
_INT_FIELDS = {"max_retries", "backend_start", "frontend_start"}

# Fields that should be parsed as floats.
_FLOAT_FIELDS = {"base_delay_seconds", "max_delay_seconds", "multiplier"}

# Fields that should be parsed as booleans.
_BOOL_FIELDS = {"skip_hooks", "sync_comments", "auto_close", "labels_enabled"}


def _parse_form_value(field_name: str, raw_value: str) -> Any:
    """Parse a raw form string value to its correct Python type.

    Args:
        field_name: Name of the form field.
        raw_value: Raw string value from the form submission.

    Returns:
        Parsed value with correct type.
    """
    if field_name in _BOOL_FIELDS:
        return raw_value.lower() in ("true", "1", "on", "yes")
    if field_name in _INT_FIELDS:
        return int(raw_value)
    if field_name in _FLOAT_FIELDS:
        return float(raw_value)
    # String fields — empty string → None for optional fields
    if raw_value == "":
        return None
    return raw_value


def _collect_indexed_fields(form: Any, prefix: str) -> list[str]:
    """Collect indexed form fields into an ordered list.

    Scans form data for keys like ``prefix.0``, ``prefix.1``, etc.
    and returns values in index order, filtering out empty strings.

    Args:
        form: The form data (Starlette FormData or dict-like).
        prefix: Field name prefix (e.g., ``blocked_env_files``).

    Returns:
        Ordered list of non-empty string values.
    """
    items: list[tuple[int, str]] = []
    for key in form:
        if not key.startswith(prefix + "."):
            continue
        suffix = key[len(prefix) + 1 :]
        try:
            idx = int(suffix)
        except ValueError:
            continue
        val = str(form[key]).strip()
        if val:
            items.append((idx, val))
    items.sort(key=lambda x: x[0])
    return [v for _, v in items]


def _collect_mapping_fields(form: Any, prefix: str) -> dict[str, str]:
    """Collect dot-prefixed form fields into a dict.

    Scans form data for keys like ``prefix.plan``, ``prefix.build``, etc.
    and returns a dict mapping the suffix to the string value.

    Args:
        form: The form data (Starlette FormData or dict-like).
        prefix: Field name prefix (e.g., ``state_mapping``).

    Returns:
        Dict mapping suffix keys to string values.
    """
    result: dict[str, str] = {}
    for key in form:
        if not key.startswith(prefix + "."):
            continue
        suffix = key[len(prefix) + 1 :]
        val = str(form[key]).strip()
        result[suffix] = val
    return result


def _deep_set(data: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set a value in a nested dict using a list of keys.

    Args:
        data: The dict to modify in place.
        keys: Path of keys to the target value.
        value: The value to set.
    """
    for key in keys[:-1]:
        existing = data.get(key)
        if not isinstance(existing, dict):
            data[key] = {}
        data = data.setdefault(key, {})
    data[keys[-1]] = value


def _atomic_write_config(path: Path, content: str) -> None:
    """Write config file atomically using temp file + rename pattern.

    Args:
        path: Target file path.
        content: YAML content to write.
    """
    temp_path = path.with_suffix(".tmp")
    try:
        with open(temp_path, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        temp_path.replace(path)
        logger.debug("Atomic config write completed", extra={"path": str(path)})
    except OSError:
        if temp_path.exists():
            temp_path.unlink()
        raise


@router.post(
    "/settings/save",
    response_class=HTMLResponse,
    dependencies=[Depends(validate_csrf)],
)
async def save_settings(
    request: Request,
    project_registry: ProjectRegistryManager = Depends(get_project_registry),
) -> HTMLResponse:
    """Save settings for a specific section of project configuration.

    Accepts form data with ``_section``, ``_project``, and field values.
    Loads the existing config, merges the submitted section, validates
    via Pydantic, and writes atomically to disk.
    """
    from adw.config.loader import ConfigLoader
    from adw.config.registry import ConfigRegistry
    from adw.dashboard.routes import (
        _SETTINGS_TABS,
        _build_phase_settings,
        build_complex_settings_context,
        build_settings_context,
        compute_changed_counts,
    )

    templates: Jinja2Templates = request.app.state.templates
    form = await request.form()

    section = str(form.get("_section", ""))
    project_display = str(form.get("_project", ""))

    # Resolve project path from display name
    project_path_str, _ = resolve_project_filter(
        project_registry, project_display
    )
    if not project_path_str:
        return _render_settings_error(
            request, templates, "Project not found.", section, project_display,
            project_registry=project_registry,
        )

    project_root = Path(project_path_str)

    # Validate section is editable
    if section not in _SECTION_FIELD_MAP:
        return _render_settings_error(
            request, templates, "Invalid section.", section, project_display,
            project_registry=project_registry,
        )

    field_map = _SECTION_FIELD_MAP[section]

    # Load existing config as raw dict (for merging)
    config_path = project_root / ".adw" / "project.yaml"
    existing_data: dict[str, Any] = {}
    if config_path.exists():
        try:
            raw = config_path.read_text()
            loaded = yaml.safe_load(raw)
            if isinstance(loaded, dict):
                existing_data = loaded
            elif loaded is not None:
                return _render_settings_error(
                    request, templates,
                    "Existing config file is malformed (not a YAML mapping).",
                    section, project_display,
                    project_registry=project_registry,
                )
        except yaml.YAMLError as e:
            return _render_settings_error(
                request, templates,
                f"Failed to parse existing config: {e}",
                section, project_display,
                project_registry=project_registry,
            )
        except OSError as e:
            logger.warning(
                "Failed to read existing config for merge",
                extra={"project": project_display, "error": str(e)},
            )
            return _render_settings_error(
                request, templates,
                f"Failed to read existing config: {e}",
                section, project_display,
                project_registry=project_registry,
            )

    # Seed required fields if missing (name, language are required by ProjectConfig)
    if "name" not in existing_data:
        existing_data["name"] = project_display or "unnamed"
    if "language" not in existing_data:
        existing_data["language"] = "python"

    # Handle complex field types (indexed lists, mapping dicts) before
    # the standard scalar field loop.
    if section == "task_manager":
        mapping = _collect_mapping_fields(form, "state_mapping")
        if mapping:
            _deep_set(existing_data, ["task_manager", "state_mapping"], mapping)

    if section == "security":
        blocked_commands = _collect_indexed_fields(form, "blocked_commands")
        # Preserve existing BlockedPattern metadata when possible.
        # Build a lookup from pattern string → existing dict so that
        # unchanged patterns keep their description/severity/category.
        existing_bp = (
            existing_data.get("security", {}).get("blocked_patterns", [])
        )
        existing_bp_map: dict[str, dict[str, Any]] = {}
        if isinstance(existing_bp, list):
            for entry in existing_bp:
                if isinstance(entry, dict) and "pattern" in entry:
                    existing_bp_map[entry["pattern"]] = entry
        blocked_patterns = []
        for p in blocked_commands:
            if p in existing_bp_map:
                blocked_patterns.append(existing_bp_map[p])
            else:
                blocked_patterns.append(
                    {
                        "pattern": p,
                        "description": "Custom pattern",
                        "severity": "warning",
                        "category": "destructive",
                    }
                )
        _deep_set(existing_data, ["security", "blocked_patterns"], blocked_patterns)

        blocked_env = _collect_indexed_fields(form, "blocked_env_files")
        _deep_set(existing_data, ["security", "blocked_env_files"], blocked_env)

    # Parse and map form values into the nested config structure
    for field_name, path_keys in field_map.items():
        # HTML hidden+checkbox pattern sends ["false","true"] when checked;
        # form.get() returns the first value ("false"). Use getlist and take last.
        if field_name in _BOOL_FIELDS:
            values = form.getlist(field_name)
            raw_value = values[-1] if values else None
        else:
            raw_value = form.get(field_name)
        if raw_value is None:
            continue
        try:
            parsed = _parse_form_value(field_name, str(raw_value))
        except (ValueError, TypeError) as e:
            return _render_settings_error(
                request,
                templates,
                f"Invalid value for {field_name}: {e}",
                section,
                project_display,
                project_registry=project_registry,
            )
        _deep_set(existing_data, path_keys, parsed)

    # Validate the complete merged config via Pydantic
    try:
        ProjectConfig.model_validate(existing_data)
    except PydanticValidationError as e:
        # Extract first user-facing error message
        errors = e.errors()
        error_msg = errors[0]["msg"] if errors else str(e)
        return _render_settings_error(
            request, templates, f"Validation failed: {error_msg}",
            section, project_display,
            project_registry=project_registry,
        )

    # Create .adw/ directory if it doesn't exist
    adw_dir = project_root / ".adw"
    adw_dir.mkdir(parents=True, exist_ok=True)

    # Write config atomically
    yaml_content = yaml.dump(
        existing_data, default_flow_style=False, sort_keys=False,
        allow_unicode=True,
    )
    try:
        _atomic_write_config(config_path, yaml_content)
    except OSError as e:
        logger.error(
            "Failed to write config",
            extra={"project": project_display, "error": str(e)},
        )
        return _render_settings_error(
            request, templates, f"Failed to save: {e}",
            section, project_display,
            project_registry=project_registry,
        )

    logger.info(
        "Settings saved successfully",
        extra={"project": project_display, "section": section},
    )

    # Re-render the settings content with fresh data and success toast
    loader = ConfigLoader(project_root=project_root)
    config = loader.load()
    registry = ConfigRegistry()

    settings_sections = build_settings_context(config, registry)
    phase_settings = _build_phase_settings(config, registry)
    complex_ctx = build_complex_settings_context(config)

    valid_tab_keys = [t[0] for t in _SETTINGS_TABS]
    if section not in valid_tab_keys:
        section = "project"

    context = {
        "request": request,
        "active_tab": section,
        "settings_sections": settings_sections,
        "phase_settings": phase_settings,
        "has_config": True,
        "selected_settings_project": project_display,
        "csrf_token": generate_csrf_token(request),
        "changed_counts": compute_changed_counts(
            settings_sections,
            complex_ctx["task_manager_context"],
            complex_ctx["security_context"],
        ),
    }
    context.update(complex_ctx)

    content_html = templates.get_template(
        "partials/settings_content.html"
    ).render(context)

    toast_html = (
        '<div id="toast-container" hx-swap-oob="innerHTML">'
        '<div class="alert alert-success shadow-lg">'
        "<span>Settings saved successfully.</span>"
        "</div>"
        "<script>setTimeout(function(){var t=document.getElementById("
        "'toast-container');if(t)t.innerHTML='';},3000);</script>"
        "</div>"
    )

    return HTMLResponse(content=content_html + toast_html)


# ── Phase config save ────────────────────────────────────────────────────────

_VALID_PHASES = frozenset(["plan", "build", "validate", "document", "ship"])


@router.post(
    "/settings/phase/{phase}/save",
    response_class=HTMLResponse,
    dependencies=[Depends(validate_csrf)],
)
async def save_phase_settings(
    request: Request,
    phase: str,
    project_registry: "ProjectRegistryManager" = Depends(get_project_registry),
) -> HTMLResponse:
    """Save phase config to .adw/commands/{phase}/config.yaml.

    Parses form fields, validates via the phase-specific Pydantic model,
    and writes atomically to disk.
    """
    from adw.commands.loader import get_config_class
    from adw.config.registry import ConfigRegistry
    from adw.config.yaml_generator import YAMLWithComments

    if phase not in _VALID_PHASES:
        return HTMLResponse(content="Invalid phase.", status_code=400)

    templates: "Jinja2Templates" = request.app.state.templates
    form = await request.form()
    project_display = str(form.get("_project", ""))

    project_path_str, _ = resolve_project_filter(project_registry, project_display)
    if not project_path_str:
        return HTMLResponse(content="Project not found.", status_code=400)

    project_root = Path(project_path_str)

    # Parse base fields
    enabled_raw = str(form.get("enabled", "true"))
    enabled = enabled_raw.lower() in ("true", "1", "on", "yes")
    llm_model = str(form.get("llm_model", ""))

    # Build config dict
    config_data: dict[str, Any] = {
        "enabled": enabled,
    }

    if llm_model:
        config_data["llm"] = {"model": llm_model}

    # Collect input_files key-value pairs
    input_files: dict[str, str] = {}
    for key in form:
        if key.startswith("input_files_key."):
            idx = key[len("input_files_key."):]
            k = str(form[key]).strip()
            v = str(form.get(f"input_files_val.{idx}", "")).strip()
            if k and v:
                input_files[k] = v
    if input_files:
        config_data["input_files"] = input_files

    # Document phase: collect doc_mappings
    if phase == "document":
        doc_mappings: list[dict[str, str]] = []
        for key in form:
            if key.startswith("doc_mappings_source."):
                idx = key[len("doc_mappings_source."):]
                src = str(form[key]).strip()
                docs_dir = str(form.get(f"doc_mappings_dir.{idx}", "")).strip()
                if src and docs_dir:
                    doc_mappings.append({
                        "source_pattern": src,
                        "docs_dir": docs_dir,
                    })
        if doc_mappings:
            config_data["doc_mappings"] = doc_mappings

    # Ship phase: collect commands and bypass_ci
    if phase == "ship":
        version_bump = str(form.get("version_bump", "")).strip()
        publish = str(form.get("publish", "")).strip()
        commands: dict[str, str | None] = {}
        if version_bump:
            commands["version_bump"] = version_bump
        if publish:
            commands["publish"] = publish
        if commands:
            config_data["commands"] = commands

        bypass_raw = str(form.get("bypass_ci", "true"))
        config_data["bypass_ci"] = bypass_raw.lower() in ("true", "1", "on", "yes")

        wait_raw = str(form.get("wait_for_merge", "false"))
        config_data["wait_for_merge"] = wait_raw.lower() in ("true", "1", "on", "yes")

    # Validate via phase-specific Pydantic model
    config_class = get_config_class(phase)
    try:
        config_class.model_validate(config_data)
    except PydanticValidationError as e:
        errors = e.errors()
        error_msg = errors[0]["msg"] if errors else str(e)
        return _render_phase_editor_error(
            request, templates, phase, config_data, project_display,
            f"Validation failed: {html.escape(error_msg)}",
        )

    # Create directory and write atomically
    phase_dir = project_root / ".adw" / "commands" / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    config_path = phase_dir / "config.yaml"

    yaml_gen = YAMLWithComments(ConfigRegistry())
    yaml_content = yaml_gen.generate_phase_yaml(phase, config_data)

    try:
        _atomic_write_config(config_path, yaml_content)
    except OSError as e:
        logger.error(
            "Failed to write phase config",
            extra={"phase": phase, "project": project_display, "error": str(e)},
        )
        return _render_phase_editor_error(
            request, templates, phase, config_data, project_display,
            f"Failed to save: {html.escape(str(e))}",
        )

    logger.info(
        "Phase settings saved",
        extra={"phase": phase, "project": project_display},
    )

    # Re-render the phase editor partial with fresh data + success toast
    from adw.dashboard.partials import PHASE_DEFAULTS

    defaults = PHASE_DEFAULTS.get(phase, {"model": "opus"})

    # Reload the config we just saved
    loaded_data = yaml.safe_load(config_path.read_text()) or {}
    loaded_obj = config_class.model_validate(loaded_data)

    has_config = True
    loaded_enabled = loaded_obj.enabled
    loaded_llm_model = defaults["model"]
    if loaded_obj.llm and loaded_obj.llm.model:
        loaded_llm_model = loaded_obj.llm.model
    loaded_input_files = dict(loaded_obj.input_files) if loaded_obj.input_files else {}
    loaded_doc_mappings: list[dict[str, str]] = []
    loaded_ship_vb = ""
    loaded_ship_pub = ""
    loaded_bypass_ci = True

    if phase == "document" and hasattr(loaded_obj, "doc_mappings"):
        dm = loaded_obj.doc_mappings
        if dm:
            loaded_doc_mappings = [
                {"source_pattern": m.source_pattern, "docs_dir": m.docs_dir}
                for m in dm
            ]

    if phase == "ship" and hasattr(loaded_obj, "commands"):
        cmds = loaded_obj.commands
        if cmds:
            loaded_ship_vb = cmds.version_bump or ""
            loaded_ship_pub = cmds.publish or ""
        loaded_bypass_ci = getattr(loaded_obj, "bypass_ci", True)

    context = {
        "phase": phase,
        "has_config": has_config,
        "enabled": loaded_enabled,
        "llm_model": loaded_llm_model,
        "input_files": loaded_input_files,
        "doc_mappings": loaded_doc_mappings,
        "ship_version_bump": loaded_ship_vb,
        "ship_publish": loaded_ship_pub,
        "bypass_ci": loaded_bypass_ci,
        "default_model": defaults["model"],
        "selected_settings_project": project_display,
        "csrf_token": generate_csrf_token(request),
    }

    content_html = templates.get_template(
        "partials/settings_phase_editor.html"
    ).render(context)

    toast_html = (
        '<div id="toast-container" hx-swap-oob="innerHTML">'
        '<div class="alert alert-success shadow-lg">'
        "<span>Phase settings saved successfully.</span>"
        "</div>"
        "<script>setTimeout(function(){var t=document.getElementById("
        "'toast-container');if(t)t.innerHTML='';},3000);</script>"
        "</div>"
    )

    return HTMLResponse(content=content_html + toast_html)


def _render_phase_editor_error(
    request: Request,
    templates: "Jinja2Templates",
    phase: str,
    config_data: dict[str, Any],
    project_display: str,
    error_message: str,
) -> HTMLResponse:
    """Re-render the phase editor with submitted data and an error toast.

    Unlike returning raw error text, this preserves the form UI so the user
    can correct their input and re-submit.
    """
    from adw.dashboard.partials import PHASE_DEFAULTS

    defaults = PHASE_DEFAULTS.get(phase, {"model": "opus"})

    # Extract values from the submitted config_data for re-rendering
    llm_data = config_data.get("llm", {})
    doc_mappings = config_data.get("doc_mappings", [])
    commands = config_data.get("commands", {})

    context = {
        "phase": phase,
        "has_config": True,
        "enabled": config_data.get("enabled", True),
        "llm_model": llm_data.get("model", defaults["model"]) if llm_data else defaults["model"],
        "input_files": config_data.get("input_files", {}),
        "doc_mappings": doc_mappings,
        "ship_version_bump": commands.get("version_bump", "") if commands else "",
        "ship_publish": commands.get("publish", "") if commands else "",
        "bypass_ci": config_data.get("bypass_ci", True),
        "default_model": defaults["model"],
        "selected_settings_project": project_display,
        "csrf_token": generate_csrf_token(request),
    }

    content_html = templates.get_template(
        "partials/settings_phase_editor.html"
    ).render(context)

    toast_html = (
        '<div id="toast-container" hx-swap-oob="innerHTML">'
        '<div class="alert alert-error shadow-lg">'
        f"<span>{error_message}</span>"
        "</div>"
        "<script>setTimeout(function(){var t=document.getElementById("
        "'toast-container');if(t)t.innerHTML='';},5000);</script>"
        "</div>"
    )

    return HTMLResponse(content=content_html + toast_html)


def _render_settings_error(
    request: Request,
    templates: Jinja2Templates,
    error_message: str,
    section: str,
    project_display: str,
    project_registry: ProjectRegistryManager | None = None,
) -> HTMLResponse:
    """Render settings content with an error toast via OOB swap.

    Args:
        request: The current request.
        templates: Jinja2Templates instance.
        error_message: User-facing error message.
        section: The active settings tab.
        project_display: The project display name.
        project_registry: ProjectRegistryManager for resolving project paths.

    Returns:
        HTMLResponse with settings content and error toast.
    """
    from adw.config.loader import ConfigLoader
    from adw.config.registry import ConfigRegistry
    from adw.dashboard.routes import (
        _SETTINGS_TABS,
        _build_phase_settings,
        build_complex_settings_context,
        build_settings_context,
        compute_changed_counts,
    )

    # Try to load config for re-rendering the form
    config = None
    if project_registry is None:
        project_registry = get_project_registry()
    project_path_str, _ = resolve_project_filter(
        project_registry, project_display
    )
    if project_path_str:
        try:
            loader = ConfigLoader(project_root=Path(project_path_str))
            config = loader.load()
        except Exception:
            pass

    registry = ConfigRegistry()
    settings_sections = build_settings_context(config, registry)
    phase_settings = _build_phase_settings(config, registry)
    complex_ctx = build_complex_settings_context(config)

    valid_tab_keys = [t[0] for t in _SETTINGS_TABS]
    if section not in valid_tab_keys:
        section = "project"

    context = {
        "request": request,
        "active_tab": section,
        "settings_sections": settings_sections,
        "phase_settings": phase_settings,
        "has_config": config is not None,
        "selected_settings_project": project_display,
        "csrf_token": generate_csrf_token(request),
        "changed_counts": compute_changed_counts(
            settings_sections,
            complex_ctx["task_manager_context"],
            complex_ctx["security_context"],
        ),
    }
    context.update(complex_ctx)

    content_html = templates.get_template(
        "partials/settings_content.html"
    ).render(context)

    safe_message = html.escape(error_message)
    toast_html = (
        '<div id="toast-container" hx-swap-oob="innerHTML">'
        '<div class="alert alert-error shadow-lg">'
        f"<span>{safe_message}</span>"
        "</div>"
        "<script>setTimeout(function(){var t=document.getElementById("
        "'toast-container');if(t)t.innerHTML='';},3000);</script>"
        "</div>"
    )

    return HTMLResponse(content=content_html + toast_html)
