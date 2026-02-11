# Analytics Page: Time Range Tabs & Stat Cards

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/templates/partials/analytics.html`, `src/adw/dashboard/templates/pages/analytics.html`

## Overview

The analytics page provides aggregate token and cost statistics for selectable time ranges with trend indicators. It introduces the first analytics view in Epic 5, using a period-over-period delta calculation pattern and bookmarkable HTMX tab navigation.

## What Was Built

- Analytics page at `/analytics` with "Token & Cost Analytics" title
- Time range tabs (7d, 30d, 90d, All time) using DaisyUI `tabs-box`
- 4 stat cards: Total Tokens, Total Cost, Avg Tokens/Run, Total Runs
- Delta indicators comparing current period to previous equivalent period
- Empty state for periods with no data
- Project filter preservation across range changes

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py`: Route handler with `_RANGE_DAYS` mapping and range normalization
- `src/adw/dashboard/partials.py`: `build_analytics_context()` helper with delta calculations
- `src/adw/dashboard/templates/partials/analytics.html`: Full analytics partial with tabs, stat cards, empty state
- `src/adw/dashboard/templates/pages/analytics.html`: Page wrapper extending base template

### Key Patterns

- **Delta Calculation via Subtraction**: Since `get_global_stats()` only supports a `since` parameter (no `until`), previous period stats are computed by fetching stats for 2x the selected range and subtracting the current period. For example, to get "previous 7 days", fetch stats since 14 days ago and subtract stats since 7 days ago.

- **Range Normalization**: Invalid range values are silently normalized to the default `"7d"`. The `_RANGE_DAYS` dict maps range keys to day counts (`None` = all time).

- **All-Time Has No Deltas**: When `range=all`, there is no previous period to compare against. All delta values are zero and the template shows "No change vs prev period".

- **Bookmarkable HTMX Tabs**: Each tab uses `hx-push-url` to update the browser URL with `?range=` and `?project=` params, making the selected range bookmarkable. The HTMX target is `#analytics` with `outerHTML` swap for a full partial replacement.

### Code Examples

```python
# Delta calculation pattern (partials.py)
# 1. Fetch current period stats
current_stats = stats_aggregator.get_global_stats(since=now - timedelta(days=7))

# 2. Fetch combined (current + previous) stats
combined_stats = stats_aggregator.get_global_stats(since=now - timedelta(days=14))

# 3. Derive previous period by subtraction
prev_total_runs = combined_stats.total_runs - current_stats.total_runs
prev_total_tokens = combined_stats.tokens.total_tokens - current_stats.tokens.total_tokens

# 4. Compute deltas
runs_delta = current_stats.total_runs - prev_total_runs
```

```html
{# Stat card with delta indicator (analytics.html) #}
<div class="stat bg-base-100 shadow rounded-box flex-1 min-w-[180px]">
  <div class="stat-title">Total Runs</div>
  <div class="stat-value text-2xl font-mono">{{ analytics_total_runs }}</div>
  <div class="stat-desc">
    {% if runs_delta > 0 %}
      <span class="text-success">&#x25B2; +{{ runs_delta }} vs prev period</span>
    {% elif runs_delta < 0 %}
      <span class="text-error">&#x25BC; {{ runs_delta | abs }} vs prev period</span>
    {% else %}
      <span>No change vs prev period</span>
    {% endif %}
  </div>
</div>
```

## How to Use

1. Navigate to `/analytics` or click "Analytics" in the dashboard nav
2. Select a time range tab (7d, 30d, 90d, All time)
3. View stat cards with delta indicators showing trend vs previous period
4. Use the global project filter to scope analytics to a specific project
5. Bookmark the URL to return to a specific range/project combination

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `range` | Query param | `7d` | Time range: `7d`, `30d`, `90d`, `all` |
| `project` | Query param | `""` | Project filter (empty = all projects) |

## Notes

- The `_RANGE_DAYS` dict is the single source of truth for valid range values and their day counts
- `max(0, ...)` guards prevent negative values from rounding/timing edge cases in delta subtraction
- The `_format_tokens()` helper from `partials.py` is reused for consistent token formatting (e.g., "2.4M", "15K")
- Future analytics features (charts, breakdowns) should follow the same `build_analytics_context()` pattern and extend the context dict
