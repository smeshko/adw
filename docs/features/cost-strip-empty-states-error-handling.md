# Cost Summary Strip, Empty States & Error Handling

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/core/stats_aggregator.py`, `src/adw/dashboard/templates/partials/overview.html`, `src/adw/dashboard/templates/partials/cost_strip.html`, `src/adw/dashboard/templates/partials/data_error_banner.html`, `src/adw/dashboard/templates/pages/run_not_found.html`, `src/adw/dashboard/templates/base.html`

## Overview

The overview page uses a three-state rendering pattern — no projects, no runs, or full dashboard — with a cost summary strip showing weekly spend and a 7-day token bar chart. Error resilience wraps all data-layer calls so the page degrades gracefully, and a global HTMX error toast provides retry capability for failed requests.

## What Was Built

- **Cost Summary Strip**: Compact card showing weekly cost, total tokens, and a 7-day mini bar chart with server-side height calculation
- **Three-State Overview**: Conditional rendering for welcome (no projects), empty (no runs), and full dashboard states
- **Data Error Banner**: Reusable `alert-error` partial for data-layer failures (corrupted index, file lock)
- **HTMX Error Toast**: Global error handler with XSS-safe DOM construction, status display, retry link, and 5-second auto-dismiss
- **404 Run Not Found**: Dual-response pattern returning fragment (HTMX) or full page (direct navigation)
- **New Run Button**: Placeholder `btn btn-primary btn-sm` button (functional in Epic 3)

## Technical Implementation

### Key Files

- `src/adw/core/stats_aggregator.py`: `get_daily_token_counts()` method returns 7-day token breakdown grouped by UTC date, filtered to registered projects
- `src/adw/dashboard/partials.py`: `build_cost_strip_context()` computes bar heights as percentages relative to the max-day value
- `src/adw/dashboard/routes.py`: `overview()` route detects empty states and wraps data calls in try/except for graceful degradation
- `src/adw/dashboard/templates/partials/overview.html`: Three-branch conditional template (`has_projects` → `has_runs` → full view)
- `src/adw/dashboard/templates/partials/cost_strip.html`: 7-bar chart using inline `style="height: X%"` with `min-height: 2px` fallback
- `src/adw/dashboard/templates/partials/data_error_banner.html`: Reusable error banner with default message fallback
- `src/adw/dashboard/templates/base.html`: HTMX `responseError` event handler (~15 lines inline JS)

### Key Patterns

- **Three-State Overview Rendering**: The overview route checks `has_projects` then `has_runs` to select which template branch renders. When neither condition is met, a welcome card with CLI instructions appears. This pattern should be followed for any dashboard page that needs progressive empty states.

- **Error Resilience Wrapping**: Data-layer calls in the route handler are wrapped in try/except blocks. On failure, `data_error=True` and `data_error_message` are set in the template context, and the page renders whatever data is available. The error banner partial is conditionally included at the top of the overview.

- **Server-Side Bar Height Calculation**: The `build_cost_strip_context()` function computes percentage heights for the 7-day bar chart. The max-day gets 100%, others get proportional values, and all-zero days get 0%. This avoids client-side JavaScript for the chart.

- **XSS-Safe HTMX Error Toast**: The error handler in `base.html` uses `document.createTextNode()` instead of `.innerHTML` to prevent XSS from error messages. The retry link calls `htmx.ajax('GET', retryPath, {target:'#main'})` to re-request the failed path.

- **Dual-Response 404**: The `run_detail()` route returns an HTML fragment (no `<!DOCTYPE>`) for HTMX requests and a full page (extending `base.html`) for direct browser navigation, both with `status_code=404`.

### Code Examples

Adding a new empty state to a dashboard page:

```python
# In routes.py — detect empty state before loading data
all_projects = project_registry.get_all()
has_projects = len(all_projects) > 0
context["has_projects"] = has_projects

if has_projects:
    context["data_error"] = False
    try:
        recent = index_manager.get_recent_runs(limit=1, project_name=project_name)
        has_runs = len(recent) > 0
    except Exception:
        has_runs = False
        context["data_error"] = True
        context["data_error_message"] = "Unable to load run data."
    context["has_runs"] = has_runs
```

Building bar chart context with proportional heights:

```python
# In partials.py — compute percentage heights for bar chart
max_tokens = max((d["tokens"] for d in daily_counts), default=0)
daily_bars = []
for d in daily_counts:
    tokens = d["tokens"]
    height_pct = int((tokens / max_tokens) * 100) if max_tokens > 0 else 0
    daily_bars.append({"date_label": day_label, "height_pct": height_pct, "tokens": tokens})
```

## How to Use

1. **Cost strip** renders automatically on the full overview when `has_runs` is True — no separate endpoint needed
2. **Empty states** are controlled by `has_projects` and `has_runs` flags in the template context
3. **Error banner** appears when `data_error` is True — include `partials/data_error_banner.html` in any template that loads data
4. **Error toast** is global (in `base.html`) — fires for any failed HTMX request across the dashboard
5. **404 handling** — check if resource exists and return `HTMLResponse(content, status_code=404)` for HTMX or a template response for full pages

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `days` | int | 7 | Number of days in the daily token breakdown (passed to `get_daily_token_counts()`) |
| `project_name` | str \| None | None | Filter cost strip and stats to a specific project |

## Notes

- The "New Run" button is rendered as `disabled` with `data-action="new-run"` — it becomes functional in Epic 3
- The bar chart uses CSS-only rendering (inline height percentages) with no JavaScript
- The cost strip refreshes with the page — no independent HTMX polling
- Project breakdown cards display in the no-runs state (with placeholder content for Stories 1.4–1.5)
- The error toast auto-dismisses after 5 seconds via `setTimeout`
