# 4. Overview Page

**Route:** `/`
**Purpose:** Hub page. Compact previews of every data domain. Every section is a doorway to a full page.
**PRD FRs:** FR1-7, FR8-11 (partial)
**Visual Language:** Industrial Brutalist Dark — charcoal steel surfaces, cream borders on void, red offset shadows, zero-radius rectangles, monospace uppercase authority.

## Layout

> The ASCII wireframe below is a **structural reference** only. All visual styling follows the Industrial Brutalist Dark design system described in each section.

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

**Container:** `flex gap-[14px] flex-wrap` row. Each card takes `flex: 1; min-width: 180px`.

**DaisyUI base:** `.stat` — overridden with brutalist styling. All DaisyUI border-radius and soft shadows are stripped. Zero-radius everywhere.

**Card surface:**
- Background: `var(--bg-card)` (`#1E1E1E`)
- Border: `2px solid var(--accent-cream)` (`#E8E4DF`) — the harsh cream border that defines the brutalist card vocabulary
- Shadow: `var(--shadow-brutal)` — `4px 4px 0 var(--accent-red)` (`#C43018`), hard-edged offset, never blurred
- Hover: shadow grows to `6px 6px 0 var(--accent-red)`, card lifts via `transform: translate(-1px, -1px)`
- Active/click: shadow collapses to 0, card snaps `translate(2px, 2px)`
- Transition: `150ms ease`; disabled when `prefers-reduced-motion: reduce`

**Diagonal hatching accent (`::after`):**
Each stat card has a decorative corner mark — a `24x24px` pseudo-element positioned `top: 0; right: 0` containing a repeating `-45deg` linear gradient of `var(--accent-red)` stripes (2px stripe, 3px gap). This hatching references industrial blueprint markings and distinguishes stat cards from other card types.

**Card contents:**

| Element | Font | Size | Weight | Transform | Color |
|---------|------|------|--------|-----------|-------|
| `.stat-title` (label) | Azeret Mono | 9px | 700 | uppercase, `letter-spacing: 0.15em` | `var(--text-muted)` (`#666`) |
| `.stat-value` (number) | Azeret Mono | 32px | 900 | none | `var(--text-primary)` (`#E8E4DF`) |
| `.stat-desc` (trend) | Inconsolata | 11px | 600 | none | `var(--text-muted)` default |

**Trend indicators:**
- Positive trend: `var(--accent-green)` (`#2ECC40`), `▲` prefix
- Negative trend: `var(--accent-red)` (`#C43018`), `▼` prefix
- Neutral: `var(--text-muted)` (`#666`)

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

**Section header:** Azeret Mono 13px, weight 800, uppercase, `letter-spacing: 0.12em`. Prefixed with `//` in `var(--accent-red)` via CSS `::before`. Count badge beside title: transparent background, `2px solid var(--accent-orange)` border, Azeret Mono 10px weight 800 in `var(--accent-orange)`.

**Visibility:** Only rendered when active runs exist. Server returns an empty fragment when no runs are active.

**Container:** `flex gap-[14px] flex-wrap`. Cards take `flex: 1; min-width: 280px; max-width: 400px`.

**Card surface:**
- Background: `var(--bg-card)` (`#1E1E1E`)
- Border: `2px solid var(--accent-cream)` on top/right/bottom
- **Left border: `6px solid var(--accent-orange)`** (`#D4602A`) — the thick left accent stripe that distinguishes active run cards from all other card types
- Shadow: `3px 3px 0 var(--accent-orange)` — orange offset shadow (not red, signaling "in-progress")
- Hover: shadow grows to `5px 5px 0 var(--accent-orange)`, card lifts `translate(-2px, -2px)`
- Active/click: shadow collapses, card snaps down
- Cursor: `pointer`

**Card contents:**

| Element | Font | Size | Weight | Transform | Color |
|---------|------|------|--------|-----------|-------|
| Project name | Azeret Mono | 12px | 800 | uppercase, `letter-spacing: 0.05em` | `var(--text-primary)` |
| Feature description | Inconsolata | 12px | 400 | none, truncated ~40 chars | `var(--text-secondary)` (`#999`) |
| Elapsed time | Inconsolata | 11px | 700 | none | `var(--accent-amber)` (`#D49A20`) |

**Phase pipeline (mini version):**
Five compact rectangular blocks representing Plan, Build, Validate, Document, Ship. These are **not** DaisyUI steps — they are flat, zero-radius rectangles laid out in a `flex` row with `gap: 3px`.

| State | Background | Border | Text Color | Extra |
|-------|-----------|--------|------------|-------|
| Completed | `var(--accent-green)` (`#2ECC40`) | `1px solid var(--accent-green)` | `var(--bg-void)` (dark on green) | `✓` prefix |
| Active | `var(--accent-orange)` (`#D4602A`) | `1px solid var(--accent-orange)` | `var(--bg-void)` (dark on orange) | `●` prefix, CSS `animation: pulse 2s ease-in-out infinite` |
| Pending | `#2A2A2A` | `1px solid #333` | `var(--text-muted)` | No prefix |

Each block: Azeret Mono 9px, weight 700, uppercase, `letter-spacing: 0.06em`, `padding: 3px 8px`.

**HTMX:**
- Section `id="active-runs"`
- `hx-get="/partials/active-runs" hx-trigger="every 3s" hx-swap="outerHTML"`
- When a run completes, the card disappears on next poll and stats update via `hx-swap-oob`

**Click behavior:** Entire card is clickable — `hx-get="/runs/{id}" hx-target="#main" hx-push-url="/runs/{id}"`

## 4.3 Recent Runs Section

**Section header:** Same `//`-prefixed pattern as 4.2. "Recent Runs" in Azeret Mono 13px, weight 800, uppercase. The `//` prefix renders in `var(--accent-red)`.

**"View All" link:** Azeret Mono 10px, weight 700, uppercase, `letter-spacing: 0.08em`, `var(--text-muted)` default. Hover: color shifts to `var(--accent-red)`, underline appears via `border-bottom: 2px solid var(--accent-red)`. Navigates via `hx-get="/runs" hx-target="#main" hx-push-url="/runs"`.

**Table wrapper card:**
- Background: `var(--bg-card)` (`#1E1E1E`)
- Border: `2px solid var(--accent-cream)` (`#E8E4DF`)
- Shadow: `var(--shadow-brutal)` — `4px 4px 0 var(--accent-red)`
- `overflow: hidden` to contain table edges within the card border

**Table header (`thead`):**
- Background: `var(--bg-header)` (`#252525`)
- Bottom border: `3px solid var(--accent-red)` — the thick red divider between header and body
- `th` cells: Azeret Mono 9px, weight 800, uppercase, `letter-spacing: 0.15em`, color `var(--accent-cream)` (`#E8E4DF`)

**Table rows (`tbody tr`):**
- `td` padding: `12px 16px`, font-size 13px, Inconsolata weight 500
- Bottom border: `1px solid #2A2A2A`
- Hover: `td` background shifts to `var(--bg-card-hover)` (`#252525`), transition `50ms`
- Cursor: `pointer`

**Table columns:**

| Column | Width | Content | Style |
|--------|-------|---------|-------|
| Project | auto | Project name | Inconsolata 13px, `var(--text-primary)` |
| Feature | flexible | Description, truncated | Inconsolata 13px, `var(--text-secondary)` (`#999`) |
| Status | narrow | Badge | Outline badge (see below) |
| Duration | narrow | `Xm Ys` | Inconsolata 13px, `var(--text-primary)` |
| Started | narrow | Relative time | Inconsolata 12px, `var(--text-muted)` (`#666`) |

**Status badges (outline style):**
All badges: Azeret Mono 9px, weight 700, uppercase, `letter-spacing: 0.05em`, `padding: 3px 8px`, **zero border-radius**, transparent background with `2px solid` colored border.

| Status | Text Color | Border Color |
|--------|-----------|-------------|
| Completed (`✓`) | `var(--accent-green)` | `var(--accent-green)` |
| Running (`●`) | `var(--accent-amber)` | `var(--accent-amber)` |
| Failed (`✗`) | `var(--accent-red)` | `var(--accent-red)` |
| Aborted (`⦻`) | `var(--text-muted)` | `var(--text-muted)` |

**Rows:** 5 most recent runs. No pagination here — that's what the full Runs List page is for.

**Click behavior:** Each row is clickable — navigates to `/runs/{id}`.

**HTMX:** `hx-trigger="every 15s"` to refresh the table body. Slower polling than active runs since recent runs change less frequently.

## 4.4 Project Breakdown Section

**Section header:** `// PROJECTS` — same `//`-prefixed pattern.

**Container:** `flex gap-[14px] flex-wrap` row.

**Card surface:**
- Background: `var(--bg-card)` (`#1E1E1E`)
- Border: `2px solid var(--accent-cream)` (`#E8E4DF`)
- Shadow (default): `3px 3px 0 #444` — neutral gray offset shadow at rest, signaling these are selectable but not active
- Shadow (hover): `5px 5px 0 var(--accent-red)`, card lifts `translate(-2px, -2px)` — shadow shifts from gray to red on hover
- Shadow (selected): `4px 4px 0 var(--accent-red)` — red shadow persists to indicate selection
- Border (selected): `border-color: var(--accent-red)` — cream border turns red
- `min-width: 160px`
- Cursor: `pointer`

**Card contents:**

| Element | Font | Size | Weight | Transform | Color |
|---------|------|------|--------|-----------|-------|
| Project name | Azeret Mono | 12px | 800 | uppercase, `letter-spacing: 0.05em` | `var(--text-primary)` |
| Run count | Inconsolata | 11px | 600 | none | `var(--text-muted)` (`#666`) |
| Success rate | Inconsolata | 11px | 700 | none | Color-coded (see below) |
| Total cost | Inconsolata | 11px | 600 | none | `var(--text-muted)` (`#666`) |

**Success rate color coding:**
- 80% or above: `var(--accent-green)` (`#2ECC40`)
- 50-79%: `var(--accent-amber)` (`#D49A20`)
- Below 50%: `var(--accent-red)` (`#C43018`)

**Click behavior:** Clicking a project card sets the global project filter.
- `hx-get="/?project={name}" hx-target="#main" hx-push-url="/?project={name}"`
- This reloads the entire overview scoped to that project
- The project filter dropdown in the header also updates (via `hx-swap-oob`)

**Visual hint:** When a project filter is active, the selected project card gains `border-color: var(--accent-red)` and `box-shadow: 4px 4px 0 var(--accent-red)`. The section title shows "Projects -- Filtered: {name}" with a clear (x) button.

## 4.5 Cost Summary Strip

A compact, full-width preview of cost/token data with a link to the full analytics page.

**Card surface:**
- Background: `var(--bg-card)` (`#1E1E1E`)
- Border: `2px solid var(--accent-cream)` (`#E8E4DF`)
- Shadow: `var(--shadow-brutal)` — `4px 4px 0 var(--accent-red)`
- Layout: `flex` row with `align-items: center; justify-content: space-between; gap: 24px`
- Padding: `16px 20px`

**Content:**

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| "Cost This Week" label | Azeret Mono | 9px | 700, uppercase, `letter-spacing: 0.15em` | `var(--text-muted)` (`#666`) |
| Cost value | Azeret Mono | 24px | 900 | `var(--accent-amber)` (`#D49A20`) |
| Token count | Inconsolata | 11px | 600 | `var(--text-muted)` (`#666`) |

**Mini bar chart:**
- 7 bars (one per day of the week), laid out in a `flex` row with `align-items: flex-end; gap: 4px; height: 36px`
- Each bar: `width: 14px`, `min-height: 2px`, zero border-radius
- Odd bars: `var(--accent-orange)` (`#D4602A`)
- Even bars: `var(--accent-red)` (`#C43018`)
- Hover on individual bar: background shifts to `var(--accent-amber)`
- Bar heights set via inline `style="height: XX%"` based on daily token count relative to the week's max

**"View All" link:** Azeret Mono (display font), 10px, weight 700, uppercase, `var(--text-muted)`. Hover: `var(--accent-red)` with red underline. Navigates to `/analytics`.

**HTMX:** Static — refreshes only when the overview page reloads. No independent polling.

## 4.6 New Run Button

Prominent button placed top-right of the overview content area, in the page header row next to the `h1` title.

**Surface:**
- Background: `transparent` — no fill at rest, letting the void show through
- Border: `3px solid var(--accent-cream)` (`#E8E4DF`)
- Text: `var(--accent-cream)`, Azeret Mono 11px, weight 800, uppercase, `letter-spacing: 0.08em`
- Shadow: `var(--shadow-brutal-sm)` — `3px 3px 0 var(--accent-red)`
- Border-radius: `0` (zero-radius, like everything else)
- Padding: `8px 16px`
- Content: `+ New Run`

**Hover state:**
- Background fills with `var(--accent-red)` (`#C43018`)
- Shadow grows to `5px 5px 0 var(--accent-cream)` (shadow color flips from red to cream)
- Card lifts: `transform: translate(-2px, -2px)`

**Active/click state:**
- Shadow collapses to `none`
- Element snaps down: `transform: translate(2px, 2px)`

**Transition:** `150ms ease` on all properties.

**Behavior:** Opens the New Run modal (see section 8).

---
