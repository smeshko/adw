# Project Context Analysis

## Requirements Overview

**Functional Requirements:**

The PRD (in progress) and user-stated goals define the following functional scope for Phase 1:

| Category | Requirements | Architectural Implication |
|----------|-------------|--------------------------|
| Run Monitoring | Display recent runs, active runs, run details | Read-only API endpoints consuming IndexManager |
| Statistics | Global stats, per-project stats, token/cost tracking | API endpoints consuming StatsAggregator |
| Project Views | Project list, per-project breakdown | API endpoints consuming ProjectRegistryManager |
| Auto-Refresh | Live updates for active runs, periodic refresh | HTMX polling or SSE integration |
| Navigation | View switching (summary, runs, projects), run detail drill-down | Server-rendered page routes with HTMX partial swaps |
| Information Density | Cards, collapsible sections, progressive disclosure | Template design concern, not structural |

**Future Phase Requirements (shape architecture now, implement later):**

| Phase | Capability | Architectural Impact |
|-------|-----------|---------------------|
| Phase 2 | Start/stop/manage runs | Write API endpoints, async job management |
| Phase 3 | Linear integration, project config | External API clients, WebSocket/SSE for real-time |

**Non-Functional Requirements:**

| Category | Requirement | Constraint |
|----------|------------|------------|
| Tooling | Zero JavaScript build tooling | No npm, no bundlers — HTMX + server-rendered only |
| Stack | Python-only frontend | Jinja2 templates, CSS (no JS frameworks) |
| Data | Reuse existing data layer | No new databases, no new storage formats |
| Evolution | Grow from dashboard to command center | Architecture must support phases 2-3 without rewrites |
| Performance | Responsive auto-refresh | HTMX polling at 5s for active runs |
| Integration | Share FastAPI with webhooks cleanly | Single server process, isolated concerns |

**Scale & Complexity:**

- Primary domain: Server-rendered web dashboard extending existing CLI tool
- Complexity level: Low-Medium
- Language: Python 3.13+
- Package manager: uv
- Estimated architectural components: ~6 new modules (server infrastructure, dashboard routes, templates, static assets, dashboard models, dashboard CLI command)

## Technical Constraints & Dependencies

**Existing Infrastructure (must extend, not replace):**
- FastAPI webhook server with factory pattern (`webhook/server.py`)
- Webhook routes, middleware, provider system
- Data layer: IndexManager (JSONL), StatsAggregator (cached), ProjectRegistryManager

**New Dependencies Required:**
- Jinja2 (FastAPI template rendering)
- HTMX (vendored locally)
- DaisyUI 5 + Tailwind CSS v4 (CDN)

**Pre-existing Architecture Constraints (from project-context.md):**
- All models in `src/adw/models/`
- Exception hierarchy — no bare exceptions
- Full type annotations required
- Structured logging
- CLI layer: parse input, format output, delegate to core
- Core layer: all business logic, no CLI dependencies

## Cross-Cutting Concerns Identified

1. **Server Lifecycle & Ownership** — FastAPI app must be owned by shared infrastructure, not by webhooks or dashboard individually
2. **Routing Namespace Isolation** — Clean URL separation between webhook, dashboard, and API concerns
3. **Middleware Divergence** — Webhook logging middleware must not process dashboard requests; dashboard may need its own middleware
4. **Configuration Unification** — Shared server config (host, port, CORS) with per-feature config (webhook providers, dashboard settings)
5. **Error Response Format** — JSON for webhook/API routes, HTML for dashboard routes
6. **Static Asset Serving** — Dashboard requires CSS and potentially vendored HTMX
7. **Authentication Model** — Webhooks: HMAC signature verification. Dashboard: local-only for Phase 1, optional auth for future phases
