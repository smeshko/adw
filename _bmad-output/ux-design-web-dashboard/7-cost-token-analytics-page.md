# 7. Cost & Token Analytics Page

**Route:** `/analytics`
**Purpose:** Token usage and cost trends, breakdowns by project, run status, and activity patterns.
**PRD FRs:** FR32-35
**Design:** Industrial Brutalist Dark

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (global)                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ANALYTICS                       [7D] [30D] [90D] [ALL]    │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ TOTAL RUNS   │ SUCCESS RATE │ TOTAL TOKENS │TOTAL COST│  │
│  │    142       │     87%      │    1.2M      │  $48.20  │  │
│  │ ▲ +34%       │ ▲ +5pp       │ Avg 8.4K/run │ $0.34/run│  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
│                                                             │
│  // DAILY RUNS (full-width card)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ▅▇    ▅█                                            │   │
│  │  ██   ███                   stacked: green/red/gray  │   │
│  │  ███ ████ ▃                                          │   │
│  │  Mon Tue Wed Thu Fri Sat Sun                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ STATUS BREAKDOWN ────────┐ ┌─ COST BY PROJECT ───────┐  │
│  │                           │ │                          │  │
│  │    ╭───╮                  │ │ adw-core   ████████ $28  │  │
│  │   ╱87% ╲   ● Completed   │ │ dashboard  ████    $14   │  │
│  │   ╲    ╱   ● Failed      │ │ cli        ██       $5   │  │
│  │    ╰───╯   ● Aborted     │ │                          │  │
│  └───────────────────────────┘ └──────────────────────────┘  │
│                                                             │
│  // TOKEN USAGE (30 DAYS) (full-width card)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ▁▂▃▃▄▅▅▆▆▇▆▇▇▆▇█▇█▇█▇██▇▇▆▅▃▂  amber sparkline    │   │
│  │ Jan 13    Jan 20    Jan 27    Feb 3    Feb 11        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  // ACTIVITY HEATMAP (full-width card)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Mon [▪▪▪▪▪▪▪▪▪▪▪▪]                                  │   │
│  │ Tue [▪▪▪▪▪▪▪▪▪▪▪▪]   7 rows × 12 columns           │   │
│  │ Wed [▪▪▪▪▪▪▪▪▪▪▪▪]   heat-0..heat-4 color stops     │   │
│  │ Thu [▪▪▪▪▪▪▪▪▪▪▪▪]                                  │   │
│  │ Fri [▪▪▪▪▪▪▪▪▪▪▪▪]                                  │   │
│  │ Sat [▪▪▪▪▪▪▪▪▪▪▪▪]                                  │   │
│  │ Sun [▪▪▪▪▪▪▪▪▪▪▪▪]                                  │   │
│  │      W1 W2 W3 W4 W5 W6 W7 W8 W9 W10 W11 W12        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  FOOTER (global)                                            │
└─────────────────────────────────────────────────────────────┘
```

## Grid System

All cards below the summary strip live in a two-column CSS grid. Some cards span both columns.

```css
.analytics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 1.5rem;
}
.analytics-grid .full-width {
  grid-column: 1 / -1;
}
```

---

## 7.1 Time Range Button Group

A side-by-side button group replaces the previous `tabs-boxed` component. No DaisyUI tab classes are used.

**Typography:** Azeret Mono, 10px, weight 700, uppercase, `letter-spacing: 0.08em`.

**Structure:**
```html
<div class="period-toggle">
  <button class="period-btn" hx-get="/analytics?range=7d" hx-target="#analytics-content" hx-push-url="true">7D</button>
  <button class="period-btn active" hx-get="/analytics?range=30d" hx-target="#analytics-content" hx-push-url="true">30D</button>
  <button class="period-btn" hx-get="/analytics?range=90d" hx-target="#analytics-content" hx-push-url="true">90D</button>
  <button class="period-btn" hx-get="/analytics?range=all" hx-target="#analytics-content" hx-push-url="true">ALL</button>
</div>
```

**CSS:**
```css
.period-toggle {
  display: flex;
  gap: 0; /* buttons touch — no gap */
}
.period-btn {
  font-family: var(--font-display);   /* Azeret Mono */
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 6px 14px;
  background: var(--bg-card);
  color: var(--text-muted);           /* #666 */
  border: 2px solid #444;
  cursor: pointer;
  transition: all 0.1s;
}
.period-btn + .period-btn {
  border-left: none;                  /* adjacent buttons share border */
}
.period-btn:hover {
  color: var(--text-primary);         /* #E8E4DF */
}
.period-btn.active {
  background: var(--accent-red);      /* #C43018 */
  color: white;
  border-color: var(--accent-red);
}
```

**Placement:** Right-aligned inside the `.page-header` row, opposite the `<h1>ANALYTICS</h1>` heading. The page header has a 3px cream bottom border.

**Options:** 7D, 30D, 90D, ALL (default: 30D).

The server re-renders the entire `#analytics-content` fragment for the selected range. The active button receives the `.active` class.

---

## 7.2 Summary Numbers Strip

A full-width "big numbers" bar replacing discrete stat cards. This is a continuous horizontal strip divided into four equal cells.

**Layout:**
```html
<div class="big-numbers" id="analytics-summary">
  <div class="big-number">
    <div class="big-number-label">Total Runs</div>
    <div class="big-number-value">142</div>
    <div class="big-number-sub" style="color: var(--accent-green);">&#9650; +34% vs prior period</div>
  </div>
  <div class="big-number">
    <div class="big-number-label">Success Rate</div>
    <div class="big-number-value">87%</div>
    <div class="big-number-sub" style="color: var(--accent-green);">&#9650; +5pp vs prior period</div>
  </div>
  <div class="big-number">
    <div class="big-number-label">Total Tokens</div>
    <div class="big-number-value">1.2M</div>
    <div class="big-number-sub">Avg 8.4K per run</div>
  </div>
  <div class="big-number">
    <div class="big-number-label">Total Cost</div>
    <div class="big-number-value">$48.20</div>
    <div class="big-number-sub">Avg $0.34 per run</div>
  </div>
</div>
```

**CSS:**
```css
.big-numbers {
  display: flex;
  gap: 0;
  border: 2px solid var(--border-color);   /* cream outer border */
  box-shadow: var(--shadow-offset);        /* 4px 4px 0 #C43018 — red offset shadow */
  margin-bottom: 1.5rem;
}
.big-number {
  flex: 1;
  padding: 16px 18px;
  border-right: 1px solid #333;            /* 1px vertical dividers */
}
.big-number:last-child {
  border-right: none;
}
.big-number-label {
  font-family: var(--font-display);        /* Azeret Mono */
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 700;
  color: var(--text-muted);               /* #666 */
  margin-bottom: 4px;
}
.big-number-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 900;
  color: var(--text-primary);             /* #E8E4DF */
  line-height: 1.1;
}
.big-number-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  font-weight: 600;
}
```

**4 columns:**

| Cell | Label | Value | Sub-text |
|------|-------|-------|----------|
| Total Runs | `TOTAL RUNS` | Integer (e.g., `142`) | Trend vs prior period |
| Success Rate | `SUCCESS RATE` | Percentage (e.g., `87%`) | pp change vs prior period |
| Total Tokens | `TOTAL TOKENS` | Formatted (e.g., `1.2M`) | Average per run |
| Total Cost | `TOTAL COST` | `$X.XX` | Average per run |

**Trend sub-text coloring:**
- Positive/improving: `color: var(--accent-green)` (`#2ECC40`)
- Negative/declining: `color: var(--accent-red)` (`#C43018`)
- Neutral: default `--text-muted`

**HTMX:** The strip has `id="analytics-summary"` and is re-rendered as part of the `#analytics-content` fragment on range change.

---

## 7.3 Daily Runs Chart

A full-width card containing a stacked bar chart. Each bar represents one day, with segments for completed, failed, and aborted runs.

**Card:**
```html
<div class="card full-width">
  <div class="card-header"><h2>Daily Runs</h2></div>
  <div class="bar-chart">
    <!-- One bar-group per day -->
    <div class="bar-group">
      <div class="bar-stack">
        <div class="bar-segment bar-success" style="height: 35%"></div>
        <div class="bar-segment bar-failed" style="height: 5%"></div>
      </div>
      <span class="bar-label">Mon</span>
    </div>
    <!-- ... repeat for each day in range -->
  </div>
</div>
```

**Section header** uses the brutalist `h2` convention with a red `//` prefix:
```css
h2::before {
  content: '//';
  color: var(--accent-red);
  margin-right: 8px;
  font-weight: 900;
}
```

**CSS:**
```css
.card {
  background: var(--bg-card);              /* #1E1E1E */
  border: var(--border-harsh);             /* 2px solid #E8E4DF */
  box-shadow: var(--shadow-offset);        /* 4px 4px 0 #C43018 */
  padding: 18px 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 160px;
  padding-top: 10px;
  border-bottom: 2px solid #333;
}
.bar-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.bar-stack {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  width: 100%;
  height: 140px;
  gap: 1px;
}
.bar-segment {
  width: 100%;
  min-height: 1px;
}
.bar-success { background: var(--accent-green); }  /* #2ECC40 */
.bar-failed  { background: var(--accent-red); }     /* #C43018 */
.bar-aborted { background: #444; }
.bar-label {
  font-family: var(--font-display);        /* Azeret Mono */
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 6px;
}
```

- Chart height: 160px total, 140px for bar stacks
- Heights are server-calculated percentages relative to the max daily total
- Bar segments stack bottom-up: success, failed, aborted
- Day labels appear below each bar group (e.g., `MON`, `TUE`, etc.)

---

## 7.4 Status Breakdown (Donut Chart)

A card in the two-column grid containing a CSS-only donut ring chart with a legend.

**Structure:**
```html
<div class="card">
  <div class="card-header"><h2>Status Breakdown</h2></div>
  <div class="ring-chart-container">
    <div class="ring-chart" style="--completed-deg: 313; --failed-deg: 334;"></div>
    <div class="ring-legend">
      <div class="legend-item">
        <div class="legend-dot" style="background: var(--accent-green)"></div>
        <span>Completed <strong>124</strong> (87%)</span>
      </div>
      <div class="legend-item">
        <div class="legend-dot" style="background: var(--accent-red)"></div>
        <span>Failed <strong>12</strong> (8%)</span>
      </div>
      <div class="legend-item">
        <div class="legend-dot" style="background: #444"></div>
        <span>Aborted <strong>6</strong> (4%)</span>
      </div>
    </div>
  </div>
</div>
```

**CSS:**
```css
.ring-chart-container {
  display: flex;
  align-items: center;
  gap: 24px;
}
.ring-chart {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: conic-gradient(
    var(--accent-green) 0deg 313deg,        /* completed */
    var(--accent-red) 313deg 334deg,         /* failed */
    #444 334deg 360deg                       /* aborted */
  );
  position: relative;
  flex-shrink: 0;
}
.ring-chart::after {
  content: '87%';                            /* server-rendered percentage */
  position: absolute;
  inset: 20px;                               /* 20px inset creates the center cutout */
  background: var(--bg-card);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);          /* Azeret Mono */
  font-size: 22px;
  font-weight: 900;
  color: var(--text-primary);
}
.ring-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
}
```

- The `conic-gradient` degree stops are calculated server-side from run status counts
- The center cutout percentage (shown in `::after` content) is the success rate
- Legend items show colored 10px dots with label, count, and percentage

---

## 7.5 Cost by Project

A card in the two-column grid (beside the Status Breakdown) with a custom table showing per-project cost distribution.

**Structure:**
```html
<div class="card">
  <div class="card-header"><h2>Cost by Project</h2></div>
  <table class="cost-table">
    <thead>
      <tr><th>Project</th><th>Cost</th><th>Distribution</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>adw-core</td>
        <td style="font-family: var(--font-display);">$28.50</td>
        <td class="cost-bar-cell">
          <div class="cost-bar-track">
            <div class="cost-bar-fill" style="width: 59%"></div>
          </div>
        </td>
      </tr>
      <tr>
        <td>adw-dashboard</td>
        <td style="font-family: var(--font-display);">$14.20</td>
        <td class="cost-bar-cell">
          <div class="cost-bar-track">
            <div class="cost-bar-fill secondary" style="width: 29%"></div>
          </div>
        </td>
      </tr>
      <tr>
        <td>adw-cli</td>
        <td style="font-family: var(--font-display);">$5.50</td>
        <td class="cost-bar-cell">
          <div class="cost-bar-track">
            <div class="cost-bar-fill tertiary" style="width: 11%"></div>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

**CSS (custom table, not DaisyUI):**
```css
.cost-table {
  width: 100%;
  border-collapse: collapse;
}
.cost-table th {
  font-family: var(--font-display);        /* Azeret Mono */
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 700;
  color: var(--text-muted);
  padding: 8px 0;
  text-align: left;
  border-bottom: 2px solid #333;
}
.cost-table td {
  padding: 10px 0;
  font-size: 13px;
  border-bottom: 1px solid #2A2A2A;
}
.cost-bar-cell { width: 40%; }
.cost-bar-track {
  height: 12px;
  background: #2A2A2A;
  width: 100%;
}
.cost-bar-fill          { height: 100%; background: var(--accent-red); }     /* primary — #C43018 */
.cost-bar-fill.secondary { height: 100%; background: var(--accent-orange); } /* #D4602A */
.cost-bar-fill.tertiary  { height: 100%; background: var(--accent-amber); }  /* #D49A20 */
```

- Header row: 9px uppercase muted labels, 2px `#333` bottom border
- Body rows: project name (13px), cost in mono font, horizontal bar in a 12px-tall track (`#2A2A2A` background)
- Fill colors rotate: red (primary project), orange (secondary), amber (tertiary)
- Widths are server-calculated percentage of total cost

---

## 7.6 Token Usage Trend (Sparkline)

A full-width card showing a 30-day token usage sparkline using CSS flex bars.

**Structure:**
```html
<div class="card full-width">
  <div class="card-header"><h2>Token Usage (30 Days)</h2></div>
  <div class="token-trend">
    <!-- One bar per day, 30 bars total -->
    <div class="trend-bar" style="height: 15%"></div>
    <div class="trend-bar" style="height: 25%"></div>
    <!-- ... 28 more bars -->
  </div>
  <div class="trend-labels">
    <span class="trend-label">Jan 13</span>
    <span class="trend-label">Jan 20</span>
    <span class="trend-label">Jan 27</span>
    <span class="trend-label">Feb 3</span>
    <span class="trend-label">Feb 11</span>
  </div>
</div>
```

**CSS:**
```css
.token-trend {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 80px;
}
.trend-bar {
  flex: 1;
  background: var(--accent-amber);        /* #D49A20 */
  min-height: 2px;
  transition: background 0.1s;
}
.trend-bar:hover {
  background: var(--accent-cream);         /* #E8E4DF — turns cream on hover */
}
.trend-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}
.trend-label {
  font-family: var(--font-display);        /* Azeret Mono */
  font-size: 8px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
}
```

- 80px height, 2px gap between bars
- All bars are `--accent-amber`; hover turns to cream (`--accent-cream`)
- Date labels spaced evenly below the chart (Azeret Mono 8px muted)
- Bar heights are server-calculated percentages relative to the max daily token count

---

## 7.7 Activity Heatmap

A full-width card showing a 7-row by 12-column heatmap grid representing activity intensity across days of the week and weeks.

**Structure:**
```html
<div class="card full-width">
  <div class="card-header"><h2>Activity Heatmap</h2></div>
  <div class="heatmap">
    <div class="heatmap-row">
      <span class="heatmap-label">Mon</span>
      <div class="heatmap-cell heat-2"></div>
      <div class="heatmap-cell heat-3"></div>
      <!-- ... 10 more cells -->
    </div>
    <div class="heatmap-row">
      <span class="heatmap-label">Tue</span>
      <!-- ... 12 cells -->
    </div>
    <!-- ... Wed, Thu, Fri, Sat, Sun -->
  </div>
  <div class="heatmap-months">
    <span class="heatmap-month">W1</span>
    <span class="heatmap-month">W2</span>
    <!-- ... through W12 -->
  </div>
</div>
```

**CSS:**
```css
.heatmap {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.heatmap-row {
  display: flex;
  gap: 3px;
  align-items: center;
}
.heatmap-label {
  font-family: var(--font-display);        /* Azeret Mono */
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  width: 28px;
  text-align: right;
  margin-right: 4px;
}
.heatmap-cell {
  width: 18px;
  height: 18px;
  border: 1px solid #2A2A2A;
}

/* 5-stop heatmap scale */
.heat-0 { background: #1E1E1E; }          /* no activity */
.heat-1 { background: #3D1A12; }          /* low */
.heat-2 { background: #5C2518; }          /* moderate */
.heat-3 { background: #8A3520; }          /* high */
.heat-4 { background: var(--accent-red); } /* very high — #C43018 */

.heatmap-months {
  display: flex;
  gap: 3px;
  margin-left: 32px;                       /* aligns with cells, past the row labels */
  margin-top: 4px;
}
.heatmap-month {
  font-family: var(--font-display);
  font-size: 8px;
  font-weight: 600;
  color: var(--text-muted);
  width: 18px;
  text-align: center;
}
```

- 7 rows: Mon through Sun
- 12 columns: one per week in the selected range
- Row labels: Azeret Mono 8px weight 700 uppercase muted, 28px wide, right-aligned
- Each cell: 18x18px with a 1px `#2A2A2A` border
- 5-stop heat scale from `--bg-card` (no activity) through warm red tones to `--accent-red` (peak activity)
- Week labels below the grid, aligned to the cell columns

---

## Card Styling (shared)

All section cards in the analytics grid use the brutalist card pattern:

```css
.card {
  background: var(--bg-card);              /* #1E1E1E */
  border: var(--border-harsh);             /* 2px solid #E8E4DF (cream) */
  box-shadow: var(--shadow-offset);        /* 4px 4px 0 #C43018 (red offset) */
  padding: 18px 20px;
}
```

Section headers use the `// PREFIX` convention:

```css
h2 {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  display: inline-flex;
  align-items: center;
}
h2::before {
  content: '//';
  color: var(--accent-red);
  margin-right: 8px;
  font-weight: 900;
}
```

---

## HTMX Behavior

All HTMX patterns are preserved. The page uses server-side rendering with partial fragment swaps.

| Interaction | HTMX Attributes |
|-------------|-----------------|
| Time range change | `hx-get="/analytics?range={value}" hx-target="#analytics-content" hx-push-url="true"` |
| Page load | Server renders full page for the default range (30D) |
| Range switch | Server re-renders the `#analytics-content` fragment (summary strip + all cards) |

The active period button receives the `.active` class from the server on each response. No client-side JavaScript is needed for state management.

---

## Deferred Sections

The following sections from the original spec are **not present in the current brutalist design mocks** and are deferred to a future iteration:

- **By Model breakdown** (original 7.5) -- per-model token share and cost. Deferred per design scope.
- **Budget section** (original 7.6) -- monthly budget progress bar. FR35 was already flagged as first-to-defer in the PRD.
- **Detailed Breakdown Table** (original 7.7) -- per-project tabular totals. Superseded by the Cost by Project card (7.5) and the summary strip (7.2).

These can be re-introduced in a later phase without layout changes by adding additional `.full-width` cards to the `.analytics-grid`.

---

## Design Token Reference

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-void` | `#111111` | Page background |
| `--bg-card` | `#1E1E1E` | Card backgrounds, donut cutout |
| `--border-color` | `#E8E4DF` | Cream card borders |
| `--border-harsh` | `2px solid #E8E4DF` | Card border shorthand |
| `--shadow-offset` | `4px 4px 0 #C43018` | Red offset shadow on cards/strip |
| `--accent-red` | `#C43018` | Active button, failed bars, heat-4, cost fill primary |
| `--accent-orange` | `#D4602A` | Cost fill secondary |
| `--accent-amber` | `#D49A20` | Token trend bars, cost fill tertiary |
| `--accent-green` | `#2ECC40` | Success bars, positive trends, donut completed |
| `--accent-cream` | `#E8E4DF` | Hover state for trend bars |
| `--text-primary` | `#E8E4DF` | Big number values, headings |
| `--text-muted` | `#666` | Labels, sub-text, day labels |
| `--font-display` | `Azeret Mono` | All labels, values, headings |
| `--font-body` | `Inconsolata` | Body text |

---
