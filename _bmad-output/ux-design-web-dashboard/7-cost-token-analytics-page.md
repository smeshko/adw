# 7. Cost & Token Analytics Page

**Route:** `/analytics`
**Purpose:** Token usage and cost trends, breakdowns by project, phase, and model.
**PRD FRs:** FR32-35

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (global)                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Token & Cost Analytics                                     │
│  [7 days]  [30 days]  [90 days]  [All time]                │
│                                                             │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐              │
│  │ Tokens │ │  Cost  │ │Avg/Run │ │  Runs  │              │
│  │  2.4M  │ │ $18.30 │ │ 16.9K  │ │  142   │              │
│  │340K/wk │ │$4.20/wk│ │ ▼ 1.2K │ │ +12/wk │              │
│  └────────┘ └────────┘ └────────┘ └────────┘              │
│                                                             │
│  DAILY USAGE                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │     ▁▃    ▅▇                                         │   │
│  │    ▃██   ▇██                                         │   │
│  │   ▅███  ████ ▃                                       │   │
│  │  ▇████ █████▅█                                       │   │
│  │  █████ ██████████                                    │   │
│  │  M T W T F S S   M T W T F S S                      │   │
│  │                                                      │   │
│  │  ■ Input tokens   ■ Output tokens                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ BY PROJECT ─────────────┐ ┌─ BY PHASE ──────────────┐  │
│  │                          │ │                          │  │
│  │ my-api    ████████  52%  │ │ Build    █████████  62%  │  │
│  │ sdk       █████     30%  │ │ Plan     ███       18%  │  │
│  │ dashboard ███       18%  │ │ Validate ██        12%  │  │
│  │                          │ │ Document █          5%  │  │
│  │                          │ │ Ship     ▏          3%  │  │
│  └──────────────────────────┘ └──────────────────────────┘  │
│                                                             │
│  ┌─ BY MODEL ───────────────────────────────────────────┐   │
│  │                                                      │   │
│  │ claude-sonnet   ██████████████  82%   $15.01         │   │
│  │ claude-haiku    ████             18%   $3.29          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ BUDGET ─────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │ Monthly budget: $50.00                               │   │
│  │ ████████████████████░░░░░░░░░░  $18.30 / $50.00     │   │
│  │ 36.6% used · 20 days remaining                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  DETAILED BREAKDOWN                                         │
│  ┌──────────┬──────┬────────┬────────┬─────────┐           │
│  │ Project  │ Runs │ Tokens │  Cost  │ Avg/Run │           │
│  ├──────────┼──────┼────────┼────────┼─────────┤           │
│  │ my-api   │  74  │ 1.25M  │  $9.52 │  16.9K  │           │
│  │ sdk      │  43  │  720K  │  $5.49 │  16.7K  │           │
│  │ dashboard│  25  │  430K  │  $3.29 │  17.2K  │           │
│  └──────────┴──────┴────────┴────────┴─────────┘           │
│                                                             │
│  FOOTER (global)                                            │
└─────────────────────────────────────────────────────────────┘
```

## 7.1 Time Range Tabs

**DaisyUI:** `tabs tabs-boxed`

| Tab | Query Param | Default |
|-----|------------|---------|
| 7 days | `?range=7d` | ✓ Default |
| 30 days | `?range=30d` | |
| 90 days | `?range=90d` | |
| All time | `?range=all` | |

Each tab: `hx-get="/analytics?range={value}" hx-target="#analytics-content" hx-push-url`

The active tab gets `tab-active`.

## 7.2 Stat Cards

Same pattern as overview stat cards but scoped to the selected time range.

| Stat | Value |
|------|-------|
| Total Tokens | Formatted (e.g., "2.4M") |
| Total Cost | `$X.XX` |
| Avg Tokens/Run | Formatted |
| Total Runs | Integer |

## 7.3 Daily Usage Chart (CSS-Only)

A bar chart rendered entirely with CSS. No JavaScript charting library.

**Structure:**
```html
<div class="chart-daily flex items-end gap-1 h-40">
  <!-- One bar per day -->
  <div class="chart-bar flex flex-col justify-end w-full">
    <div class="bg-primary" style="height: 62%"></div>      <!-- output tokens -->
    <div class="bg-primary/40" style="height: 38%"></div>    <!-- input tokens -->
    <span class="text-xs text-center mt-1">M</span>
  </div>
  <!-- ... repeat for each day -->
</div>
```

- Each bar is a flex column with two stacked segments (input + output tokens)
- Height percentages are calculated server-side relative to the max daily value
- Day labels below each bar
- Legend below the chart: colored squares + labels

**Responsive:** The chart uses `flex` with equal-width items. On wider screens, bars have spacing; on narrower screens, they compress.

## 7.4 Breakdown Panels

**Side-by-side layout:** Two `card card-bordered` panels in a `grid grid-cols-1 lg:grid-cols-2 gap-4` container.

### By Project

Horizontal bar chart, each row:
```html
<div class="flex items-center gap-2 mb-2">
  <span class="w-24 text-sm truncate">my-api</span>
  <div class="flex-1 bg-base-300 rounded-full h-4">
    <div class="bg-primary rounded-full h-4" style="width: 52%"></div>
  </div>
  <span class="w-12 text-right text-sm font-mono">52%</span>
</div>
```

- DaisyUI `progress` component could also work, but custom `div` gives more control
- Clickable project names set the global project filter
- Percentages are of total tokens in the selected time range

### By Phase

Same horizontal bar chart pattern but for phases:
- Plan, Build, Validate, Document, Ship
- Color-coded bars could use distinct colors per phase for visual variety
- Not clickable (no "phase filter" concept)

## 7.5 By Model

Same pattern as the other breakdowns. Shows each LLM model used with its token share and absolute cost.

## 7.6 Budget Section

**DaisyUI:** `progress progress-primary w-full` inside a `card card-bordered`.

- Shows a progress bar of current spend vs. configured budget
- Budget value is configurable (stored in project config or a dashboard setting)
- Color changes based on usage: `progress-primary` (<70%), `progress-warning` (70-90%), `progress-error` (>90%)
- Text shows: `${spent} / ${budget}` + percentage + estimated days remaining in period

**Note:** FR35 is flagged as first-to-defer in the PRD. This section can be omitted from the initial build and added later without layout changes.

## 7.7 Detailed Breakdown Table

**DaisyUI:** `table table-sm table-zebra`

Shows per-project totals for the selected time range. Same columns as the overview project cards but in tabular form with more precision.

---
