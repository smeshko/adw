# Re-run Flow

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/partials.py`, `src/adw/dashboard/mutations.py`, `src/adw/dashboard/templates/partials/new_run_modal.html`, `src/adw/dashboard/templates/partials/run_detail.html`

## Overview

Adds the ability to start a new run pre-populated with context from a previous run. From any run detail page, clicking the "Re-run" button opens the existing New Run modal with the project locked (disabled) and the feature description pre-filled. This allows developers to quickly retry or iterate on a previous feature without retyping details.

## What Was Built

- **Re-run button enablement** (`partials/run_detail.html`): The previously disabled "Re-run" button is now active with HTMX attributes that load the modal with `?from={run_id}` query parameter
- **Source run lookup** (`dashboard/partials.py`): The `GET /partials/new-run` endpoint accepts an optional `from` query parameter, looks up the source run in the global index, and passes re-run context to the template
- **Conditional modal rendering** (`partials/new_run_modal.html`): The modal template conditionally shows "Re-run" title, locks the project select (disabled with hidden input), and pre-fills the feature textarea
- **Error context preservation** (`dashboard/mutations.py`): Validation errors and trigger failures re-render the modal with re-run state intact (title, locked project, from_run hidden field)

## Technical Implementation

### Key Files

- `src/adw/dashboard/partials.py`: Modified `new_run_modal()` to accept `from` query param via `Query("", alias="from")`, look up source run via `IndexManager.get_recent_runs()`, and pass `is_rerun`, `rerun_project_path`, `rerun_project_name`, `rerun_feature`, and `from_run` to template context
- `src/adw/dashboard/mutations.py`: Added `from_run` form parameter, `index_manager` dependency, and `_build_rerun_context()` helper to preserve re-run state on validation errors and trigger failures
- `src/adw/dashboard/templates/partials/new_run_modal.html`: Conditional `{% if is_rerun %}` blocks for title, disabled project select with hidden input, and from_run hidden field
- `src/adw/dashboard/templates/partials/run_detail.html`: Re-run button activated with `hx-get="/partials/new-run?from={{ run_id }}"` targeting `#modal-container`

### Key Patterns

- **Disabled Select with Hidden Input**: HTML disabled elements don't submit values. The pattern uses a hidden `<input type="hidden" name="project" value="...">` alongside the disabled `<select>` to ensure the project path is always included in the POST data. This is the standard HTML workaround for submitting values from disabled form elements.

- **Re-run State Round-tripping**: A hidden `<input name="from_run" value="...">` preserves the source run_id across form submissions. When the mutations endpoint re-renders the modal on validation error, it reads `from_run` from the form data, looks up the source run again, and passes the re-run context back to the template. This ensures the "Re-run" title and locked project persist after errors.

- **Graceful Fallback**: If the `from` run_id doesn't match any existing run (deleted from index or invalid ID), the endpoint silently falls back to the standard "Start New Run" modal with empty fields and an editable project select. No error is shown — the user simply gets the normal new-run experience.

- **Endpoint Reuse**: Both new-run and re-run flows share the same endpoints (`GET /partials/new-run` and `POST /runs/start`). The `from` query parameter and `from_run` form field are the only differentiators. This avoids code duplication and keeps the modal infrastructure unified.

### Code Examples

**Re-run button on run detail page:**
```html
<button class="btn btn-primary btn-outline btn-sm"
        hx-get="/partials/new-run?from={{ run_id }}"
        hx-target="#modal-container"
        hx-swap="innerHTML">Re-run</button>
```

**Query parameter handling in partials route:**
```python
@router.get("/new-run", response_class=HTMLResponse)
async def new_run_modal(
    request: Request,
    from_run: str = Query("", alias="from"),
    project_registry: object = Depends(get_project_registry),
    index_manager: object = Depends(get_index_manager),
) -> HTMLResponse:
    ...
```

**Conditional modal title in template:**
```html
<h3 class="text-lg font-bold mb-4">
  {% if is_rerun %}Re-run{% else %}Start New Run{% endif %}
</h3>
```

**Disabled project select with hidden input:**
```html
{% if is_rerun %}
<input type="hidden" name="project" value="{{ rerun_project_path }}">
<select id="project-select" class="select select-bordered w-full" disabled>
  <option selected>{{ rerun_project_name }}</option>
</select>
{% else %}
<select id="project-select" name="project" class="select select-bordered w-full">
  ...
</select>
{% endif %}
```

## How to Use

1. Navigate to any run's detail page (completed, failed, interrupted, or aborted)
2. Click the "Re-run" button in the action buttons section
3. The modal opens with "Re-run" title, the project locked to the original run's project, and the feature description pre-filled
4. Edit the feature description as needed (the project cannot be changed)
5. Click "Start Run" to create a new run with the pre-selected project and updated feature
6. On success, the modal closes and a confirmation view appears

## Configuration

No additional configuration required. The re-run flow reuses the same `RunTrigger` and `POST /runs/start` endpoint as the standard new-run flow.

## Notes

- The Re-run button appears for ALL run statuses (completed, failed, interrupted, aborted) — it is not limited to finished runs
- The project select is disabled/locked during re-run to prevent accidental project changes. If the source run's project is no longer registered, the select still shows the project name but a validation error appears on submission: "Project not found or not registered"
- Re-run context is preserved across validation errors: if the user submits with an empty feature, the modal re-renders with the "Re-run" title and locked project intact
- The `from_run` hidden input ensures re-run state survives form re-rendering without requiring session storage or cookies
- Source run lookup uses `IndexManager.get_recent_runs(limit=10000)` — for very large indices, this could be optimized with a dedicated `get_run_by_id()` method in the future
