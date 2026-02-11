# 4. Overview Page

**Route:** `/`
**Purpose:** Hub page. Compact previews of every data domain. Every section is a doorway to a full page.
**PRD FRs:** FR1-7, FR8-11 (partial)

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (global)                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│  │ Total  │ │Success │ │  Avg   │ │ Tokens │ │  Cost  │   │
│  │ Runs   │ │ Rate   │ │Duration│ │  Used  │ │  Est.  │   │
│  │  142   │ │ 94.2%  │ │ 5m 12s │ │  2.4M  │ │ $18.30 │   │
│  │+12 /wk │ │ ▲ 2.1% │ │ ▼ 18s  │ │340K/wk │ │$4.20/wk│   │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                             │
│  ACTIVE RUNS (2)                                            │
│  ┌──────────────────────────────┐ ┌────────────────────────┐│
│  │ my-api                       │ │ sdk                    ││
│  │ "Add auth middleware"        │ │ "Fix config loader"    ││
│  │ [✓Plan]━[●Build]━[ ]━[ ]━[ ]│ │ [✓]━[✓]━[●Valid]━[ ]━[ ││
│  │ Started 2m ago               │ │ Started 45s ago        ││
│  └──────────────────────────────┘ └────────────────────────┘│
│                                                             │
│  RECENT RUNS                                   View All →   │
│  ┌─────────┬──────────┬────────┬─────────┬────────────┐    │
│  │ Project │ Feature  │ Status │Duration │ Started    │    │
│  ├─────────┼──────────┼────────┼─────────┼────────────┤    │
│  │ my-api  │ Add CORS │ ✓ done │ 4m 12s  │ 25m ago    │    │
│  │ sdk     │ Retry lo │ ✗ fail │ 2m 01s  │ 1h ago     │    │
│  │ dashb.. │ Dark mod │ ✓ done │ 6m 44s  │ 2h ago     │    │
│  │ my-api  │ Rate lim │ ✓ done │ 3m 55s  │ 3h ago     │    │
│  │ sdk     │ Refactor │ ✓ done │ 7m 20s  │ 5h ago     │    │
│  └─────────┴──────────┴────────┴─────────┴────────────┘    │
│                                                             │
│  PROJECTS                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ my-api       │ │ sdk          │ │ dashboard    │       │
│  │ 74 runs      │ │ 43 runs      │ │ 25 runs      │       │
│  │ 91% success  │ │ 88% success  │ │ 96% success  │       │
│  │ $9.52 spent  │ │ $5.49 spent  │ │ $3.29 spent  │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                             │
│  COST THIS WEEK                            View Details →   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  $4.20 total  ·  340K tokens  ·  ▁▂▃▅▇█▅ daily      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  FOOTER (global)                                            │
└─────────────────────────────────────────────────────────────┘
```

## 4.1 Stat Cards Row

**DaisyUI:** `stats stats-horizontal shadow` wrapping multiple `stat` blocks.

Each stat card contains:
- `stat-title` — Label (e.g., "Total Runs")
- `stat-value` — Large number (`text-2xl font-mono`)
- `stat-desc` — Trend indicator (e.g., "+12 this week", "▲ 2.1%")

**Trend indicators:**
- Positive trend: green text, `▲` prefix
- Negative trend: red text, `▼` prefix
- Neutral: default text color

**HTMX:** The entire stats row has `id="stats-row"` and can be refreshed out-of-band when other sections poll.

**Stats displayed (5 cards):**

| Stat | Value format | Trend comparison |
|------|-------------|-----------------|
| Total Runs | Integer | vs. previous week |
| Success Rate | Percentage (1 decimal) | vs. previous week (percentage points) |
| Avg Duration | `Xm Ys` | vs. previous week |
| Tokens Used | Formatted: `2.4M`, `340K` | This week total |
| Estimated Cost | `$X.XX` | This week total |

## 4.2 Active Runs Section

**Visibility:** Only rendered when active runs exist. Server returns an empty fragment when no runs are active.

**DaisyUI:** Each active run is a `card card-compact card-bordered` with a left border accent (`border-l-4 border-warning`).

**Card contents:**
- Project name (`font-semibold text-sm`)
- Feature description (`text-sm text-base-content/70`, truncated to ~40 chars)
- Phase pipeline: mini horizontal steps indicator
- Elapsed time (`font-mono text-xs`)

**Phase pipeline (mini version):**
Five compact nodes representing Plan → Build → Validate → Document → Ship.
- Completed: `step-success` (filled green)
- Active: `step-warning` with a CSS pulsing animation (`animate-pulse`)
- Pending: `step` (unfilled/grey)

Uses DaisyUI `steps steps-horizontal` at a compact size.

**Layout:** Horizontal card row using CSS `flex gap-4 flex-wrap`. Cards take equal width up to 2-3 per row depending on viewport.

**HTMX:**
- Section `id="active-runs"`
- `hx-get="/partials/active-runs" hx-trigger="every 3s" hx-swap="outerHTML"`
- When a run completes, the card disappears on next poll and stats update via `hx-swap-oob`

**Click behavior:** Entire card is clickable → `hx-get="/runs/{id}" hx-target="#main" hx-push-url="/runs/{id}"`

## 4.3 Recent Runs Section

**Header:** "Recent Runs" with a "View All →" link on the right.
- "View All" → `hx-get="/runs" hx-target="#main" hx-push-url="/runs"`

**DaisyUI:** `table table-sm` inside a `card card-compact`.

**Table columns:**

| Column | Width | Content | Style |
|--------|-------|---------|-------|
| Project | auto | Project name | `text-sm` |
| Feature | flexible | Description, truncated | `text-sm text-base-content/70 truncate max-w-[200px]` |
| Status | narrow | Icon + label | `badge badge-sm badge-{status}` |
| Duration | narrow | `Xm Ys` | `font-mono text-xs` |
| Started | narrow | Relative time | `text-xs text-base-content/50` |

**Rows:** 5 most recent runs. No pagination here — that's what the full Runs List page is for.

**Click behavior:** Each row is clickable → navigates to `/runs/{id}`.

**HTMX:** `hx-trigger="every 15s"` to refresh the table body. Slower polling than active runs since recent runs change less frequently.

## 4.4 Project Breakdown Section

**DaisyUI:** Small `card card-compact` for each registered project, laid out in a `flex gap-3 flex-wrap` row.

**Card contents:**
- Project name (`font-semibold text-sm`)
- Run count (`text-xs`)
- Success rate (`text-xs`, color-coded: green ≥80%, yellow 50-79%, red <50%)
- Total cost (`font-mono text-xs`)

**Click behavior:** Clicking a project card sets the global project filter.
- `hx-get="/?project={name}" hx-target="#main" hx-push-url="/?project={name}"`
- This reloads the entire overview scoped to that project
- The project filter dropdown in the header also updates (via `hx-swap-oob`)

**Visual hint:** When a project filter is active, the selected project card has a `ring ring-primary` outline and the section title shows "Projects — Filtered: {name}" with a clear (×) button.

## 4.5 Cost Summary Strip

A compact, single-line preview of cost/token data with a link to the full analytics page.

**DaisyUI:** `card card-compact` with horizontal content layout.

**Content:**
- Weekly total cost (`font-mono font-semibold`)
- Weekly total tokens (formatted)
- Mini CSS bar chart (7 bars, one per day, using inline `div` elements with `height` based on daily token count)
- "View Details →" link → `/analytics`

**HTMX:** Static — refreshes only when the overview page reloads. No independent polling.

## 4.6 New Run Button

A floating action button or a prominent button in the header area.

**Placement:** Top-right of the overview content area, next to the section title or below the stat cards.

**DaisyUI:** `btn btn-primary btn-sm` with a `+` icon.

**Behavior:** Opens the New Run modal (see section 8).

---
