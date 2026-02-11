# Epic 1: Dashboard Foundation & Live Overview

User can launch the web dashboard from the CLI and see a comprehensive, auto-refreshing overview of all ADW activity — aggregate stats, active runs with phase progression, recent runs, per-project breakdown, and cost summary — with dark theme, responsive layout, and HTMX-powered navigation.

**FRs covered:** FR1-FR11, FR42-FR44, FR45-FR53 (27 FRs)

### Story 1.1: Server Infrastructure & CLI Launch

As a developer,
I want to launch the ADW web dashboard from the CLI and have it start a local server with proper security defaults,
So that I can access the dashboard in my browser without complex setup.

**Acceptance Criteria:**

**Given** the ADW CLI is installed
**When** the user runs `adw dashboard web` (or equivalent Typer command)
**Then** a FastAPI server starts on `127.0.0.1:8100` by default
**And** the user's default browser opens automatically to the dashboard URL (FR45, FR46)
**And** the CLI command follows existing ADW CLI patterns (Typer, consistent flags, help text) per NFR28

**Given** the server is starting
**When** the user provides `--port 9000`
**Then** the server binds to port 9000 instead of 8100 (FR47)

**Given** the server is starting
**When** the user provides `--host 0.0.0.0`
**Then** the server binds to all interfaces for LAN access
**And** a warning message is displayed at startup about exposing the dashboard (NFR12)

**Given** the server is running
**When** a request is made to any mutation endpoint (POST)
**Then** the server validates a CSRF token from a hidden form input
**And** requests without a valid CSRF token are rejected (FR53, NFR9)

**Given** the webhook server is already running on port 8000
**When** the dashboard server starts on port 8100
**Then** both servers run concurrently without port conflicts (NFR27)

**Architecture requirements:**
- Shared server factory in `server/app.py` with feature-based APIRouter composition — used by both dashboard and webhook
- Dashboard on port 8100, webhook on port 8000 — independent runtime but shared factory
- Global `RequestIDMiddleware` only; dashboard concerns as route dependencies
- All data access through FastAPI `Depends()` — never import managers directly in route handlers
- CSRF token generation in `dashboard/dependencies.py`, validated on POST endpoints
- Dashboard module MUST NOT import from `webhook/` module — zero dependency
- New dependency: `jinja2` added via `uv add`; HTMX 2.0.8 vendored locally; DaisyUI 5 + Tailwind CSS v4 via CDN
- Webhook refactoring: `webhook/server.py` migrated to use shared `server/app.py` factory

**Technical notes:**
- Route file organization: `routes.py` (pages), `partials.py` (fragments), `sse.py` (streams), `mutations.py` (POST actions), `dependencies.py` (DI + CSRF)
- Data layer via DI: `IndexManager`, `StatsAggregator`, `ProjectRegistryManager` injected through `Depends()` (NFR25)
- Static assets served with aggressive caching headers (NFR6)
- Dashboard server handles malformed/corrupted index entries gracefully without crashing (NFR13)
- Server binds to `127.0.0.1` by default for security (NFR8)

---

### Story 1.2: Base Template, Navigation & Theme

As a developer,
I want a persistent header with navigation, project filter, and dark/light theme toggle that works across all pages without full page reloads,
So that I can efficiently navigate the dashboard and customize its appearance.

**Acceptance Criteria:**

**Given** the dashboard is loaded in the browser
**When** the page renders
**Then** a persistent header bar is displayed that never swaps via HTMX
**And** the header contains: logo/title (`text-lg font-bold`, links to `/`), nav links (Overview, Runs, Analytics), project filter dropdown, and theme toggle
**And** the current page nav link shows an active indicator via `font-semibold border-b-2 border-primary` or `tab-active`

**Given** the header is displayed
**When** the user clicks a nav link (e.g., "Runs")
**Then** the page content swaps via HTMX (`hx-get="/runs" hx-target="#main" hx-push-url="/runs"`) without full page reload (FR51)
**And** only `<main id="main">` content is replaced — header and footer persist
**And** a `loading loading-spinner loading-sm` indicator shows in the header during the swap (UX §9.5)
**And** the browser URL updates and back/forward navigation works natively (FR52)

**Given** the user navigates directly to a URL (e.g., `/runs`) via browser address bar or bookmark
**When** the server receives the request without `HX-Request` header
**Then** the full HTML page is returned including `<html>`, `<head>`, header, content, and footer (dual-response pattern)
**And** the page is fully functional (FR52)

**Given** the header is displayed
**When** the user clicks the theme toggle (`swap swap-rotate` with sun/moon icons)
**Then** the `data-theme` attribute on `<html>` switches between `dark` and `light`
**And** the choice persists via `localStorage` key `adw-theme` (FR49)

**Given** the user previously selected light theme
**When** the page loads on any subsequent visit
**Then** an inline `<script>` in `<head>` reads `localStorage` and sets `data-theme` before render to prevent flash of wrong theme (UX §14)

**Given** the dashboard is loaded
**When** the page renders
**Then** a footer/status bar is displayed below `<main>` showing: "Last updated Xs ago", active run count, and a manual refresh button
**And** the footer updates via `hx-trigger="every 10s"` with `hx-swap-oob="true"` (UX §3.2)

**UX/Component specifications:**
- Page layout: `<body data-theme="dark">` → `<header>` (never swaps) → `<main id="main">` (HTMX swap target) → `<footer id="status-bar">` (OOB updates)
- Template hierarchy: `pages/` (full views) + `partials/` (HTMX fragments) + `components/` (reusable pieces)
- Project filter: `select select-bordered select-sm` populated server-side from `ProjectRegistryManager`; selecting appends `?project={name}` to current URL; "All Projects" clears filter
- Typography: System sans-serif for UI labels/headings; `font-mono` for data values (UX §1)
- Default theme: DaisyUI `dark`; alternative: `light` (UX §14)
- CSS transitions: `.htmx-swapping { opacity: 0; transition: opacity 100ms ease-out }` and `.htmx-settling { opacity: 1; transition: opacity 200ms ease-in }` (UX §14)
- Custom CSS properties in `dashboard/static/dashboard.css`: phase colors, chart colors, `--table-row-height`, `--card-padding-compact` (UX §14)
- Responsive: Full layout at ≥1280px, compact at 1024-1279px; min supported 1024px (UX §12)
- HTML-only error responses: HTMX errors get banner fragments, direct errors get full error pages (Architecture)

---

### Story 1.3: Overview Stat Cards & Status Vocabulary

As a developer,
I want to see aggregate statistics (total runs, success rate, avg duration, tokens, cost) on the main dashboard with consistent status indicators,
So that I can instantly assess overall ADW health and activity at a glance.

**Acceptance Criteria:**

**Given** the user navigates to the overview page (`/`)
**When** the page renders
**Then** a row of 5 stat cards is displayed using DaisyUI `stats stats-horizontal shadow` (FR1)
**And** each card contains: `stat-title` (label), `stat-value` (large number in `text-2xl font-mono`), `stat-desc` (trend indicator)

**Given** the stat cards are displayed
**When** data is loaded from `StatsAggregator`
**Then** the following stats are shown with correct formatting:
| Stat | Value Format | Trend |
|------|-------------|-------|
| Total Runs | Integer | vs. previous week |
| Success Rate | Percentage (1 decimal) | vs. previous week (pp) |
| Avg Duration | `Xm Ys` (`font-mono`) | vs. previous week |
| Tokens Used | Formatted: `2.4M`, `340K` (`font-mono`) | This week total |
| Estimated Cost | `$X.XX` (`font-mono`) | This week total |
**And** positive trends show green text with `▲` prefix, negative trends show red text with `▼` prefix, neutral uses default color

**Given** run status indicators are shown anywhere in the dashboard
**When** a run has a specific status
**Then** the following design vocabulary is applied consistently (UX §1):
| Status | Color | Icon | Badge Class |
|--------|-------|------|-------------|
| Running | `warning` (amber) | `●` (pulsing) | `badge-warning` |
| Completed | `success` (green) | `✓` | `badge-success` |
| Failed | `error` (red) | `✗` | `badge-error` |
| Interrupted | `warning` (orange) | `⊘` | `badge-warning badge-outline` |
| Aborted | `neutral` (grey) | `⦻` | `badge-ghost` |

**Given** the stats row is displayed
**When** other sections poll and data has changed
**Then** the stats row can be refreshed out-of-band via `id="stats-row"` with `hx-swap-oob="true"` (UX §9.4)

**Given** the overview is displayed at compact screen widths (1024-1279px)
**When** there isn't enough horizontal space for all 5 stat cards
**Then** stat cards wrap to 2 rows using `flex flex-wrap gap-4` (3 cards first row, 2 second row) (UX §12)

**Technical notes:**
- Stats data sourced from `StatsAggregator` via FastAPI `Depends()`
- Stats row partial at `/partials/stats` for OOB refresh (UX §9.1)
- Stats row polls every 30s on overview page (UX §9.3)
- Stat card values use bold large sans-serif (`text-3xl` or `text-2xl`) per typography rules (UX §1)

---

### Story 1.4: Active Runs Section with Live Updates

As a developer,
I want to see currently active runs with real-time phase progression and elapsed time on the overview,
So that I can monitor in-progress work without leaving the dashboard.

**Acceptance Criteria:**

**Given** the overview page is displayed and runs are currently active
**When** active runs exist
**Then** an "Active Runs" section is displayed with a count badge (e.g., "Active Runs (2)") (FR2)
**And** each active run is shown as a `card card-compact card-bordered` with `border-l-4 border-warning` left accent

**Given** an active run card is displayed
**When** the card renders
**Then** it shows: project name (`font-semibold text-sm`), feature description (`text-sm text-base-content/70`, truncated ~40 chars), mini phase pipeline, and elapsed time (`font-mono text-xs`)
**And** the mini phase pipeline uses DaisyUI `steps steps-horizontal` at compact size with: completed phases as `step-success`, active phase as `step-warning` with CSS `phase-pulse` animation (`animate-pulse`), pending phases as default grey (FR8, FR9)

**Given** active runs are displayed
**When** 3 seconds pass
**Then** the active runs section polls via `hx-get="/partials/active-runs" hx-trigger="every 3s" hx-swap="outerHTML"` on section `id="active-runs"` (FR6, FR7)
**And** elapsed time updates reflect current duration without manual refresh (FR10)
**And** no visible loading indicator is shown during polling — polling is invisible to the user (UX §9.5)

**Given** the active runs section polls
**When** a run has completed since the last poll
**Then** the completed run's card disappears from active runs
**And** the stats row and status bar are updated via `hx-swap-oob="true"` out-of-band (UX §9.4)

**Given** an active run card is displayed
**When** the user clicks the card
**Then** navigation occurs via `hx-get="/runs/{id}" hx-target="#main" hx-push-url="/runs/{id}"` to the run detail page

**Given** the overview page is displayed and no runs are currently active
**When** no active runs exist
**Then** the active runs section is not rendered at all — no "no active runs" message; its absence is the message (UX §11.1)

**Given** the browser tab becomes hidden
**When** `document.visibilityState === "hidden"`
**Then** HTMX naturally pauses polling; no additional logic needed (UX §9.3)

**Given** active run cards at compact widths (1024-1279px)
**When** horizontal space is limited
**Then** cards use `flex flex-wrap gap-4` and stack vertically (UX §12)

**UX specifications:**
- Phase pipeline mini version: 5 compact nodes (Plan → Build → Validate → Document → Ship) (UX §4.2)
- Cards layout: `flex gap-4 flex-wrap`, cards take equal width up to 2-3 per row
- CSS animation: `@keyframes phase-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }` applied to `.phase-active` (UX §14)

---

### Story 1.5: Recent Runs Table & Project Breakdown

As a developer,
I want to see my most recent runs in a compact table and a per-project breakdown showing run counts, success rates, and costs,
So that I can quickly assess recent activity and compare project health.

**Acceptance Criteria:**

**Given** the overview page is displayed
**When** runs exist in the index
**Then** a "Recent Runs" section is displayed with a "View All →" link on the right (FR3)
**And** the link navigates via `hx-get="/runs" hx-target="#main" hx-push-url="/runs"`
**And** the section contains a `table table-sm` inside a `card card-compact`

**Given** the recent runs table is displayed
**When** data is loaded
**Then** the 5 most recent runs are shown with columns:
| Column | Content | Style |
|--------|---------|-------|
| Project | Project name | `text-sm` |
| Feature | Description, truncated | `text-sm text-base-content/70 truncate max-w-[200px]` |
| Status | Icon + label | `badge badge-sm badge-{status}` per design vocabulary |
| Duration | `Xm Ys` | `font-mono text-xs` |
| Started | Relative time (e.g., "25m ago") | `text-xs text-base-content/50` |
**And** each row is clickable and navigates to `/runs/{id}` (UX §4.3)

**Given** the recent runs section is displayed
**When** 15 seconds pass
**Then** the table body refreshes via `hx-trigger="every 15s"` on section `id="recent-runs"` (UX §9.3)
**And** no loading indicator is shown during polling

**Given** the overview page is displayed
**When** projects are registered
**Then** a "Projects" section shows a card for each registered project using `card card-compact` in a `flex gap-3 flex-wrap` row (FR4, FR42)
**And** each project card shows: name (`font-semibold text-sm`), run count (`text-xs`), success rate (`text-xs`, color-coded: green ≥80%, yellow 50-79%, red <50%), total cost (`font-mono text-xs`) (FR44)

**Given** a project card is displayed
**When** the user clicks it
**Then** the global project filter is set via `hx-get="/?project={name}" hx-target="#main" hx-push-url="/?project={name}"` (FR5, FR43)
**And** the project filter dropdown in the header also updates via `hx-swap-oob` (UX §4.4)

**Given** a project filter is active
**When** the overview renders
**Then** the selected project card shows a `ring ring-primary` outline
**And** the section title shows "Projects — Filtered: {name}" with a clear (×) button (UX §4.4)
**And** all overview sections (stats, active runs, recent runs) scope to that project (FR5)

**Given** the overview is viewed at compact widths (1024-1279px)
**When** tables don't fit horizontally
**Then** tables get a `overflow-x-auto` horizontal scroll wrapper (UX §12)
**And** the feature column `max-w` shrinks on compact screens

**Technical notes:**
- Data sourced from `IndexManager`, `StatsAggregator`, `ProjectRegistryManager` via `Depends()` (NFR25)
- Project filter behavior: selecting appends `?project={name}` to all page URLs; "All Projects" clears filter
- All pages respect the project filter — stats, runs, analytics scope to that project (UX §3.1)

---

### Story 1.6: Cost Summary Strip & Empty States

As a developer,
I want to see a compact cost preview on the overview and helpful guidance when no data exists,
So that I can track spending at a glance and know how to get started with ADW.

**Acceptance Criteria:**

**Given** the overview page is displayed and runs exist
**When** the page renders
**Then** a "Cost This Week" strip is displayed using `card card-compact` with horizontal content layout
**And** it shows: weekly total cost (`font-mono font-semibold`), weekly total tokens (formatted), a mini CSS bar chart (7 bars, one per day, using inline `div` elements with height based on daily token count), and a "View Details →" link to `/analytics` (UX §4.5)

**Given** the cost summary strip is displayed
**When** the overview page reloads
**Then** the strip refreshes with the page — no independent polling (UX §4.5)

**Given** a "New Run" button is present on the overview
**When** it is rendered
**Then** it appears as `btn btn-primary btn-sm` with a `+` icon, positioned top-right of the overview content area (UX §4.6)
**And** clicking it opens the New Run modal (implemented in Epic 3)

**Given** the dashboard is loaded for the first time with no registered projects
**When** the overview page renders
**Then** a welcome empty state is displayed using a centered `card` or `hero` component with `text-base-content/60`:
```
Welcome to ADW Dashboard

No projects registered yet. Register a
project from the CLI to get started:

$ adw global register
```
**And** the stat cards, active runs, recent runs, and project sections are not shown (NFR14, UX §11.1)

**Given** projects are registered but no runs have been executed
**When** the overview page renders
**Then** a "No runs yet" empty state is displayed:
```
No runs yet

Start your first run from the CLI or use
the New Run button above.

[+ Start a Run]
```
**And** the "Start a Run" button opens the New Run modal (NFR15, UX §11.1)
**And** project breakdown cards still display (with 0 runs, 0% success)

**Given** the data layer encounters an error (corrupted index, file lock)
**When** the overview tries to load
**Then** an `alert alert-error` banner appears at the top of the affected section: "Unable to load run data. The index file may be corrupted or locked." (UX §11.2)
**And** the rest of the page still renders with whatever data is available (NFR13, NFR17)

**Given** an HTMX request fails (network error, server error)
**When** the error occurs
**Then** a positioned `alert alert-error` toast appears at `fixed top-16 right-4 w-auto z-50` with a retry link
**And** the toast auto-dismisses after a few seconds (UX §11.2)
**And** shown via `htmx:responseError` event handler (~5 lines inline JS)

**Given** the server receives a request for a non-existent run
**When** the route returns 404
**Then** a centered message is shown in `#main`: "Run not found. It may have been deleted." with a back link to overview (UX §11.2)

**Technical notes:**
- Mini bar chart: 7 `div` elements with CSS `height` percentages calculated server-side relative to max daily value
- Empty state detection: check `ProjectRegistryManager.list_projects()` count and `IndexManager` run count
- Error states must work for both HTMX partial and full-page responses (HTML-only, never JSON)
