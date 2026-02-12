# Abort Active Run

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/mutations.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/templates/partials/abort_modal.html`, `src/adw/dashboard/templates/partials/run_detail.html`

## Overview

Adds the ability to abort an active run from the dashboard with a two-step confirmation flow. The abort button on the run detail page opens a DaisyUI modal that shows the run ID and current phase, then submits a CSRF-protected POST that uses the core `InterruptionHandler` to gracefully stop the run, update the index, and refresh the page with OOB swap to clear the modal.

## What Was Built

- HTMX-enabled Abort button on the run detail page (visible only when run is active)
- Abort confirmation modal partial loaded via `GET /partials/abort/{run_id}`
- `POST /runs/{run_id}/abort` mutation endpoint with CSRF validation
- OOB swap pattern to clear the modal container after successful abort
- Dual status validation (index entry + live RunContext) to prevent stale-state aborts

## Technical Implementation

### Key Files

- `src/adw/dashboard/templates/partials/abort_modal.html`: DaisyUI dialog modal with warning text, run metadata, CSRF hidden input, and hx-post form
- `src/adw/dashboard/partials.py` (abort_modal route): GET handler that validates run existence and active status, loads live phase from RunContext with IndexEntry fallback
- `src/adw/dashboard/mutations.py` (abort_run route): POST handler that validates CSRF, checks status at both index and context level, calls `InterruptionHandler.abort_gracefully()`, updates the index, and returns refreshed detail page
- `src/adw/dashboard/templates/partials/run_detail.html`: Abort button with `hx-get` targeting `#modal-container`

### Key Patterns

- **Destructive Action Confirmation Modal**: Two-step flow where the Abort button loads a modal via `hx-get` into `#modal-container`, and the modal form submits via `hx-post` targeting `#main`. This pattern prevents accidental destructive actions and can be reused for any future destructive operation (delete run, force restart, etc.).

- **OOB Modal Clear**: After a successful mutation, the response prepends `<div id="modal-container" hx-swap-oob="innerHTML"></div>` before the main content HTML. This clears the modal without requiring client-side JavaScript, using HTMX's out-of-band swap mechanism.

- **Dual Status Validation**: The abort modal GET route and the abort POST route both validate status at two levels: (1) the index entry status and (2) the live RunContext status loaded from disk. This guards against stale index data where a run may have already completed or failed between page load and abort click.

- **Inline Core Manager Instantiation**: Rather than creating FastAPI dependency providers for `ContextManager` and `SnapshotManager`, these are instantiated inline in the endpoint using the run's `project_path` from the index entry. This avoids unnecessary abstraction for a single-use path.

### Code Examples

```python
# Loading abort modal with live status check (partials.py)
@router.get("/abort/{run_id}", response_class=HTMLResponse)
async def abort_modal(request, run_id, index_manager=Depends(get_index_manager)):
    # ... validate run exists and is active via index ...

    # Load live phase from RunContext, fall back to IndexEntry
    current_phase = run_entry.phase_reached
    try:
        cm = ContextManager(Path(run_entry.project_path) / ".adw" / "runs")
        ctx = cm.load(run_id)
        current_phase = ctx.current_phase
        if ctx.status != "running":
            return HTMLResponse(content="...", status_code=400)
    except (StateError, OSError):
        pass  # fall back to index data
```

```python
# OOB modal clear after successful abort (mutations.py)
modal_clear = '<div id="modal-container" hx-swap-oob="innerHTML"></div>\n'
detail_html = templates.get_template("partials/run_detail.html").render(detail_context)
response = HTMLResponse(content=modal_clear + detail_html)
response.headers["HX-Push-Url"] = f"/runs/{run_id}"
```

```html
<!-- Abort button with HTMX modal trigger (run_detail.html) -->
{% if is_active %}
<button class="btn btn-error btn-outline btn-sm"
        hx-get="/partials/abort/{{ run_id }}"
        hx-target="#modal-container"
        hx-swap="innerHTML">Abort</button>
{% endif %}
```

## How to Use

1. Navigate to a run detail page for an active (running) run
2. Click the "Abort" button in the action buttons row
3. Review the confirmation modal showing run ID and current phase
4. Click "Abort Run" to confirm, or "Cancel" to dismiss
5. On confirmation, the run is stopped, marked as aborted, and the page refreshes

## Notes

- The abort uses `InterruptionHandler.abort_gracefully()` which creates an abort snapshot and uses filelock for concurrent access safety
- The index is updated after abort to reflect the new status; a warning is logged if the index update fails (non-fatal)
- The Abort button is only rendered when `is_active` is true in the template context
- 36 unit tests cover the full abort flow including CSRF validation, status validation, lock timeout handling, and OOB swap verification
