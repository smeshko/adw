# Daily Usage Chart & Breakdown Panels

**Date:** 2026-02-12
**Related Files:** `src/adw/core/stats_aggregator.py`, `src/adw/core/phase_runner.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/templates/partials/analytics.html`, `src/adw/dashboard/static/dashboard.css`

## Overview

Adds a CSS-only stacked bar chart showing daily token usage (input vs output) and three breakdown panels (By Project, By Phase, By Model) to the analytics page. All chart heights and percentages are computed server-side — no JavaScript charting library is used.

## What Was Built

- CSS-only stacked bar chart with output tokens (solid) and input tokens (translucent) per day
- "By Project" breakdown panel with clickable project names that set the global project filter via HTMX
- "By Phase" breakdown panel showing canonical phases (Plan, Build, Validate, Document, Ship) in fixed order
- "By Model" breakdown panel showing each LLM model's token share and absolute cost
- `get_phase_breakdown()` and `get_model_breakdown()` aggregation methods on StatsAggregator
- Input/output token split in `get_daily_token_counts()` return data
- `model` field added to LLM response files via `_capture_artifacts()`

## Technical Implementation

### Key Files

- `src/adw/core/stats_aggregator.py`: New `get_phase_breakdown()` and `get_model_breakdown()` methods; updated `get_daily_token_counts()` to return input/output split
- `src/adw/core/phase_runner.py`: Passes `model` parameter to `_capture_artifacts()`, stored in LLM response JSON
- `src/adw/dashboard/partials.py`: Extended `build_analytics_context()` with daily chart bars, project/phase/model breakdown computation
- `src/adw/dashboard/templates/partials/analytics.html`: Chart and breakdown panel HTML templates
- `src/adw/dashboard/static/dashboard.css`: `.chart-daily` and `.chart-bar` CSS rules

### Key Patterns

- **CSS-Only Vertical Bar Chart**: Each bar is a flex column (`flex-col justify-end`) with two `<div>` segments. Heights are set via inline `style="height: N%"` where N is computed server-side relative to the max daily value. The container uses `flex items-end gap-1 h-40`. This avoids any JavaScript charting dependency.

- **Server-Side Height Normalization**: The tallest bar day gets heights summing to exactly 100% (with rounding correction: `inp_h = 100 - out_h` when `total == max_daily`). All other bars are proportional.

- **Canonical Phase Ordering**: Phase breakdown always shows phases in the fixed order `[plan, build, validate, document, ship]` regardless of data ordering. Only phases with tokens > 0 are displayed. The percentage denominator sums only canonical phases, excluding any non-standard phases.

- **Horizontal Bar Rows**: Both project and phase breakdowns use the same visual pattern: a label, a `bg-base-300` track with `bg-primary` fill bar, and a percentage label. Width is set via `style="width: N%"`.

- **Model Cost Calculation**: Each model's cost is computed individually using `stats_aggregator.calculate_cost()` with a `TokenUsage` instance, ensuring model-specific pricing is applied if configured.

- **Fallback for Pre-Existing Data**: LLM response files created before this feature lack a `model` field. `get_model_breakdown()` falls back to `"default"` for these files.

### Code Examples

```python
# Server-side bar height computation (partials.py)
max_daily = max((d["input_tokens"] + d["output_tokens"] for d in daily_counts), default=0)
for d in daily_counts:
    out_h = int((d["output_tokens"] / max_daily) * 100)
    inp_h = int((d["input_tokens"] / max_daily) * 100)
    if d["input_tokens"] + d["output_tokens"] == max_daily:
        inp_h = 100 - out_h  # rounding correction for tallest bar
```

```html
{# CSS-only stacked bar (analytics.html) #}
<div class="chart-daily flex items-end gap-1 h-40">
  {% for bar in daily_chart_bars %}
  <div class="chart-bar flex flex-col justify-end w-full">
    <div class="bg-primary rounded-t" style="height: {{ bar.output_height }}%"></div>
    <div class="bg-primary/40" style="height: {{ bar.input_height }}%"></div>
  </div>
  {% endfor %}
</div>
```

## How to Use

1. Navigate to `/analytics` and select a time range
2. The daily usage chart renders below the stat cards showing input/output token stacks per day
3. The "By Project" panel shows horizontal bars — click a project name to filter analytics
4. The "By Phase" panel shows token distribution across pipeline phases
5. The "By Model" panel shows each LLM model's share with absolute cost

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `range` | Query param | `7d` | Time range for chart data (7d, 30d, 90d, all) |
| `project` | Query param | `""` | Project filter (empty = all projects) |

## Notes

- `get_phase_breakdown()` reads `phase_tokens` from `context.json` files; runs without `context.json` are silently skipped
- `get_model_breakdown()` reads `model` from LLM response JSON files; pre-existing files without `model` fall back to `"default"`
- Phase breakdown percentage denominator only sums canonical phases, so non-standard phases don't dilute the percentages
- The daily chart uses `min-height: 2px` on bar segments via CSS to ensure zero-value days still show a sliver
- Day labels use abbreviated weekday names (Mon, Tue, etc.) derived from `date.weekday()`
