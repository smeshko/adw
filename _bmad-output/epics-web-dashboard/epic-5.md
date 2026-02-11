# Epic 5: Cost & Token Analytics

User can analyze token usage and costs with time-range filtering, daily usage charts, and breakdowns by project, phase, and model — providing full visibility into ADW resource consumption.

**FRs covered:** FR32-FR38 (7 FRs)

### Story 5.1: Analytics Page Layout with Time Range & Stat Cards

As a developer,
I want to view aggregate token and cost statistics for selectable time ranges with trend indicators,
So that I can understand my ADW resource consumption patterns over different periods.

**Acceptance Criteria:**

**Given** the user navigates to `/analytics`
**When** the page renders
**Then** the analytics page displays with dual-response pattern and title "Token & Cost Analytics"
**And** the URL is bookmarkable (e.g., `/analytics?range=30d`) (FR52)

**Given** the analytics page is displayed
**When** the time range tabs render
**Then** DaisyUI `tabs tabs-boxed` are shown with options: 7 days (`?range=7d`, default), 30 days (`?range=30d`), 90 days (`?range=90d`), All time (`?range=all`) (FR32, UX §7.1)
**And** the active tab shows `tab-active`
**And** clicking a tab triggers `hx-get="/analytics?range={value}" hx-target="#analytics-content" hx-push-url` for a partial swap without full page reload (FR32)

**Given** a time range is selected
**When** the stat cards render
**Then** 4 stat cards are displayed using the same `stats stats-horizontal shadow` pattern as the overview (UX §7.2):
| Stat | Value Format | Delta |
|------|-------------|-------|
| Total Tokens | Formatted (e.g., "2.4M") | vs. previous period |
| Total Cost | `$X.XX` | vs. previous period |
| Avg Tokens/Run | Formatted (e.g., "16.9K") | vs. previous period |
| Total Runs | Integer | vs. previous period |
**And** each card shows a delta indicator comparing to the previous equivalent period (FR33)
**And** positive deltas show green `▲`, negative show red `▼`

**Given** the user changes the time range
**When** a different tab is clicked
**Then** all analytics content (stat cards, charts, breakdowns, table) refresh via HTMX partial swap of `#analytics-content` (FR32)
**And** the URL updates to reflect the new range

**Given** no analytics data exists for the selected time range
**When** the content area renders
**Then** an empty state message is shown: "No data for the selected period. Try a wider time range." (UX §11.1)

**Given** the global project filter in the header is set
**When** the analytics page loads
**Then** all analytics data is scoped to the filtered project
**And** the `?project=` param is preserved alongside `?range=`

**Technical notes:**
- Route: `/analytics` with query params: `?range=`, `?project=`
- Analytics content partial: `/analytics?range=...` returns `#analytics-content` fragment
- No independent polling on this page — manual range change only (UX §9.3)
- Server-side calculations for delta comparisons (current period vs. previous equivalent period)

---

### Story 5.2: Daily Usage Chart & Breakdown Panels

As a developer,
I want to see a daily token usage chart and breakdowns by project, phase, and model,
So that I can identify usage trends, understand which projects consume the most resources, and see which phases are most expensive.

**Acceptance Criteria:**

**Given** the analytics page is displayed with data
**When** the daily usage chart renders
**Then** a CSS-only stacked bar chart is displayed — no JavaScript charting library (FR34, UX §7.3)
**And** the chart uses `flex items-end gap-1 h-40` with one bar per day
**And** each bar is a flex column with two stacked segments: output tokens (`bg-primary`) and input tokens (`bg-primary/40`) (FR34)
**And** height percentages are calculated server-side relative to the max daily value
**And** day labels (M, T, W, etc.) appear below each bar
**And** a legend below the chart shows: colored squares for "Input tokens" and "Output tokens"

**Given** the daily chart at different widths
**When** the viewport is narrow (1024-1279px)
**Then** bars compress proportionally using `flex` with equal-width items (UX §7.3, §12)

**Given** the analytics page is displayed
**When** the breakdown panels render
**Then** two panels appear side-by-side in a `grid grid-cols-1 lg:grid-cols-2 gap-4` container (UX §7.4)
**And** at widths below `lg` (1024px), panels stack vertically (UX §12)

**Given** the "By Project" breakdown panel renders
**When** data is available
**Then** it shows a `card card-bordered` with horizontal bar rows for each project (FR35)
**And** each row: project name (`w-24 text-sm truncate`), bar (`bg-primary rounded-full h-4` inside `bg-base-300 rounded-full h-4`), percentage (`w-12 text-right text-sm font-mono`)
**And** percentages are of total tokens in the selected time range (UX §7.4)

**Given** a project name in the "By Project" breakdown
**When** the user clicks it
**Then** the global project filter is set and the entire analytics page reloads scoped to that project (FR36)

**Given** the "By Phase" breakdown panel renders
**When** data is available
**Then** it shows the same horizontal bar pattern for phases: Plan, Build, Validate, Document, Ship (FR37)
**And** phase bars are not clickable (no "phase filter" concept) (UX §7.4)

**Given** the "By Model" breakdown renders
**When** data is available
**Then** it shows each LLM model used with its token share percentage and absolute cost (`$X.XX`) (UX §7.5)
**And** uses the same horizontal bar pattern as other breakdowns

**Technical notes:**
- CSS-only charts: server-rendered bar charts via CSS flex/height — no JS charting library (Architecture decision)
- Server calculates all percentages and bar heights
- By Project click: uses `hx-get="/analytics?range={current}&project={name}" hx-target="#main" hx-push-url`

---

### Story 5.3: Budget Section & Detailed Breakdown Table

As a developer,
I want to see my budget usage progress and a detailed per-project breakdown table with sortable columns,
So that I can track spending against limits and compare resource consumption across projects.

**Acceptance Criteria:**

**Given** the analytics page is displayed
**When** the budget section renders
**Then** a `card card-bordered` shows: monthly budget label, `progress` bar (DaisyUI `progress progress-primary w-full`), spent vs. budget text (`$X.XX / $Y.YY`), percentage used, and estimated days remaining (UX §7.6)

**Given** the budget progress bar renders
**When** usage is below 70%
**Then** the bar color is `progress-primary`
**When** usage is 70-90%
**Then** the bar color is `progress-warning`
**When** usage exceeds 90%
**Then** the bar color is `progress-error` (UX §7.6)

**Given** the analytics page is displayed
**When** the detailed breakdown table renders
**Then** a `table table-sm table-zebra` shows per-project metrics for the selected time range (FR38, UX §7.7):
| Column | Content | Sortable |
|--------|---------|----------|
| Project | Project name | Yes |
| Runs | Run count | Yes |
| Tokens | Total tokens (formatted) | Yes |
| Cost | `$X.XX` | Yes |
| Avg Tokens/Run | Average (formatted) | Yes |

**Given** the detailed breakdown table is displayed
**When** the user clicks a column header to sort
**Then** the table re-sorts by that column (ascending/descending toggle)
**And** this can be done client-side (simple table sort) or via HTMX with a `?sort=` param

**Given** the analytics page at compact widths (1024-1279px)
**When** the table doesn't fit horizontally
**Then** a `overflow-x-auto` wrapper enables horizontal scrolling (UX §12)

**Technical notes:**
- Budget section is flagged as first-to-defer in the PRD — section is self-contained and can be added later without layout changes
- Budget value from project config or dashboard setting
- Table sort can be implemented as lightweight client-side or server-side via HTMX
