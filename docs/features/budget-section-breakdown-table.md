# Budget Section & Detailed Breakdown Table

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/partials.py`, `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/analytics.html`

## Overview

Adds a monthly budget progress card with color-coded thresholds and a per-project detailed breakdown table with server-side sortable columns to the analytics page. The budget feature is opt-in via an environment variable, and the table sorting uses HTMX with a `?sort=` query parameter — no JavaScript required.

## What Was Built

- Budget progress card with DaisyUI `progress` bar, spent/budget text, percentage, and estimated days remaining
- Color-coded progress bar: `progress-primary` (<70%), `progress-warning` (70–90%), `progress-error` (>90%)
- Graceful hiding of budget section when `ADW_MONTHLY_BUDGET` is not configured
- Detailed breakdown table (`table table-sm table-zebra`) with 5 columns: Project, Runs, Tokens, Cost, Avg Tokens/Run
- Server-side sorting via `?sort=` query parameter with ascending/descending toggle per column
- Sort direction indicators (▲/▼) on active column headers
- `analytics_url` Jinja2 macro that preserves `range`, `project`, and `sort` params across all HTMX interactions
- Sort parameter validation via whitelist (`_VALID_SORTS` set in routes.py)

## Technical Implementation

### Key Files

- `src/adw/dashboard/partials.py`: Budget calculation (thresholds, days remaining) and breakdown table data generation with sort logic, all within `build_analytics_context()`
- `src/adw/dashboard/routes.py`: Added `sort` query parameter with whitelist validation (`_VALID_SORTS`) and default `"cost_desc"`
- `src/adw/dashboard/templates/partials/analytics.html`: Budget card HTML, breakdown table with sortable headers, `analytics_url` macro

### Key Patterns

- **Environment-Variable-Gated Feature**: The budget section is controlled by `ADW_MONTHLY_BUDGET` env var. When absent or invalid, `has_budget` is `False` and the template `{% if has_budget %}` guard hides the entire card. No empty card is rendered.

- **Progress Bar Color Thresholds**: Three tiers mapped to DaisyUI classes — `progress-primary` (normal, <70%), `progress-warning` (caution, 70–90%), `progress-error` (critical, >90%). The percentage can exceed 100% for over-budget scenarios; `budget_days_remaining` is clamped to 0.

- **Days Remaining Estimation**: Calculated as `int((budget_amount - total_cost) / daily_avg_cost)` where `daily_avg_cost = total_cost / days` for the selected range. Returns `None` when cost is zero (avoiding division by zero) and `0` when over budget.

- **Server-Side Sort with HTMX**: Each column header is an `<a>` with `hx-get` pointing to the analytics URL with a toggled `?sort=` parameter. Clicking a sorted column flips direction (desc→asc); clicking a different column defaults to desc (except Project which defaults to asc). The entire `#analytics` partial is swapped via `outerHTML`.

- **Sort Parameter Whitelist**: The `_VALID_SORTS` set in `routes.py` contains all 10 valid sort values. Invalid sort params silently default to `"cost_desc"`, preventing injection.

- **`analytics_url` Jinja2 Macro**: A macro defined at the top of `analytics.html` that builds a URL preserving `range`, `project`, and `sort` params. Used by time range tabs, sort headers, and project breakdown links. This replaces the previously duplicated inline URL construction.

### Code Examples

```python
# Budget calculation (partials.py)
budget_percentage = round((total_cost / budget_amount) * 100, 1)

if budget_percentage > 90:
    budget_progress_class = "progress-error"
elif budget_percentage >= 70:
    budget_progress_class = "progress-warning"
# else: stays "progress-primary" (default)
```

```python
# Sort logic (partials.py)
sort_key_map = {"cost": "cost_raw", "tokens": "tokens_raw", "runs": "runs_raw",
                "project": "name", "avg": "avg_tokens_raw"}
parts = sort.rsplit("_", 1)
col, direction = parts[0], parts[1]
breakdown_table.sort(key=lambda r: r[sort_key_map[col]], reverse=(direction == "desc"))
```

```html
{# analytics_url macro (analytics.html) #}
{% macro analytics_url(range=selected_range, sort=breakdown_sort) %}
/analytics?range={{ range }}{% if selected_project %}&project={{ selected_project | urlencode }}{% endif %}&sort={{ sort }}
{%- endmacro %}
```

## How to Use

1. Set `ADW_MONTHLY_BUDGET=100.00` (or any positive float) as an environment variable to enable budget tracking
2. Navigate to `/analytics` — the budget card appears above the breakdown table
3. The progress bar color reflects current spend level against the budget
4. Scroll down to the "Detailed Breakdown" table to see per-project metrics
5. Click any column header to sort; click again to reverse sort direction
6. Sort selection is preserved when switching time ranges or project filters

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ADW_MONTHLY_BUDGET` | Env var | Not set | Monthly budget in dollars (e.g., `100.00`). Budget section hidden when absent. |
| `sort` | Query param | `cost_desc` | Sort order for breakdown table. Valid: `cost_desc`, `cost_asc`, `tokens_desc`, `tokens_asc`, `runs_desc`, `runs_asc`, `project_desc`, `project_asc`, `avg_desc`, `avg_asc` |
| `range` | Query param | `7d` | Time range (inherited from analytics page) |
| `project` | Query param | `""` | Project filter (inherited from analytics page) |

## Notes

- Budget days remaining uses the selected time range's daily average, so switching from 7d to 90d may produce different estimates
- Over-budget scenarios show percentage >100% and days remaining = 0; the progress bar fills completely with `progress-error`
- The `analytics_url` macro replaced all inline URL construction in analytics.html, ensuring consistent parameter preservation
- Sort parameter is validated server-side; invalid values silently fall back to `cost_desc`
- The breakdown table reuses `_format_tokens()` from partials.py and `calculate_cost()` from StatsAggregator for consistent formatting
