# Run Detail Page Layout & Metadata

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/pages/run_detail.html`, `src/adw/dashboard/templates/partials/run_detail.html`

## Overview

The run detail page (`/runs/{run_id}`) provides a dedicated drill-down view for individual ADW runs, displaying full metadata, a horizontal phase pipeline with duration, action buttons, and links to external services (GitHub PR, Linear issue). It follows the dashboard's dual-response pattern (full page for direct navigation, HTMX partial for SPA transitions) and enriches IndexEntry data with live RunContext loaded from disk.

## What Was Built

- Run detail route (`/runs/{run_id}`) with dual-response pattern and 404 handling for both full-page and HTMX requests
- Context-aware back link that adapts based on navigation origin (`?from=runs` param or `Referer` header)
- Title section with `{project} / {feature}` heading, large status badge, and monospaced meta line (truncated run ID, branch, duration, relative time)
- Full-width horizontal phase pipeline with per-phase duration display
- Metadata card with 2-column CSS grid showing 12 fields: Run ID (with clipboard copy), Project, Feature, Branch, Started, Completed, Duration, Tokens, Cost, PR link, Linear link, Artifacts path
- Placeholder action buttons (Abort for active runs, Re-run for all) rendered disabled for future interactivity stories
- RunContext enrichment with graceful fallback to IndexEntry data on `StateError` or `OSError`

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py`: Route handler (`run_detail`), context builder (`_build_run_detail_context`), detail phase pipeline helper (`_build_detail_phase_pipeline`), and duration formatter (`_format_duration_from_seconds`)
- `src/adw/dashboard/templates/pages/run_detail.html`: Full page wrapper extending `base.html`, includes the partial
- `src/adw/dashboard/templates/partials/run_detail.html`: HTMX-swappable partial with back link, title, action buttons, phase pipeline, metadata card, and clipboard copy script
- `tests/unit/dashboard/test_run_detail.py`: 47 tests across 10 test classes covering route, back link, title, pipeline, metadata, actions, clipboard, RunContext enrichment, and helper functions

### Key Patterns

- **Dual-Data-Source Context Builder**: `_build_run_detail_context()` first extracts baseline data from the `IndexEntry` (always available from the global index), then attempts to load the `RunContext` from disk via `ContextManager`. If successful, it overrides fields like `current_phase`, `phases_completed`, `branch_name`, `total_tokens`, `pr_url`, `task_id`, and `task_manager` with live data. On failure (`StateError`, `OSError`), it silently falls back to the IndexEntry baseline. This pattern should be used for any detail page that needs richer data than the index provides.

- **Context-Aware Back Link**: The back link destination is determined by a priority chain: (1) `?from=runs` query parameter, (2) `Referer` header containing `/runs` but not the current run's URL, (3) default to overview (`/`). This provides intuitive navigation regardless of how the user arrived at the page. The link uses `hx-get` with `hx-target="#main"` and `hx-push-url` for SPA transitions, plus a regular `href` fallback for non-JS browsing.

- **Detail Phase Pipeline**: `_build_detail_phase_pipeline()` extends the overview's `_build_phase_pipeline()` concept with duration display. Each phase entry includes `{name, status, duration}`. Status logic handles `completed`, `active` (running), `failed` (failed/aborted on current phase), and `pending`. The detail version lives in `routes.py` because it includes additional status logic for completed/interrupted runs (treating current phase as completed) that the overview pipeline does not need.

- **Clipboard Copy Pattern**: A lightweight vanilla JS script attaches click handlers to `.copy-btn` elements, reads the `data-copy` attribute, and writes to `navigator.clipboard`. On success, the button temporarily gains `text-success` class for visual feedback. This pattern can be reused for any copyable value in the dashboard.

### Code Examples

Building run detail context in a route handler:

```python
from adw.dashboard.routes import _build_run_detail_context

# In a route handler with an IndexEntry:
detail_context = _build_run_detail_context(run_entry, request)

# For HTMX partial:
detail_context["request"] = request
return templates.TemplateResponse(request, "partials/run_detail.html", detail_context)

# For full page:
context = _build_page_context(request, "run_detail", ...)
context.update(detail_context)
return templates.TemplateResponse(request, "pages/run_detail.html", context)
```

Using the detail phase pipeline helper:

```python
from adw.dashboard.routes import _build_detail_phase_pipeline

phases = _build_detail_phase_pipeline(
    phases_completed=["plan", "build"],
    current_phase="validate",
    status="running",
)
# Returns:
# [{"name": "Plan", "status": "completed", "duration": ""},
#  {"name": "Build", "status": "completed", "duration": ""},
#  {"name": "Valid", "status": "active", "duration": ""},
#  {"name": "Doc", "status": "pending", "duration": ""},
#  {"name": "Ship", "status": "pending", "duration": ""}]
```

## How to Use

1. **Navigate to a run detail page**: Click a run row in the runs list or active run card — the link should target `/runs/{run_id}?from=runs` (or `?from=overview`) to get the correct back link
2. **Add new metadata fields**: Add the field to `_build_run_detail_context()` return dict, then add a row to the metadata grid in `partials/run_detail.html` following the existing `flex justify-between` pattern
3. **Enable action buttons**: Remove the `disabled` attribute and add `hx-post` / `hx-confirm` attributes to the Abort and Re-run buttons when the backend endpoints are implemented
4. **Reuse clipboard copy**: Add `class="copy-btn"` and `data-copy="value"` to any button — the script in the partial handles the rest

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| Cost estimate rate | Python constant | `total_tokens * 0.000009` | Rough average $/token for cost display |
| Run ID truncation | Python slice | First 8 chars + ellipsis | Displayed in meta line; full ID in metadata card |
| Linear URL format | Python f-string | `https://linear.app/{team_key}/issue/{task_id}` | Team key extracted from identifier prefix |
| Feature truncation in `<title>` | Jinja2 slice | First 40 chars | Browser tab title truncation |

## Notes

- Action buttons (Abort, Re-run) are rendered as disabled placeholders. They will be wired to backend endpoints in a future interactivity story.
- The cost estimate uses a rough average of $0.000009/token. This should be replaced with actual per-model pricing when the cost tracking system is implemented.
- Linear URL construction extracts the team key from the task identifier prefix (e.g., `"ADW"` from `"ADW-17"`) and lowercases it. This assumes the standard Linear URL format `https://linear.app/{team}/issue/{identifier}`.
- The detail phase pipeline in `routes.py` has different status logic than the overview pipeline in `partials.py`: for completed/interrupted runs, it marks the current phase as `completed` rather than leaving it ambiguous. This provides accurate historical representation on the detail page.
- The page sets `active_page = "run_detail"` in the base page context, but no nav item highlights for it since it's a sub-page of runs.
