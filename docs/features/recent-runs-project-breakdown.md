# Recent Runs Table & Project Breakdown

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/partials.py`, `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/recent_runs.html`, `src/adw/dashboard/templates/partials/project_breakdown.html`

## Overview

Adds the first data-driven content sections to the dashboard overview: a recent runs table showing the 5 most recent pipeline runs with HTMX auto-polling, and a project breakdown card grid that doubles as an interactive project filter. These sections establish the pattern for embedding polling partials within the overview page while sharing context builders between full-page and partial routes.

## What Was Built

- **Recent Runs Table** — A compact `table-sm` displaying the 5 most recent runs with project name, feature description, status badge, formatted duration, and relative timestamp. Auto-refreshes every 15 seconds via HTMX polling. Rows are clickable to navigate to run details.
- **Project Breakdown Cards** — A flex-wrap row of `card-compact` cards, one per registered project, showing run count, color-coded success rate, and estimated cost. Clicking a card sets the global project filter; the selected card gets a `ring ring-primary` highlight.
- **Shared Context Builders** — `build_recent_runs_context()` and `build_stats_context()` are extracted into `partials.py` so both the overview page route and the standalone partial routes can produce identical template data without duplicating logic.

## Technical Implementation

### Key Files

- `src/adw/dashboard/partials.py`: Contains `recent_runs` and `project_breakdown` route handlers at `/partials/recent-runs` and `/partials/projects`, plus the shared `build_recent_runs_context()` helper.
- `src/adw/dashboard/routes.py`: The `overview()` handler imports shared builders from `partials.py` to populate recent runs and project stats into the overview context.
- `src/adw/dashboard/templates/partials/recent_runs.html`: Jinja2 template with HTMX polling attributes, status badge macro import, clickable rows, and overflow-x-auto responsive wrapper.
- `src/adw/dashboard/templates/partials/project_breakdown.html`: Jinja2 template with conditional filter title, clear button, flex-wrap card layout, and color-coded success rate logic.

### Key Patterns

- **Shared Context Builder Pattern**: The `build_recent_runs_context()` function in `partials.py` transforms `IndexEntry` objects into template-ready dicts. The overview route imports and calls it directly, so the data is identical whether the partial renders standalone (via HTMX poll) or inline (via `{% include %}`). Follow this pattern when adding new overview sections that also have standalone partial endpoints.

- **Project Filter Propagation**: The `selected_project` query parameter propagates through all HTMX attributes — polling URLs (`hx-get`), navigation links (`View All →`), and card click targets. The project breakdown always fetches _unfiltered_ stats (`project_name=None`) so all project cards are visible even when a filter is active; only the ring highlight changes.

- **Template Variable Naming**: The project card data uses `project_stats` (not `projects`) to avoid colliding with the `projects` variable in the page-level context that holds the project name list for the header dropdown.

### Code Examples

Importing and using the shared context builder in a page route:

```python
from adw.dashboard.partials import build_recent_runs_context

entries = index_manager.get_recent_runs(limit=5, project_name=project_name)
context["recent_runs"] = build_recent_runs_context(entries)
```

HTMX polling on a section element (preserves project filter in poll URL):

```html
<section id="recent-runs"
         hx-get="/partials/recent-runs{% if selected_project %}?project={{ selected_project | urlencode }}{% endif %}"
         hx-trigger="every 15s"
         hx-swap="outerHTML">
```

## How to Use

1. The recent runs and project breakdown sections render automatically on the overview page (`/`).
2. To add project filtering to a new section, accept the `project` query param via `Query("", alias="project")` and pass `selected_project` to the template context.
3. To create a new section that embeds in the overview and also has a standalone partial endpoint, extract a `build_*_context()` function in `partials.py` and import it from `routes.py`.

## Configuration

No new configuration options. Data is sourced from `IndexManager` and `StatsAggregator` via FastAPI dependency injection.

## Notes

- The recent runs table limits to 5 entries. This is hardcoded in the route handler, not configurable.
- Duration formatting uses `_format_duration()` which accepts milliseconds. Convert from seconds by multiplying by 1000.
- Success rate color thresholds: green >= 80%, yellow 50-79%, red < 50%. These are hardcoded in the Jinja2 template.
- The overview template uses `{% include %}` for all three sections (stats row, recent runs, project breakdown), keeping the overview template itself minimal.
