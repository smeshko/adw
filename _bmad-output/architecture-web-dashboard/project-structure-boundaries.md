# Project Structure & Boundaries

## Requirements-to-Architecture Mapping

**FR Category → Module/Directory:**

| FR Category | FRs | Primary Module | Secondary Modules |
|---|---|---|---|
| Dashboard Overview | FR1–FR7 | `dashboard/routes.py` (overview page) | `dashboard/partials.py` (polling fragments) |
| Run Monitoring | FR8–FR11 | `dashboard/sse.py` (live events) | `dashboard/partials.py` (active runs) |
| Run Management | FR12–FR15 | `dashboard/mutations.py` (start/abort) | `core/run_trigger.py` (extracted logic) |
| Run Inspection | FR16–FR27 | `dashboard/routes.py` (run detail page) | `dashboard/partials.py` (lazy-load panels) |
| Runs List & Filtering | FR28–FR31 | `dashboard/routes.py` (runs list page) | `dashboard/partials.py` (filtered table) |
| Cost & Token Analytics | FR32–FR38 | `dashboard/routes.py` (analytics page) | `dashboard/partials.py` (time range swap) |
| View Modes | FR39–FR41 | `dashboard/templates/` + `dashboard/static/` | Client-side JS in vendored HTMX extensions |
| Project Overview | FR42–FR44 | `dashboard/routes.py` (overview, project filter) | `dashboard/partials.py` (project drill-down) |
| Dashboard Infrastructure | FR45–FR53 | `cli/dashboard_web.py` + `server/app.py` | `server/config.py`, `dashboard/dependencies.py` |

**Cross-Cutting Concern → Location:**

| Concern | Location |
|---|---|
| Shared server factory | `server/app.py` |
| Server configuration | `server/config.py` |
| Shared middleware (request ID) | `server/middleware.py` |
| Data layer access (DI) | `dashboard/dependencies.py` |
| Run trigger (shared core) | `core/run_trigger.py` |
| CSRF protection | `dashboard/dependencies.py` (token validation) |
| HTML error handling | `dashboard/error_handlers.py` |
| Dashboard models (if needed) | `models/dashboard.py` |

## Complete Project Directory Structure

```
src/adw/
├── server/                              # NEW — Shared server infrastructure
│   ├── __init__.py
│   ├── app.py                           # create_app(features=[], config=) factory
│   ├── config.py                        # ServerConfig (host, port, features)
│   └── middleware.py                    # RequestIDMiddleware (shared)
│
├── dashboard/                           # NEW — Web dashboard feature
│   ├── __init__.py
│   ├── routes.py                        # Page routes: /, /runs, /runs/{id}, /analytics
│   ├── partials.py                      # Partial routes: /partials/* (polling targets)
│   ├── sse.py                           # SSE routes: /runs/{id}/events, /runs/{id}/logs/stream
│   ├── mutations.py                     # POST routes: /runs/start, /runs/{id}/abort
│   ├── dependencies.py                 # Depends() providers + CSRF validation
│   ├── error_handlers.py               # HTML exception handlers (banner + error page)
│   ├── templates/
│   │   ├── base.html                    # Full page shell: <head>, <header>, <main>, <footer>
│   │   ├── pages/
│   │   │   ├── overview.html            # FR1-7: Stats, active runs, recent runs, projects
│   │   │   ├── runs_list.html           # FR28-31: Filterable, sortable, paginated runs
│   │   │   ├── run_detail.html          # FR16-27: Full run inspection view
│   │   │   ├── analytics.html           # FR32-38: Cost & token analytics
│   │   │   └── error.html               # Full-page error display
│   │   ├── partials/
│   │   │   ├── stats_row.html           # FR1: Aggregate stat cards (polling: 30s)
│   │   │   ├── active_runs.html         # FR2,8-10: Active run cards (polling: 3s)
│   │   │   ├── recent_runs.html         # FR3: Recent runs table (polling: 15s)
│   │   │   ├── project_breakdown.html   # FR4: Per-project stats section
│   │   │   ├── status_bar.html          # FR11: Last refreshed + server status
│   │   │   ├── new_run_modal.html       # FR12,15: New run form (project selector)
│   │   │   ├── abort_modal.html         # FR13: Abort confirmation dialog
│   │   │   ├── phase_detail.html        # FR17: Lazy-loaded phase accordion content
│   │   │   ├── artifact_viewer.html     # FR18-19: Inline artifact content
│   │   │   ├── log_viewer.html          # FR20-23,26: Log entries w/ search+filter
│   │   │   ├── llm_viewer.html          # FR25: LLM prompt/response viewer
│   │   │   ├── analytics_content.html   # FR32: Time-range-filtered analytics swap
│   │   │   ├── error_banner.html        # HTMX error fragment
│   │   │   └── runs_table.html          # FR28-31: Filtered/sorted runs fragment
│   │   └── components/
│   │       ├── phase_pipeline.html      # Reusable phase progression visualization
│   │       ├── run_row.html             # Single run table row
│   │       ├── stat_card.html           # Single stat card
│   │       ├── status_badge.html        # Status icon + label (running/failed/etc)
│   │       ├── chart_bar.html           # CSS bar chart container
│   │       ├── project_card.html        # Project summary card
│   │       └── keyboard_help.html       # FR39: Keyboard shortcut overlay
│   └── static/
│       ├── htmx.min.js                  # Vendored HTMX 2.0.8 (~14KB)
│       ├── htmx-ext-sse.js              # Vendored HTMX SSE extension
│       └── dashboard.css                # Custom CSS (charts, animations, overrides)
│
├── core/                                # EXISTING — Extended
│   ├── run_trigger.py                   # NEW — Extracted from webhook/runner.py
│   ├── index_manager.py                 # EXISTING — no changes
│   ├── stats_aggregator.py              # EXISTING — no changes
│   ├── project_registry.py             # EXISTING — no changes
│   └── ...
│
├── models/                              # EXISTING — Extended
│   ├── dashboard.py                     # NEW — DashboardConfig (if needed)
│   └── ...
│
├── cli/                                 # EXISTING — Extended
│   ├── dashboard.py                     # EXISTING — TUI dashboard (unchanged)
│   ├── dashboard_web.py                 # NEW — `adw dashboard` / `adw global dashboard --web`
│   └── ...
│
├── webhook/                             # EXISTING — Refactored
│   ├── server.py                        # REFACTORED — delegates to server/app.py factory
│   ├── routes.py                        # UNCHANGED — webhook_router
│   ├── middleware.py                    # REFACTORED — convert to route dependency
│   ├── runner.py                        # REFACTORED — delegates to core/run_trigger.py
│   └── ...
│
└── ...
```

```
tests/
├── unit/
│   ├── server/                          # NEW — Shared server tests
│   │   ├── test_app.py                  # Factory tests (feature routing)
│   │   ├── test_config.py               # Server config tests
│   │   └── test_middleware.py           # RequestID middleware tests
│   │
│   ├── dashboard/                       # NEW — Dashboard unit tests
│   │   ├── test_routes.py               # Page route tests (dual-response)
│   │   ├── test_partials.py             # Partial route tests
│   │   ├── test_sse.py                  # SSE stream tests
│   │   ├── test_mutations.py            # Mutation route tests (CSRF)
│   │   ├── test_dependencies.py         # DI provider tests
│   │   └── test_error_handlers.py       # Error handler tests
│   │
│   ├── core/
│   │   ├── test_run_trigger.py          # NEW — Run trigger extraction tests
│   │   └── ...
│   │
│   ├── webhook/                         # EXISTING — updated for refactored code
│   │   └── ...
│   │
│   └── cli/
│       ├── test_dashboard.py            # EXISTING — TUI dashboard tests
│       ├── test_dashboard_web.py        # NEW — Web dashboard CLI tests
│       └── ...
│
├── integration/
│   └── dashboard/                       # NEW — Dashboard integration tests
│       ├── test_dashboard_server.py     # Full server lifecycle tests
│       ├── test_dashboard_polling.py    # HTMX polling integration
│       └── test_dashboard_sse.py        # SSE stream integration
│
└── fixtures/
    └── dashboard/                       # NEW — Dashboard test fixtures
        ├── sample_runs.json             # Pre-built run data for tests
        └── templates/                   # Template rendering test helpers
```

## Architectural Boundaries

**API Boundaries:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer                                 │
│  cli/dashboard_web.py ───► server/app.py(features=["dashboard"])│
│  cli/webhook.py       ───► server/app.py(features=["webhook"])  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────── server/app.py ──────────────────────────────┐
│  create_app() ─── includes routers based on features list       │
│                                                                  │
│  ┌────────── Dashboard Routers ──────────┐  ┌── Webhook ──────┐│
│  │ routes.py     → GET /, /runs, etc.    │  │ routes.py       ││
│  │ partials.py   → GET /partials/*       │  │   GET /health   ││
│  │ sse.py        → GET /runs/{id}/events │  │   POST /webhook ││
│  │ mutations.py  → POST /runs/*          │  └─────────────────┘│
│  │ static/       → /static/*            │                      │
│  └───────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Depends() injection
                              │
                              ▼
┌──────────────────── Data Layer (read-only) ─────────────────────┐
│  core/index_manager.py    → Run data (JSONL)                    │
│  core/stats_aggregator.py → Computed statistics (cached)        │
│  core/project_registry.py → Project list and config             │
│  core/run_trigger.py      → Run lifecycle (start/abort)         │
└─────────────────────────────────────────────────────────────────┘
```

**Component Boundaries:**

| Boundary | Rule | Enforcement |
|---|---|---|
| Dashboard → Data Layer | Always via `Depends()` in route functions | Never import managers directly in route handlers |
| Dashboard → Templates | Routes pass `dict` context, never raw objects | Templates receive pre-shaped data |
| Mutations → Run Trigger | `core/run_trigger.py` only — never import webhook code | Dashboard has zero imports from `webhook/` |
| SSE → Data Layer | Async generators poll `IndexManager` | No direct file system access from SSE |
| CLI → Server | CLI creates config, calls `create_app()`, runs uvicorn | CLI never defines routes or middleware |

**Data Boundaries:**

| Data Source | Owner | Access Pattern | Consumers |
|---|---|---|---|
| JSONL run index | `IndexManager` | Read via DI | Dashboard routes, partials, SSE |
| Cached statistics | `StatsAggregator` | Read via DI | Dashboard overview, analytics |
| Project registry | `ProjectRegistryManager` | Read via DI | Dashboard overview, new run form |
| Run artifacts | File system via `IndexManager` | Read via DI (path resolution) | Artifact viewer partial |
| Run logs | File system via `IndexManager` | Read via DI | Log viewer partial, SSE log stream |

## Requirements-to-Structure Detailed Mapping

**Dashboard Overview (FR1-7):**
- Page: `templates/pages/overview.html`
- Partials: `stats_row.html`, `active_runs.html`, `recent_runs.html`, `project_breakdown.html`
- Routes: `routes.py::overview()`, `partials.py::stats_row()`, `partials.py::active_runs()`, `partials.py::recent_runs()`
- Tests: `test_routes.py::TestOverview`, `test_partials.py::TestPollingPartials`

**Run Monitoring (FR8-11):**
- SSE: `sse.py::run_events()`, `sse.py::run_log_stream()`
- Partials: `active_runs.html` (phase indicator), `status_bar.html` (last refreshed)
- Components: `phase_pipeline.html`, `status_badge.html`
- Tests: `test_sse.py::TestRunEvents`, `test_partials.py::TestStatusBar`

**Run Management (FR12-15):**
- Mutations: `mutations.py::start_run()`, `mutations.py::abort_run()`
- Partials: `new_run_modal.html`, `abort_modal.html`
- Core: `core/run_trigger.py::RunTrigger`
- Dependencies: `dependencies.py::validate_csrf_token()`
- Tests: `test_mutations.py`, `tests/unit/core/test_run_trigger.py`

**Run Inspection (FR16-27):**
- Page: `templates/pages/run_detail.html`
- Partials: `phase_detail.html`, `artifact_viewer.html`, `log_viewer.html`, `llm_viewer.html`
- Routes: `routes.py::run_detail()`, `partials.py::phase_detail()`, `partials.py::artifact_content()`, `partials.py::log_entries()`, `partials.py::llm_exchange()`
- Tests: `test_routes.py::TestRunDetail`, `test_partials.py::TestLazyLoadPanels`

**Runs List & Filtering (FR28-31):**
- Page: `templates/pages/runs_list.html`
- Partial: `runs_table.html` (filtered/sorted/paginated fragment)
- Route: `routes.py::runs_list()`, `partials.py::runs_table()`
- Tests: `test_routes.py::TestRunsList`, `test_partials.py::TestRunsFiltering`

**Cost & Token Analytics (FR32-38):**
- Page: `templates/pages/analytics.html`
- Partial: `analytics_content.html` (time-range swap)
- Components: `chart_bar.html`, `stat_card.html`
- Route: `routes.py::analytics()`, `partials.py::analytics_content()`
- Tests: `test_routes.py::TestAnalytics`

**View Modes (FR39-41):**
- Component: `keyboard_help.html` (shortcut overlay)
- Static: `dashboard.css` (terminal mode styling, focus mode transitions)
- Template logic: `base.html` conditional classes for mode switching

**Project Overview (FR42-44):**
- Covered by overview page project breakdown + project filter query param
- Partial: `project_breakdown.html` with drill-down links
- Route: `routes.py::overview(project=...)`, `partials.py::project_breakdown()`

**Dashboard Infrastructure (FR45-53):**
- CLI: `cli/dashboard_web.py` (FR45-48: launch, browser open, port config, localhost)
- Template: `base.html` (FR49: dark mode via DaisyUI `data-theme`)
- Server: `server/app.py` (FR50-52: layout, navigation, URL bookmarks)
- Dependencies: `dependencies.py` (FR53: CSRF token validation)

## Integration Points

**Internal Communication:**

```
cli/dashboard_web.py
    └──► server/app.py::create_app(features=["dashboard"])
             └──► uvicorn.run(app, host=config.host, port=config.port)

dashboard/routes.py
    └──► Depends(get_index_manager) ──► core/index_manager.py
    └──► Depends(get_stats_aggregator) ──► core/stats_aggregator.py
    └──► Depends(get_project_registry) ──► core/project_registry.py
    └──► templates.TemplateResponse() ──► dashboard/templates/**

dashboard/mutations.py
    └──► Depends(validate_csrf_token) ──► dashboard/dependencies.py
    └──► Depends(get_run_trigger) ──► core/run_trigger.py

dashboard/sse.py
    └──► Depends(get_index_manager) ──► core/index_manager.py
    └──► StreamingResponse(event_stream())
```

**External Integrations:**
- **CDN (outbound):** DaisyUI CSS + Tailwind CSS browser runtime loaded in `base.html` `<head>`
- **Browser (inbound):** User's default browser opened on server start
- **File system:** Read-only access to `.adw/` run artifacts and logs via `IndexManager`

**Data Flow:**

```
[Browser] ──GET /──► [FastAPI routes.py] ──Depends()──► [IndexManager]
                                                         [StatsAggregator]
                                                         [ProjectRegistry]
                         │
                         ▼
              [Jinja2 templates] ──► [HTML Response] ──► [Browser DOM]
                                                              │
                                                    [HTMX polls partials]
                                                    [HTMX SSE subscribes]
```

## File Organization Patterns

**Source Organization:**
- Route modules are organized by response type (pages, partials, SSE, mutations), not by feature area
- Templates are organized by rendering context (pages for full views, partials for HTMX fragments, components for reusable pieces)
- Static assets are minimal: 2 vendored JS files + 1 custom CSS file

**Test Organization:**
- Unit tests mirror source structure: `tests/unit/dashboard/test_routes.py` ↔ `src/adw/dashboard/routes.py`
- Integration tests focus on server lifecycle and cross-component flows
- Dashboard fixtures provide pre-built run/stats data for template rendering tests

**Configuration:**
- `ServerConfig` in `server/config.py` holds host, port, features list
- Dashboard-specific config (polling intervals, theme) in `models/dashboard.py` if needed
- CLI flags in `cli/dashboard_web.py` map to `ServerConfig` fields
