# Stat Cards & Status Vocabulary

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/partials.py`, `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/stats_row.html`, `src/adw/dashboard/templates/components/status_badge.html`, `src/adw/models/stats.py`, `src/adw/core/stats_aggregator.py`

## Overview

The dashboard overview page displays a row of 5 stat cards showing aggregate ADW health metrics (total runs, success rate, avg duration, tokens used, estimated cost) with week-over-week trend indicators. A reusable status badge macro provides the canonical visual vocabulary for run statuses across the entire dashboard.

## What Was Built

- 5 stat cards in a responsive flex-wrap layout with DaisyUI styling and `font-mono` values
- Week-over-week trend comparison using a sliding 7-14 day "previous week" window
- Trend indicators with green `text-success` / `▲` for positive and red `text-error` / `▼` for negative
- Auto-refresh via HTMX polling (`hx-trigger="every 30s"`) with OOB swap support (`id="stats-row"`)
- Reusable Jinja2 status badge macro mapping 5 statuses to DaisyUI badge classes and icons
- Server-side formatting helpers for duration (`Xm Ys`), tokens (`2.4M`, `340K`), and cost (`$X.XX`)

## Technical Implementation

### Key Files

- `src/adw/dashboard/templates/partials/stats_row.html`: The 5-card stats row template with trend display logic
- `src/adw/dashboard/templates/components/status_badge.html`: Reusable Jinja2 macro for status badges
- `src/adw/dashboard/partials.py`: `GET /partials/stats` route, `build_stats_context()` helper, and formatting functions
- `src/adw/dashboard/routes.py`: Overview route includes stats data via `build_stats_context()`
- `src/adw/models/stats.py`: `GlobalStatistics` model with trend comparison fields
- `src/adw/core/stats_aggregator.py`: Previous-week computation window and this-week token/cost accumulation

### Key Patterns

- **Status Badge Macro**: Import and call `{{ badge.status_badge(status, size) }}` from `components/status_badge.html`. This is the single source of truth for status-to-visual mapping. All dashboard pages rendering status must use this macro rather than inline badge classes.

- **Stats Context Builder**: `build_stats_context(stats, selected_project)` in `partials.py` transforms raw `GlobalStatistics` into pre-formatted template variables. Both the overview page route and the stats partial route call this function, keeping formatting logic DRY.

- **Trend Window**: Trend comparison uses a sliding window — "this week" = last 7 days, "previous week" = 7-14 days ago. This is not calendar-week aligned. Duration trend is inverted: negative ms means faster (shown as green/improvement).

- **Stats Row OOB Refresh**: The stats row div has `id="stats-row"` enabling out-of-band replacement. Other partials can include `hx-swap-oob="true"` on a stats row fragment to update it alongside their own content.

### Code Examples

Using the status badge macro in a template:

```jinja2
{# Import the macro at the top of your template #}
{% import "components/status_badge.html" as badge %}

{# Render a badge — status is a string like "running", "completed", etc. #}
{{ badge.status_badge(run.status) }}

{# Render a larger badge #}
{{ badge.status_badge(run.status, "lg") }}
```

Including stats data in a new route that needs the stats row:

```python
from adw.dashboard.partials import build_stats_context

# In your route handler:
stats = stats_aggregator.get_global_stats(project_name=project_name)
context.update(build_stats_context(stats, project_name))
```

## How to Use

1. **Display status badges**: Import `components/status_badge.html` as a Jinja2 macro and call `status_badge(status_string)`. Valid statuses: `running`, `completed`, `failed`, `interrupted`, `aborted`.
2. **Include stats in a page**: Call `build_stats_context()` with a `GlobalStatistics` object and add the result to your template context, then `{% include "partials/stats_row.html" %}`.
3. **Add a new stat card**: Add a new `<div class="stat ...">` block to `stats_row.html` following the existing pattern. Add the formatted value to `build_stats_context()` in `partials.py`.
4. **Add a new status type**: Add an entry to the `config` dict in `status_badge.html` with `class`, `icon`, and `pulse` keys.

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| Stats poll interval | HTMX trigger | `every 30s` | `hx-trigger` on the stats row div |
| Stats row OOB ID | HTML id | `stats-row` | Used for out-of-band swap targeting |
| Trend window | timedelta | 7 days / 7-14 days | Current vs previous week sliding window |
| Badge sizes | string | `sm` | Supports `sm` and `lg` via DaisyUI `badge-sm`/`badge-lg` |

## Notes

- The stats row wraps to 2 rows at compact widths (1024-1279px) via `flex flex-wrap gap-4` with `min-w-[180px]` per card.
- The `phase-active` CSS class (pulsing animation) is applied only to the `running` status badge. This class is defined in `dashboard.css`.
- Token formatting uses a threshold: >= 1M shows `X.XM`, >= 1K shows `XXXK`, below 1K shows raw integer.
- Cost values are formatted as `$X.XX` with 2 decimal places.
- The `_format_duration` and `_format_tokens` helpers are module-level functions in `partials.py`, available for import by other modules.
