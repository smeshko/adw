---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
inputDocuments:
  - _bmad-output/prd.md
  - _bmad-output/analysis/product-brief-adw-sdk-2025-12-30.md
  - _bmad-output/index.md
  - _bmad-output/architecture.md
  - src/adw/cli/dashboard.py
  - src/adw/core/index_manager.py
  - src/adw/core/stats_aggregator.py
  - src/adw/core/project_registry.py
  - src/adw/webhook/server.py
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 7
workflowType: 'prd'
lastStep: 11
status: 'complete'
project_name: 'adw-sdk-web-dashboard'
user_name: 'Ivo'
date: '2026-02-10'
---

# Product Requirements Document - ADW Web Dashboard

**Author:** Ivo
**Date:** 2026-02-10

---

## Executive Summary

ADW Web Dashboard is a browser-based command center for the ADW SDK, replacing the terminal-based Rich TUI dashboard with a properly styled, information-dense web interface. While the existing TUI dashboard provides basic run monitoring, terminal rendering constraints limit information density, styling, and interactivity — making it difficult to surface rich data without clutter.

**Vision:** Evolve the dashboard from a read-only monitoring surface into a full command center where developers can monitor, control, and manage their ADW workflows — and eventually connect to external task managers like Linear.

**Core Problem:** The terminal is fundamentally limited as a dashboard medium. Fixed-width character rendering, no progressive disclosure, no hover states, and no multi-column layouts mean developers either see too little information or a cluttered wall of text. As ADW's feature set grows, the TUI cannot scale to surface the data developers need.

**Solution:** A FastAPI + HTMX server-rendered web dashboard that reuses ADW's existing data layer (`IndexManager`, `StatsAggregator`, `ProjectRegistryManager`) and FastAPI infrastructure. HTMX enables dynamic interactions with zero JavaScript build tooling, keeping the project firmly in Python-land.

**Scope:** This PRD covers both monitoring and interactive controls — the dashboard ships as a command center from day one, not a read-only view that gets upgraded later.

### What Makes This Special

1. **Information density without clutter** — Cards, collapsible sections, and progressive disclosure let developers see more at a glance without noise
2. **Zero JS build tooling** — HTMX + server-rendered templates keep the entire stack in Python, matching ADW's CLI-first philosophy
3. **Existing data layer** — No new data infrastructure needed; the web dashboard is a new view on proven data sources
4. **Command center from day one** — Monitor, control, and inspect runs without falling back to the CLI
5. **Developer-native aesthetic** — Purpose-built for ADW's data model (phases, artifacts, token costs, success rates), not a generic monitoring tool

## Project Classification

| Attribute | Value |
|-----------|-------|
| **Technical Type** | Web App (server-rendered) |
| **Domain** | Developer Tools |
| **Complexity** | Low-Medium |
| **Project Context** | Brownfield — extending existing ADW SDK |
| **Tech Stack** | FastAPI, HTMX, Jinja2, DaisyUI + Tailwind CSS |
| **Rendering** | Server-side with HTMX partial swaps |
| **Target Users** | ADW SDK users (solo devs, tech leads) |

---

## Success Criteria

### User Success

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Dashboard preference** | >70% of active ADW users switch to web dashboard within 30 days | CLI telemetry: `adw dashboard` web vs TUI invocations |
| **Glanceability** | Users find run status within 3 seconds of opening | Qualitative feedback from early adopters |
| **Terminal tab recovery** | Users no longer dedicate a terminal tab to dashboard | Self-reported workflow change |
| **Information satisfaction** | Users report the web dashboard surfaces enough information without clutter | NPS-style survey (>8/10) |
| **Run management adoption** | >50% of run start/stop actions happen via web dashboard | CLI telemetry: web vs CLI run management |

**The "I'm never going back" moment:** A developer opens the web dashboard, immediately sees their active run's phase progress alongside summary stats and recent history — then starts a new run directly from the browser without switching to a terminal.

### Business Success

**3-Month Goals:**
- Web dashboard ships as part of ADW distribution (no separate install)
- 80%+ of active ADW users have tried the web dashboard
- Foundation architecture supports post-MVP features without rewrites

**6-Month Goals:**
- Dashboard becomes the primary ADW monitoring and control surface
- Positive community feedback drives new ADW adoption
- Post-MVP features (task manager integration) can be scoped confidently

### Technical Success

| Metric | Target |
|--------|--------|
| **Page load time** | <500ms initial load |
| **Refresh latency** | <200ms for HTMX partial swaps |
| **Zero JS build step** | No node_modules, no webpack/vite, no transpilation |
| **Data layer reuse** | No modifications to IndexManager, StatsAggregator, or ProjectRegistryManager |
| **Test coverage** | >80% for new dashboard code (API routes, template rendering) |
| **No new system dependencies** | Only Python packages (Jinja2, HTMX served as static file) |

### Measurable Outcomes

- **MVP success gate:** Users can monitor AND control ADW workflows from the browser, preferring it over CLI for day-to-day operations
- **Go/No-Go for post-MVP:** >50% of weekly active users managing runs primarily through the web dashboard
- **Architecture validation:** Post-MVP features (task manager, project config) can be added without restructuring MVP code

## Product Scope

### MVP (This PRD)

**Monitoring & Display:**
1. **Summary statistics panel** — Total runs, success rate, avg duration, token usage, estimated cost
2. **Active runs display** — Running jobs with project, feature, phase, elapsed time
3. **Recent runs table** — Status-coded list with project, feature, status, duration, relative timestamp
4. **Per-project breakdown** — Project-level stats (runs, success rate, tokens, cost)
5. **Run detail view** — Click-to-expand with full metadata, phase progression, artifacts path
6. **Auto-refresh** — Polling for active run updates (configurable interval)

**Interactive Controls:**
7. **Start new runs** — Project selector + feature description input
8. **Abort/stop active runs** — With confirmation dialog
9. **Artifact browser** — View phase outputs inline
10. **Log viewer** — Searchable, filterable run logs
11. **Run comparison** — Diff two runs side by side

**Cost & Token Analytics:**
12. **Analytics page** — Dedicated page with time range filtering, stat cards, daily usage chart, project/phase breakdowns, and detailed table (see UI Specifications)

**UX & Infrastructure:**
13. **Dark mode** — Developer-native aesthetic, dark by default
14. **CLI launch** — `adw global dashboard --web` or `adw web` command
15. **Responsive layout** — Usable on laptop screens (no mobile requirement)

### Post-MVP (Future)

- Task manager integration (Linear issues as run sources)
- Project configuration editor
- Prompt template browser and editor
- Team view (multiple developer activity)
- Webhook status and configuration

---

## User Journeys

### Journey 1: Alex Torres — Fire and Forget

Alex is deep in a refactoring sprint on his side project, a meal planning SaaS he's been building nights and weekends. He's got three features queued up in Linear and a two-hour window before dinner. He opens his browser, navigates to localhost:8100 where the ADW dashboard is already running, and immediately sees the summary cards — 47 runs this week, 82% success rate, $12.40 in token costs. Not bad.

He clicks "New Run", selects his meal-planner project from the dropdown, and types: "Add Stripe subscription management with trial period support." He hits Start, watches the status flip to "running" with the phase indicator showing "Plan", and then minimizes the browser. Time to work on feature two from the terminal.

Twenty minutes later, a glance at the dashboard tab shows the run is in "Validate" phase — tests are running. He doesn't touch it. By the time he finishes his second feature manually, the dashboard shows a green checkmark: run complete, all phases passed, PR ready. He clicks into the run detail, scans the phase progression timeline, sees 0 test failures and a clean diff, and moves on to feature three. Three features in two hours — one fully automated, two manual. The automated one produced better documentation.

**This journey reveals requirements for:**
- Summary statistics panel (glanceable health)
- New Run form (project selector + feature input)
- Active run status with phase indicator
- Run detail view with phase progression timeline
- Status transitions visible without manual refresh

### Journey 2: Alex Torres — The Debug Detective

It's the next morning and Alex opens the dashboard to check on an overnight run he kicked off for a complex database migration feature. The recent runs table shows it immediately — a red X on "Add multi-tenant data isolation." Status: failed. Phase: Build.

He clicks into the run detail. The phase progression shows Plan completed successfully (green), then Build failed (red). He opens the log viewer, which shows the last 50 lines of build output. The LLM tried to modify a migration file that doesn't exist in his project — it hallucinated a file path. He filters the logs by "error" and sees the exact moment it went wrong.

He switches to the artifact browser and opens the Plan phase output. The plan looks reasonable, but step 4 references `migrations/0003_tenant_isolation.py` — a file that should have been created, not modified. The plan was subtly wrong. Alex now knows exactly what to fix: he'll update his plan phase prompt to include the current migration file listing as context.

He clicks "New Run" with a refined feature description that includes explicit constraints, and starts it again. This time he watches the Build phase from the log viewer in real-time, streaming output as it happens. It passes. Twenty minutes of debugging instead of an hour of digging through `.adw/runs/` directories in the terminal.

**This journey reveals requirements for:**
- Recent runs table with clear failure indicators
- Run detail with phase-by-phase status (green/red progression)
- Log viewer with filtering and search
- Artifact browser for phase outputs
- Real-time log streaming for active runs
- Quick "re-run" or "new run" flow from a failed run context

### Journey 3: Alex Torres — The Comparison Shopper

Alex has been experimenting with different prompt strategies for his Build phase. He ran the same feature twice — once with his default prompts and once with a custom prompt that includes more architectural context. Both runs completed successfully, but he wants to know which produced better results.

He opens the dashboard, selects both runs from the recent runs table, and clicks "Compare." The side-by-side view shows him the key differences: Run A took 3 minutes and used 45K tokens. Run B took 4.5 minutes, used 68K tokens, but the Build phase artifacts show more comprehensive test coverage and better error handling. The phase-by-phase comparison makes it obvious — the extra context in Run B's prompt led to more thorough code generation at a modest cost increase.

Alex updates his project's default Build prompt to include the architectural context. From now on, every run benefits from what he learned in this comparison.

**This journey reveals requirements for:**
- Multi-select runs for comparison
- Side-by-side run comparison view
- Phase-by-phase metric comparison (duration, tokens, cost)
- Artifact diff between comparable phases

### Journey 4: Jordan Kim — The Team Pulse Check

Jordan leads a team of five developers who've been using ADW for the past month. Every Monday morning, she opens the dashboard to get a pulse on how the team's AI-assisted development is going. The per-project breakdown panel tells the story at a glance — the auth-service project has a 91% success rate across 34 runs, while the payments-service is struggling at 58% across 19 runs.

She clicks into the payments-service breakdown and scans the recent runs. A pattern jumps out: most failures are in the Validate phase. Tests keep failing. She drills into one of the failed runs and sees the log — the LLM-generated code doesn't follow the team's testing conventions. Jordan makes a mental note to update the payments-service Build prompt to include test file examples.

She checks the summary stats — the team has spent $89.40 on tokens this week across 67 runs. The average run takes 8 minutes. She compares this to the first week (23 runs, 12-minute average, 44% success rate) and sees clear improvement. The dashboard gives her the data she needs for her engineering update without asking each developer to self-report.

**This journey reveals requirements for:**
- Per-project breakdown with success rate trends
- Project-level drill-down to recent runs
- Aggregate cost and usage metrics
- Historical comparison (implied — post-MVP, but shapes data model)
- Multi-project view as the default landing state

### Journey Requirements Summary

| Capability | Journeys | Priority |
|-----------|----------|----------|
| Summary statistics panel | 1, 4 | Must have |
| Active runs with phase indicator | 1, 2 | Must have |
| Recent runs table with status | 1, 2, 4 | Must have |
| Per-project breakdown | 4 | Must have |
| Run detail with phase progression | 1, 2 | Must have |
| New Run form (project + feature) | 1, 2 | Must have |
| Abort/stop active runs | 1 | Must have |
| Log viewer with search/filter | 2 | Must have |
| Real-time log streaming | 2 | Must have |
| Artifact browser | 2 | Must have |
| Run comparison (side-by-side) | 3 | Must have |
| Auto-refresh / live updates | 1, 2 | Must have |
| Dark mode | All | Must have |

---

## Web Application Specific Requirements

### Project-Type Overview

The ADW Web Dashboard is a server-rendered web application using FastAPI + HTMX + Jinja2 templates. It serves as a localhost dashboard for developers — not a public-facing SaaS. This significantly simplifies requirements around SEO, authentication, multi-tenancy, and browser compatibility.

The rendering model is server-side HTML with HTMX-driven partial page swaps. This provides SPA-like interactivity (no full page reloads, smooth transitions) while keeping all logic server-side and eliminating the need for a JavaScript build pipeline.

### Browser Support

| Browser | Support Level |
|---------|--------------|
| Chrome (latest 2) | Full support |
| Firefox (latest 2) | Full support |
| Safari (latest 2) | Full support |
| Edge (latest 2) | Full support |
| IE11 / Legacy | Not supported |
| Mobile browsers | Not targeted (no mobile requirement) |

### Responsive Design

- **Primary target:** Laptop screens (1280px+)
- **Minimum supported:** 1024px width
- **No mobile requirement:** Dashboard is a developer tool accessed from workstations
- **Layout strategy:** CSS Grid for dashboard panels, flex for internal components
- **Breakpoints:** Single responsive breakpoint at 1024px for compact layout

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Initial page load | <500ms | Server-rendered, no JS bundle to download |
| HTMX partial swap | <200ms | Server responds with HTML fragment |
| Time to interactive | <500ms | No hydration step needed |
| Auto-refresh cycle | <100ms render | Polling interval configurable (5s-60s) |
| Static assets | Cached aggressively | HTMX lib (~14KB), Tailwind CSS, minimal static files |

### SEO Strategy

Not applicable. The dashboard runs on localhost and is not publicly accessible. No search engine optimization, meta tags, sitemap, or robots.txt required.

### Accessibility Level

- **Target:** WCAG 2.1 Level A (basic compliance)
- **Semantic HTML:** Proper heading hierarchy, landmarks, form labels
- **Keyboard navigation:** All interactive elements reachable via Tab/Enter
- **Color contrast:** Minimum 4.5:1 ratio for text (naturally achieved with dark theme)
- **Screen reader:** Basic aria-labels on interactive elements; full screen reader optimization is post-MVP
- **No animation reliance:** All state changes communicated through text/color, not animation alone

### Implementation Considerations

**Server Architecture:**
- FastAPI application mounted alongside or separate from existing webhook server
- Jinja2 template engine for server-side rendering
- HTMX served as a static file (~14KB gzipped)
- DaisyUI + Tailwind CSS via CDN or pre-built static file (no build step)

**State Management:**
- No client-side state — all state lives server-side in the existing data layer
- HTMX handles DOM updates via server responses
- Browser URL reflects current view for bookmarkability

**Security:**
- Localhost-only by default (bind to 127.0.0.1)
- No authentication required for v1 (single-user, local machine)
- CSRF protection on mutation endpoints (start/stop runs)
- Optional `--host` flag for LAN access (future consideration)

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Platform MVP — Build the dashboard as a complete command center foundation from day one, avoiding the cost of re-launching a "v2" that adds interactivity later.

**Rationale:** ADW already has an established user base with the CLI. The web dashboard needs to be immediately *better* than the TUI to justify adoption. A read-only dashboard would feel like a downgrade in capability (can't start runs), even if it looks nicer. Shipping monitoring + controls together means users can fully switch their workflow on day one.

**Resource Requirements:** Solo developer (Ivo), leveraging existing data layer. No new infrastructure. Estimated scope: medium — the data layer exists, the work is primarily API routes + templates + styling.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Journey 1 (Fire and Forget) — Full support
- Journey 2 (Debug Detective) — Full support
- Journey 3 (Comparison Shopper) — Deferred (run comparison moved to post-MVP)
- Journey 4 (Team Pulse Check) — Partial support (multi-project view yes, historical trends post-MVP)

**Must-Have Capabilities (53 FRs across 9 capability areas):**

See Functional Requirements section for complete list. Key feature groups:

| Group | Features | Journeys |
|-------|----------|----------|
| Dashboard Overview | Stats, active runs, recent runs, project breakdown | 1, 4 |
| Run Monitoring | Phase progression, status indicators, live updates | 1, 2 |
| Run Management | Start, abort, re-run | 1, 2 |
| Run Inspection | Detail view, artifacts, logs, LLM interactions | 2 |
| Runs List & Filtering | Status/date filters, sorting, pagination | 2, 4 |
| Cost & Token Analytics | Time range filtering, stat cards, daily chart, project/phase breakdown, detailed table | 4 |
| View Modes | Keyboard shortcuts, terminal mode, focus mode | All |
| Project Overview | Project list, drill-down, health trends | 4 |
| Dashboard Infrastructure | CLI launch, dark mode, responsive, CSRF | All |

**Scope risk:** Cost & Token Analytics (FR32-38) is the most feature-rich capability area. If scope pressure hits, the detailed breakdown table (FR38) is the first candidate to defer.

### Post-MVP Features

**Phase 2 (Growth):**
- Run comparison (side-by-side view, metric/artifact diff)
- Task manager integration (Linear issues as run sources)
- Project configuration editor (edit `.adw/project.yaml` from browser)
- Light/dark theme toggle

**Phase 3 (Expansion):**
- Prompt template browser and editor
- Team view (multi-developer activity across projects)
- Webhook status and configuration management
- Authentication for LAN/remote access
- Notification system (browser notifications on run completion)

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HTMX limitations for complex interactions (comparison view, log streaming) | Medium | Medium | Prototype comparison view early; SSE fallback for streaming |
| DaisyUI + Tailwind CSS via CDN adds external dependency | Low | Low | Pre-build static CSS file as fallback; bundle in package |
| FastAPI server conflicts with existing webhook server | Low | Medium | Separate server on different port, or mount as sub-application |

**Market Risks:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Users prefer CLI and don't adopt dashboard | Medium | High | Ship as opt-in alongside TUI, not replacement; gather feedback early |
| Feature scope too large for solo developer | Medium | Medium | Run comparison is deferrable; core monitoring + controls are well-scoped |

**Resource Risks:**

| Risk | Mitigation |
|------|------------|
| Solo developer bandwidth | Core 14 features (excluding comparison) are independently shippable |
| Minimum viable release | Features 1-8 + 13-15 (monitoring + basic controls + infrastructure) could ship as early access |

---

## Functional Requirements

### Dashboard Overview

- **FR1:** User can view aggregate statistics (total runs, success rate, average duration, total token usage, estimated cost) on the main dashboard
- **FR2:** User can view a list of currently active runs with their project, feature description, current phase, and elapsed time
- **FR3:** User can view a list of recent runs with their project, feature description, status, duration, and relative start time
- **FR4:** User can view a per-project breakdown showing each registered project's run count, success rate, token usage, and estimated cost
- **FR5:** User can filter the dashboard view to a specific project
- **FR6:** Dashboard automatically refreshes data at a configurable interval without full page reload
- **FR7:** Dashboard refreshes more frequently when active runs exist

### Run Monitoring

- **FR8:** User can see real-time phase progression for active runs (which phase is currently executing)
- **FR9:** User can see status indicators that visually distinguish running, completed, failed, interrupted, and aborted runs
- **FR10:** User can see elapsed time for active runs that updates without manual refresh
- **FR11:** User can see when data was last refreshed

### Run Management

- **FR12:** User can start a new run by selecting a registered project and providing a feature description
- **FR13:** User can abort an active run with a confirmation step
- **FR14:** User can start a new run pre-populated with context from a previous run (re-run flow)
- **FR15:** System validates that the selected project exists and is registered before starting a run

### Run Inspection

- **FR16:** User can view detailed metadata for any run (run ID, project, feature, status, timestamps, duration, phase history)
- **FR17:** User can view phase-by-phase progression for a run with per-phase status indicators (success/failure)
- **FR18:** User can browse artifacts produced by each phase of a run
- **FR19:** User can view artifact content inline (text-based artifacts rendered in the browser)
- **FR20:** User can view run logs with the most recent entries visible by default
- **FR21:** User can search run logs by keyword
- **FR22:** User can filter run logs by severity level
- **FR23:** User can stream logs in real-time for an active run
- **FR24:** User can view the artifacts path for a run to locate files on disk
- **FR25:** User can view LLM prompts sent and responses received for each phase, with per-exchange token counts
- **FR26:** User can view logs filtered by individual phase
- **FR27:** User can navigate to the associated PR or Linear issue from a completed run

### Runs List & Filtering

- **FR28:** User can filter the runs list by status (running, completed, failed, interrupted, aborted)
- **FR29:** User can filter the runs list by date range
- **FR30:** User can sort the runs list by any column (status, project, duration, date)
- **FR31:** User can paginate through run history

### Cost & Token Analytics

- **FR32:** User can select a time range (7 days, 30 days, 90 days, All time) that filters all analytics data on the page via HTMX partial swap
- **FR33:** User can view aggregate stat cards for the selected time range: total tokens, total cost, average tokens per run, and total runs — each with a delta indicator showing change from the previous period
- **FR34:** User can view a daily usage bar chart showing token consumption per day, with stacked bars distinguishing input tokens from output tokens
- **FR35:** User can view token usage and cost broken down by project as a horizontal bar chart, with percentage distribution
- **FR36:** User can click a project in the By Project breakdown to filter the entire analytics page to that project
- **FR37:** User can view token usage and cost broken down by phase (Build, Plan, Validate, Document, Ship) as a horizontal bar chart with percentage distribution
- **FR38:** User can view a detailed breakdown table showing per-project metrics (runs, tokens, cost, avg tokens/run) with sortable columns

### View Modes

- **FR39:** User can navigate the dashboard using keyboard shortcuts (shortcut overlay, list navigation, search focus)
- **FR40:** User can toggle a terminal mode that displays raw log output in a monospace scrolling view
- **FR41:** User can enter focus mode on an active run, replacing the dashboard with a single-run live view showing phase progress and streaming logs

### Project Overview

- **FR42:** User can view all registered projects with their associated paths
- **FR43:** User can drill down from a project into its recent runs
- **FR44:** User can see per-project success rates and usage trends

### Dashboard Infrastructure

- **FR45:** User can launch the web dashboard from the CLI
- **FR46:** System automatically opens the user's default browser when the dashboard server starts
- **FR47:** User can configure the server port
- **FR48:** System serves the dashboard on localhost by default (127.0.0.1)
- **FR49:** User can customize the dashboard appearance (dark mode as default)
- **FR50:** Dashboard layout adapts to screen widths down to 1024px
- **FR51:** User can navigate between dashboard views without full page reload
- **FR52:** User can bookmark specific dashboard views via URL
- **FR53:** System provides CSRF protection on all mutation endpoints

---

## Non-Functional Requirements

### Performance

- **NFR1:** Initial page load completes in <500ms (server-rendered, no JS bundle)
- **NFR2:** HTMX partial swaps complete in <200ms (server response time)
- **NFR3:** Auto-refresh polling does not degrade page responsiveness
- **NFR4:** Log streaming for active runs displays output within 1 second of generation
- **NFR5:** Dashboard remains responsive with 1000+ runs in the index
- **NFR6:** Static assets (HTMX, DaisyUI/Tailwind CSS) are served with aggressive caching headers
- **NFR7:** SSE connections for live run updates consume minimal server resources

### Security

- **NFR8:** Dashboard server binds to 127.0.0.1 by default (localhost only)
- **NFR9:** All mutation endpoints (start run, abort run) include CSRF protection
- **NFR10:** Dashboard does not expose file system paths beyond what the existing data layer provides
- **NFR11:** No API keys, secrets, or credentials are logged or displayed in the dashboard UI
- **NFR12:** If `--host 0.0.0.0` is used for LAN access, a warning is displayed at startup

### Reliability

- **NFR13:** Dashboard server handles malformed or corrupted index entries gracefully without crashing
- **NFR14:** Dashboard remains functional when no projects are registered (empty state)
- **NFR15:** Dashboard remains functional when no runs exist (empty state)
- **NFR16:** Failed HTMX requests display a user-visible error indicator, not a silent failure
- **NFR17:** Dashboard server recovers gracefully from data layer errors (file locks, missing files)
- **NFR18:** SSE connections automatically reconnect after network interruption
- **NFR19:** Starting/aborting a run from the dashboard handles concurrent CLI operations without data corruption

### Maintainability

- **NFR20:** New dashboard code maintains >80% test coverage (API routes, template rendering logic)
- **NFR21:** Jinja2 templates use a component/partial structure that enables reuse across pages
- **NFR22:** API routes are organized by capability area matching the FR structure
- **NFR23:** All API endpoints return both full-page and HTMX-partial responses based on request headers
- **NFR24:** Dashboard code follows existing ADW project conventions (type hints, Pydantic models, pytest)

### Integration

- **NFR25:** Dashboard reads from the same data sources as the TUI dashboard (IndexManager, StatsAggregator, ProjectRegistryManager) without modifications
- **NFR26:** Starting a run from the dashboard produces identical results to starting via CLI
- **NFR27:** Dashboard server can run concurrently with the existing webhook server without port conflicts
- **NFR28:** Dashboard CLI command follows existing ADW CLI patterns (Typer, consistent flags and help text)

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web framework | FastAPI | Already a project dependency; async support for SSE |
| Template engine | Jinja2 | Standard Python templating; FastAPI native support |
| Interactivity | HTMX | Server-rendered partials; no JS build step; ~14KB |
| Component library | DaisyUI + Tailwind CSS | Pre-built components (cards, tables, modals, badges); no JS; clean dark theme |
| Live updates | SSE (Server-Sent Events) | Native FastAPI support; no WebSocket complexity; HTMX SSE extension |
| CSS delivery | CDN with static fallback | Zero build step; offline fallback bundled in package |
| Server binding | 127.0.0.1:8100 | Avoids conflict with webhook server (8000); localhost-only by default |

---

*PRD completed on 2026-02-10. Updated 2026-02-11: Cost & Token Analytics UI specification added (FR32-40). ADW Web Dashboard — 53 functional requirements, 28 non-functional requirements, 4 user journeys, 9 capability areas.*
