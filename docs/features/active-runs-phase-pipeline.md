# Active Runs Section & Phase Pipeline

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/partials.py`, `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/active_runs.html`, `src/adw/dashboard/templates/components/phase_pipeline.html`, `src/adw/dashboard/templates/partials/overview.html`

## Overview

The dashboard overview page displays an "Active Runs" section showing currently running ADW runs with real-time phase progression, elapsed time, and 3-second HTMX polling. A reusable phase pipeline Jinja2 macro provides compact phase visualization (Plan, Build, Valid, Doc, Ship) usable across the entire dashboard.

## What Was Built

- Active runs section with count badge, clickable run cards, and 3-second auto-refresh via HTMX polling
- Reusable phase pipeline component macro (`phase_pipeline.html`) rendering DaisyUI `steps` with completed/active/pending states
- RunContext-to-IndexEntry fallback: live phase data from disk with graceful degradation on `StateError`
- Empty-state pattern: minimal `<div>` with preserved polling attributes so runs appear automatically when started
- Server-side helpers: `_format_elapsed()`, `_build_phase_pipeline()`, `_load_active_run_details()`

## Technical Implementation

### Key Files

- `src/adw/dashboard/templates/partials/active_runs.html`: Active runs section fragment with HTMX polling, run cards, and empty-state div
- `src/adw/dashboard/templates/components/phase_pipeline.html`: Reusable Jinja2 macro rendering 5-step phase pipeline
- `src/adw/dashboard/partials.py`: `GET /partials/active-runs` route and helper functions for phase pipeline computation, elapsed formatting, and RunContext loading
- `src/adw/dashboard/routes.py`: Overview route builds active runs data via `_load_active_run_details()` for initial server-side render
- `src/adw/core/constants.py`: `PHASE_SEQUENCE` list defining the canonical phase order

### Key Patterns

- **Phase Pipeline Macro**: Import and call `{{ pipeline.phase_pipeline(phases) }}` from `components/phase_pipeline.html`. Accepts a list of dicts with `name` (display label) and `status` (`completed`, `active`, or `pending`). Uses DaisyUI `steps steps-horizontal` with `step-success` for completed, `step-warning` + `phase-active` CSS class for active, and default grey for pending. This macro is the single source of truth for phase visualization and should be used wherever phases are displayed.

- **Empty-State Polling**: When no active runs exist, the template renders an empty `<div id="active-runs">` with `hx-get` and `hx-trigger="every 3s"` preserved. This means HTMX continues polling even when the section is invisible, so newly started runs appear automatically without a page refresh. This pattern should be replicated for any section that can transition from empty to populated.

- **RunContext Fallback**: `_load_active_run_details()` tries to load each run's `RunContext` from disk for live `current_phase` and `phase_history`. If loading fails (e.g., `StateError` from missing context, or `OSError` from inaccessible path), it falls back to the `IndexEntry` fields `phase_reached` and `phases_completed`. This ensures the dashboard never breaks due to stale or missing run state files.

- **Phase Label Abbreviation**: The `_PHASE_LABELS` dict maps full phase names to abbreviated display labels (`validate` -> `Valid`, `document` -> `Doc`) for compact rendering in card layouts. Extend this dict when adding new phases.

### Code Examples

Using the phase pipeline macro in a template:

```jinja2
{# Import the macro at the top of your template #}
{% import "components/phase_pipeline.html" as pipeline %}

{# Render a pipeline — phases is a list of {name, status} dicts #}
{{ pipeline.phase_pipeline(run.phases) }}
```

Building phase pipeline data in Python:

```python
from adw.dashboard.partials import _build_phase_pipeline

phases = _build_phase_pipeline(
    phases_completed=["plan", "build"],
    current_phase="validate",
)
# Returns:
# [{"name": "Plan", "status": "completed"},
#  {"name": "Build", "status": "completed"},
#  {"name": "Valid", "status": "active"},
#  {"name": "Doc", "status": "pending"},
#  {"name": "Ship", "status": "pending"}]
```

Loading active run details for a template context:

```python
from adw.dashboard.partials import _load_active_run_details

entries = index_manager.get_recent_runs(status="running", project_name=project_name)
active_runs = _load_active_run_details(entries)
context["active_runs"] = active_runs
```

## How to Use

1. **Display phase pipelines**: Import `components/phase_pipeline.html` as a Jinja2 macro and call `phase_pipeline(phases)` with a list of `{name, status}` dicts built by `_build_phase_pipeline()`.
2. **Include active runs in a page**: Call `_load_active_run_details(entries)` with running `IndexEntry` objects and pass the result as `active_runs` in the template context, then `{% include "partials/active_runs.html" %}`.
3. **Add a new phase**: Add the phase name to `PHASE_SEQUENCE` in `src/adw/core/constants.py` and add a display label entry in `_PHASE_LABELS` in `partials.py`.
4. **Customize polling interval**: Change the `hx-trigger="every 3s"` value in `active_runs.html`.

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| Active runs poll interval | HTMX trigger | `every 3s` | `hx-trigger` on the active runs section div |
| Active runs section ID | HTML id | `active-runs` | Used for HTMX `outerHTML` swap targeting |
| Card min/max width | CSS | `min-w-[280px] max-w-[400px]` | Responsive card sizing within flex container |
| Feature description truncation | Jinja2 | 40 chars + ellipsis | Truncation applied in template via slice filter |

## Notes

- Active run cards use `border-l-4 border-warning` for a yellow left accent, matching the DaisyUI warning color that represents "in progress" in the dashboard's visual vocabulary.
- The `phase-active` CSS class applies `animate-pulse` to the active step, providing visual feedback that a phase is running. This class is defined in `dashboard.css`.
- OOB stats/status-bar updates were intentionally skipped for the active runs polling cycle. Each section maintains its own independent polling interval (stats=30s, status-bar=10s, active-runs=3s) to avoid unnecessarily computing stats every 3 seconds.
- Elapsed time is computed server-side on each poll (`datetime.now(UTC) - entry.started_at`) and formatted as `Xm Ys`. Hours are shown as accumulated minutes (e.g., `65m 30s`).
- When the browser tab is hidden, HTMX naturally pauses polling via `document.visibilityState`, so no additional logic is needed.
