# Requirements Inventory

## Functional Requirements

**Dashboard Overview (FR1-FR7):**
- FR1: User can view aggregate statistics (total runs, success rate, average duration, total token usage, estimated cost) on the main dashboard
- FR2: User can view a list of currently active runs with their project, feature description, current phase, and elapsed time
- FR3: User can view a list of recent runs with their project, feature description, status, duration, and relative start time
- FR4: User can view a per-project breakdown showing each registered project's run count, success rate, token usage, and estimated cost
- FR5: User can filter the dashboard view to a specific project
- FR6: Dashboard automatically refreshes data at a configurable interval without full page reload
- FR7: Dashboard refreshes more frequently when active runs exist

**Run Monitoring (FR8-FR11):**
- FR8: User can see real-time phase progression for active runs (which phase is currently executing)
- FR9: User can see status indicators that visually distinguish running, completed, failed, interrupted, and aborted runs
- FR10: User can see elapsed time for active runs that updates without manual refresh
- FR11: User can see when data was last refreshed

**Run Management (FR12-FR15):**
- FR12: User can start a new run by selecting a registered project and providing a feature description
- FR13: User can abort an active run with a confirmation step
- FR14: User can start a new run pre-populated with context from a previous run (re-run flow)
- FR15: System validates that the selected project exists and is registered before starting a run

**Run Inspection (FR16-FR27):**
- FR16: User can view detailed metadata for any run (run ID, project, feature, status, timestamps, duration, phase history)
- FR17: User can view phase-by-phase progression for a run with per-phase status indicators (success/failure)
- FR18: User can browse artifacts produced by each phase of a run
- FR19: User can view artifact content inline (text-based artifacts rendered in the browser)
- FR20: User can view run logs with the most recent entries visible by default
- FR21: User can search run logs by keyword
- FR22: User can filter run logs by severity level
- FR23: User can stream logs in real-time for an active run
- FR24: User can view the artifacts path for a run to locate files on disk
- FR25: User can view LLM prompts sent and responses received for each phase, with per-exchange token counts
- FR26: User can view logs filtered by individual phase
- FR27: User can navigate to the associated PR or Linear issue from a completed run

**Runs List & Filtering (FR28-FR31):**
- FR28: User can filter the runs list by status (running, completed, failed, interrupted, aborted)
- FR29: User can filter the runs list by date range
- FR30: User can sort the runs list by any column (status, project, duration, date)
- FR31: User can paginate through run history

**Cost & Token Analytics (FR32-FR38):**
- FR32: User can select a time range (7 days, 30 days, 90 days, All time) that filters all analytics data on the page via HTMX partial swap
- FR33: User can view aggregate stat cards for the selected time range: total tokens, total cost, average tokens per run, and total runs — each with a delta indicator showing change from the previous period
- FR34: User can view a daily usage bar chart showing token consumption per day, with stacked bars distinguishing input tokens from output tokens
- FR35: User can view token usage and cost broken down by project as a horizontal bar chart, with percentage distribution
- FR36: User can click a project in the By Project breakdown to filter the entire analytics page to that project
- FR37: User can view token usage and cost broken down by phase (Build, Plan, Validate, Document, Ship) as a horizontal bar chart with percentage distribution
- FR38: User can view a detailed breakdown table showing per-project metrics (runs, tokens, cost, avg tokens/run) with sortable columns

**View Modes (FR39-FR41):**
- FR39: User can navigate the dashboard using keyboard shortcuts (shortcut overlay, list navigation, search focus)
- FR40: User can toggle a terminal mode that displays raw log output in a monospace scrolling view
- FR41: User can enter focus mode on an active run, replacing the dashboard with a single-run live view showing phase progress and streaming logs

**Project Overview (FR42-FR44):**
- FR42: User can view all registered projects with their associated paths
- FR43: User can drill down from a project into its recent runs
- FR44: User can see per-project success rates and usage trends

**Dashboard Infrastructure (FR45-FR53):**
- FR45: User can launch the web dashboard from the CLI
- FR46: System automatically opens the user's default browser when the dashboard server starts
- FR47: User can configure the server port
- FR48: System serves the dashboard on localhost by default (127.0.0.1)
- FR49: User can customize the dashboard appearance (dark mode as default)
- FR50: Dashboard layout adapts to screen widths down to 1024px
- FR51: User can navigate between dashboard views without full page reload
- FR52: User can bookmark specific dashboard views via URL
- FR53: System provides CSRF protection on all mutation endpoints

## NonFunctional Requirements

**Performance (NFR1-NFR7):**
- NFR1: Initial page load completes in <500ms (server-rendered, no JS bundle)
- NFR2: HTMX partial swaps complete in <200ms (server response time)
- NFR3: Auto-refresh polling does not degrade page responsiveness
- NFR4: Log streaming for active runs displays output within 1 second of generation
- NFR5: Dashboard remains responsive with 1000+ runs in the index
- NFR6: Static assets (HTMX, DaisyUI/Tailwind CSS) are served with aggressive caching headers
- NFR7: SSE connections for live run updates consume minimal server resources

**Security (NFR8-NFR12):**
- NFR8: Dashboard server binds to 127.0.0.1 by default (localhost only)
- NFR9: All mutation endpoints (start run, abort run) include CSRF protection
- NFR10: Dashboard does not expose file system paths beyond what the existing data layer provides
- NFR11: No API keys, secrets, or credentials are logged or displayed in the dashboard UI
- NFR12: If --host 0.0.0.0 is used for LAN access, a warning is displayed at startup

**Reliability (NFR13-NFR19):**
- NFR13: Dashboard server handles malformed or corrupted index entries gracefully without crashing
- NFR14: Dashboard remains functional when no projects are registered (empty state)
- NFR15: Dashboard remains functional when no runs exist (empty state)
- NFR16: Failed HTMX requests display a user-visible error indicator, not a silent failure
- NFR17: Dashboard server recovers gracefully from data layer errors (file locks, missing files)
- NFR18: SSE connections automatically reconnect after network interruption
- NFR19: Starting/aborting a run from the dashboard handles concurrent CLI operations without data corruption

**Maintainability (NFR20-NFR24):**
- NFR20: New dashboard code maintains >80% test coverage (API routes, template rendering logic)
- NFR21: Jinja2 templates use a component/partial structure that enables reuse across pages
- NFR22: API routes are organized by capability area matching the FR structure
- NFR23: All API endpoints return both full-page and HTMX-partial responses based on request headers
- NFR24: Dashboard code follows existing ADW project conventions (type hints, Pydantic models, pytest)

**Integration (NFR25-NFR28):**
- NFR25: Dashboard reads from the same data sources as the TUI dashboard (IndexManager, StatsAggregator, ProjectRegistryManager) without modifications
- NFR26: Starting a run from the dashboard produces identical results to starting via CLI
- NFR27: Dashboard server can run concurrently with the existing webhook server without port conflicts
- NFR28: Dashboard CLI command follows existing ADW CLI patterns (Typer, consistent flags and help text)

## Additional Requirements

**From Architecture:**
- Shared server infrastructure: `server/app.py` factory with feature-based APIRouter composition, used by both dashboard and webhook
- Separate server processes: Dashboard on port 8100, webhook on port 8000 — independent runtime but shared factory
- Run trigger extraction: `core/run_trigger.py` extracted from `webhook/runner.py` so dashboard can start/abort runs without importing webhook
- Middleware strategy: Global `RequestIDMiddleware` only; webhook logging converted to route dependency; dashboard concerns as route dependencies
- Data layer via Dependency Injection: All data access through FastAPI `Depends()` — never import managers directly in route handlers
- CSRF protection: Token-based via hidden form input, generated server-side, validated on POST endpoints
- SSE implementation: FastAPI `StreamingResponse` with HTMX SSE extension for live phase progression and log streaming
- CSS-only charts: Server-rendered bar charts via CSS flex/height — no JavaScript charting library
- Template hierarchy: `pages/` (full views) + `partials/` (HTMX fragments) + `components/` (reusable pieces)
- Dual-response pattern: Every page route checks `HX-Request` header; returns fragment for HTMX, full page for direct navigation
- Route file organization: `routes.py` (pages), `partials.py` (fragments), `sse.py` (streams), `mutations.py` (POST actions), `dependencies.py` (DI + CSRF)
- HTML-only error responses: Dashboard routes never return JSON; HTMX errors get banner fragments, direct errors get full error pages
- Webhook refactoring: `webhook/server.py` migrated to use shared `server/app.py` factory; middleware converted to route dependencies
- Dashboard boundary: Dashboard MUST NOT import from `webhook/` module — zero dependency
- New dependency: `jinja2` added via `uv add`; HTMX 2.0.8 vendored locally; DaisyUI 5 + Tailwind CSS v4 via CDN
- CDN delivery is authoritative: Architecture overrides UX spec's Tailwind standalone CLI suggestion — use CDN, not build tooling

**From UX Design:**
- Hub-and-spoke navigation: Overview as hub with drill-down to detail pages; no sidebar; horizontal header nav
- Persistent header: Logo, nav links (Overview/Runs/Analytics), project filter dropdown, theme toggle — never swaps via HTMX
- Content swap target: `<main id="main">` is the sole HTMX swap target for all navigation
- Status design vocabulary: Consistent across all pages — Running (amber/pulsing), Completed (green/checkmark), Failed (red/X), Interrupted (orange/outline), Aborted (grey/ghost)
- Typography rules: Monospace (`font-mono`) for run IDs, durations, token counts, costs, logs; sans-serif for UI labels and headings; stat values in bold large sans-serif
- Phase pipeline visualization: DaisyUI `steps steps-horizontal` — mini on overview cards, full-width on run detail; phase-pulse CSS animation for active phase
- Lazy-loaded phase details: Phase accordion content NOT loaded until user clicks — `hx-trigger="click once"` for fast initial page load
- Polling intervals: Active runs 3s, recent runs 15s, stats 30s, status bar 10s — polling pauses when tab hidden
- Out-of-band updates: Active runs poll can include OOB swaps for stats and status bar to keep sections synchronized
- Loading indicators: `loading-spinner` for navigation, `loading-dots` for lazy content, invisible for polling, button spinner for form submit
- Empty states: Welcome message for no projects (with CLI command); "No runs yet" with New Run button; no active runs section simply hidden; filter no-match with clear button
- Error states: Alert banners for data layer errors; positioned auto-dismiss toast for HTMX failures; inline form validation errors; 404 with back link
- Responsive behavior: Full layout at 1280px+, compact (wrapped stat cards, stacked panels) at 1024-1279px; tables get horizontal scroll wrapper; minimum supported 1024px
- Keyboard shortcuts (~30 lines inline JS): `?` overlay, `g h/r/a` navigation, `n` new run, `j/k` list navigation, `Enter` open, `Esc` close/back, `/` search focus, `r` refresh
- Dark theme default: DaisyUI `data-theme="dark"`, light alternative via toggle, `localStorage` persistence with inline `<head>` script to prevent flash
- CSS animations: `phase-pulse` keyframes for active run indicator; `htmx-swapping`/`htmx-settling` opacity transitions for smooth content swaps
- Custom CSS properties: Phase colors, chart colors, table row height, card padding — all in `dashboard/static/dashboard.css`
- Footer/status bar: Last updated timestamp, active run count, manual refresh button — updates via `hx-swap-oob` every 10s
- New Run modal: DaisyUI `modal`, project select + feature textarea, CSRF hidden input, loading spinner on submit, re-run variant pre-populates from previous run
- Abort confirmation modal: Warning-styled modal with run ID and current phase, cancel + abort buttons, CSRF protected
- Run detail page: Back link (context-aware), action buttons (Abort for active, Re-run for all), metadata card with copy button, phase accordion with hooks/artifacts/LLM/logs sub-sections
- Failed run variant: Auto-expand failed phase, error alert banner above phases, pre-filter logs to ERROR severity
- Active run variant: Pulsing phase indicator, SSE-updated elapsed time, streaming logs in current phase, Abort button visible
- Runs list: Filter bar (status/project/date), summary line with count, sort dropdown, zebra table, pagination with page size 15
- Analytics page: Time range tabs (7d/30d/90d/all), stat cards with deltas, stacked daily usage chart, by-project and by-phase horizontal bar breakdowns, by-model breakdown, budget progress bar, detailed breakdown table
- Cost summary strip on overview: Compact single-line preview with weekly cost, tokens, mini 7-day bar chart, "View Details" link to analytics
- Project cards: Name, run count, success rate (color-coded), cost — clickable to set global project filter with ring highlight on active

## FR Coverage Map

- FR1: Epic 1 — Aggregate statistics on main dashboard
- FR2: Epic 1 — Active runs list with project, feature, phase, elapsed time
- FR3: Epic 1 — Recent runs list with status, duration, relative time
- FR4: Epic 1 — Per-project breakdown (run count, success rate, tokens, cost)
- FR5: Epic 1 — Filter dashboard view to specific project
- FR6: Epic 1 — Auto-refresh at configurable interval without full page reload
- FR7: Epic 1 — More frequent refresh when active runs exist
- FR8: Epic 1 — Real-time phase progression for active runs (polling on overview)
- FR9: Epic 1 — Status indicators distinguishing running/completed/failed/interrupted/aborted
- FR10: Epic 1 — Elapsed time for active runs updates without manual refresh
- FR11: Epic 1 — Display when data was last refreshed
- FR12: Epic 3 — Start a new run (project selector + feature description)
- FR13: Epic 3 — Abort an active run with confirmation step
- FR14: Epic 3 — Start new run pre-populated from previous run (re-run)
- FR15: Epic 3 — Validate project exists and is registered before starting run
- FR16: Epic 2 — View detailed run metadata (ID, project, feature, status, timestamps, duration, phases)
- FR17: Epic 2 — View phase-by-phase progression with per-phase status indicators
- FR18: Epic 2 — Browse artifacts produced by each phase
- FR19: Epic 2 — View artifact content inline (text rendered in browser)
- FR20: Epic 2 — View run logs with most recent entries visible by default
- FR21: Epic 2 — Search run logs by keyword
- FR22: Epic 2 — Filter run logs by severity level
- FR23: Epic 2 — Stream logs in real-time for active runs
- FR24: Epic 2 — View artifacts path for a run to locate files on disk
- FR25: Epic 2 — View LLM prompts and responses with per-exchange token counts
- FR26: Epic 2 — View logs filtered by individual phase
- FR27: Epic 2 — Navigate to associated PR or Linear issue from completed run
- FR28: Epic 4 — Filter runs list by status
- FR29: Epic 4 — Filter runs list by date range
- FR30: Epic 4 — Sort runs list by any column
- FR31: Epic 4 — Paginate through run history
- FR32: Epic 5 — Select time range (7d/30d/90d/all) filtering all analytics data
- FR33: Epic 5 — Aggregate stat cards with delta indicators for selected range
- FR34: Epic 5 — Daily usage bar chart (stacked input/output tokens)
- FR35: Epic 5 — Token usage/cost broken down by project (horizontal bars)
- FR36: Epic 5 — Click project in breakdown to filter analytics page
- FR37: Epic 5 — Token usage/cost broken down by phase (horizontal bars)
- FR38: Epic 5 — Detailed breakdown table with sortable columns
- FR39: Epic 6 — Keyboard shortcuts (overlay, navigation, list nav, search focus)
- FR40: Epic 6 — Terminal mode (raw log output in monospace scrolling view)
- FR41: Epic 6 — Focus mode (single-run live view with phase progress + streaming logs)
- FR42: Epic 1 — View all registered projects with associated paths
- FR43: Epic 1 — Drill down from project into its recent runs
- FR44: Epic 1 — Per-project success rates and usage trends
- FR45: Epic 1 — Launch web dashboard from CLI
- FR46: Epic 1 — Auto-open browser when dashboard server starts
- FR47: Epic 1 — Configure server port
- FR48: Epic 1 — Serve dashboard on localhost by default
- FR49: Epic 1 — Dark mode as default appearance
- FR50: Epic 1 — Layout adapts to screen widths down to 1024px
- FR51: Epic 1 — Navigate between views without full page reload
- FR52: Epic 1 — Bookmark specific dashboard views via URL
- FR53: Epic 1 — CSRF protection on all mutation endpoints
