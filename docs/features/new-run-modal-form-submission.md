# New Run Modal & Form Submission

**Date:** 2026-02-11
**Related Files:** `src/adw/core/run_trigger.py`, `src/adw/dashboard/mutations.py`, `src/adw/dashboard/templates/partials/new_run_modal.html`, `src/adw/dashboard/templates/partials/run_started.html`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/dependencies.py`

## Overview

Adds the ability to start new ADW runs directly from the dashboard via a DaisyUI modal dialog. The feature extracts core run-triggering logic from the webhook module into a shared `core/run_trigger.py`, introduces the first CSRF-protected POST endpoint in the dashboard (`/runs/start`), and establishes the reusable HTMX modal pattern with server-side form validation and inline error rendering.

## What Was Built

- **Core run trigger** (`core/run_trigger.py`): Shared run-launching logic extracted from `webhook/runner.py`, usable by both dashboard and webhook without cross-importing
- **Mutations router** (`dashboard/mutations.py`): First POST endpoint in the dashboard with CSRF validation, form validation, and HTMX-aware responses
- **New run modal** (`partials/new_run_modal.html`): DaisyUI `<dialog>` modal with project select, feature textarea, CSRF token, and inline validation errors
- **Success confirmation** (`partials/run_started.html`): Post-submission view with OOB swap to clear the modal container
- **Modal container** in `base.html`: Empty `<div id="modal-container">` placed after `</main>` for modal injection
- **Enabled buttons**: All three "+ New Run" buttons in overview wired with HTMX to open the modal

## Technical Implementation

### Key Files

- `src/adw/core/run_trigger.py`: `RunTrigger` class and `RunTriggerResult` dataclass. Spawns `adw run <feature>` as a detached subprocess (`start_new_session=True`)
- `src/adw/dashboard/mutations.py`: `POST /runs/start` route. Validates form data, checks project registry, calls `RunTrigger.start_run()`, returns success view or re-rendered modal with errors
- `src/adw/dashboard/partials.py`: `GET /partials/new-run` route. Populates project list from `ProjectRegistryManager`, generates CSRF token, renders the modal template
- `src/adw/dashboard/dependencies.py`: `get_run_trigger()` DI provider returns a `RunTrigger` instance
- `src/adw/dashboard/templates/partials/new_run_modal.html`: DaisyUI modal template with HTMX form submission
- `src/adw/dashboard/templates/partials/run_started.html`: Success view with OOB modal clearing
- `src/adw/webhook/runner.py`: Refactored to delegate to `core/run_trigger.py` via composition

### Key Patterns

- **HTMX Modal Pattern**: Buttons use `hx-get="/partials/new-run" hx-target="#modal-container" hx-swap="innerHTML"` to load the modal. The `<dialog>` uses `modal-open` class to auto-display. On success, `hx-swap-oob="innerHTML"` on an empty `<div id="modal-container">` clears the modal without JavaScript.

- **CSRF-Protected Mutations**: All POST routes include `dependencies=[Depends(validate_csrf)]`. The CSRF token is HMAC-SHA256 signed with a per-process secret and nonce, included as a hidden form field, and verified with constant-time comparison.

- **Validation Error Re-rendering**: On validation failure, the server returns the modal HTML with error context and sets `HX-Retarget: #modal-container` + `HX-Reswap: innerHTML` headers. This redirects HTMX to re-render the modal in place (instead of the original `#main` target) with inline `text-error` messages below each field.

- **Core Extraction Pattern**: Shared logic lives in `core/` and is used by both `dashboard/` and `webhook/` via dependency injection. The webhook module wraps core with correlation IDs and structured logging; the dashboard uses core directly.

### Code Examples

**Opening the modal from a button:**
```html
<button class="btn btn-primary btn-sm"
        hx-get="/partials/new-run"
        hx-target="#modal-container"
        hx-swap="innerHTML">
  + New Run
</button>
```

**CSRF-protected POST route:**
```python
@router.post("/runs/start", response_class=HTMLResponse, dependencies=[Depends(validate_csrf)])
async def start_run(
    request: Request,
    project: str = Form(""),
    feature: str = Form(""),
    project_registry: object = Depends(get_project_registry),
    run_trigger: object = Depends(get_run_trigger),
) -> HTMLResponse:
    ...
```

**Validation error retargeting:**
```python
response = templates.TemplateResponse(request, "partials/new_run_modal.html", context)
response.headers["HX-Retarget"] = "#modal-container"
response.headers["HX-Reswap"] = "innerHTML"
```

**OOB modal clearing on success (in run_started.html):**
```html
<div id="modal-container" hx-swap-oob="innerHTML"></div>
```

## How to Use

1. Click any "+ New Run" button on the overview page (header, empty states, or full overview)
2. Select a registered project from the dropdown
3. Describe the feature to build in the textarea
4. Click "Start Run" - a loading spinner appears during submission
5. On success, the modal closes and a confirmation card appears with the project name and feature
6. On validation failure, the modal re-renders with inline error messages below the affected fields

## Configuration

No additional configuration required. The run trigger uses the default `adw` CLI command and runs in the selected project's directory.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `adw_command` | str | `"adw"` | CLI command to execute (configurable in `RunTrigger` constructor) |
| CSRF secret | bytes | auto-generated | Per-process secret, rotates on server restart |

## Notes

- The `RunTrigger` spawns a detached subprocess (`start_new_session=True`) so the dashboard response returns immediately without waiting for the run to complete
- CSRF tokens are per-process and rotate on server restart; this is acceptable for a single-user development dashboard
- The modal container `<div id="modal-container">` is placed outside `<main id="main">` to prevent modal state from being lost during HTMX main-content swaps
- `WebhookRunTrigger` now delegates to `RunTrigger` internally, maintaining full backward compatibility for the webhook module
- The `HX-Retarget` / `HX-Reswap` headers on validation failure are essential: without them, HTMX would swap the error response into `#main` (the form's `hx-target`), destroying the page content
