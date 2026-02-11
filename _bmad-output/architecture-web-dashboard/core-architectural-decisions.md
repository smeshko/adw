# Core Architectural Decisions

## Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Shared Server Architecture: APIRouter composition with feature-based factory
- Server Process Model: Separate processes, shared factory (dashboard :8100, webhook :8000)
- Data Layer Access: FastAPI dependency injection
- Middleware Strategy: Webhook middleware → route dependency; global middleware only for shared concerns
- Run Management: Extract trigger logic to shared `core/run_trigger.py`
- Dual-Response Pattern: Same URL returns full page or HTMX fragment via `HX-Request` header
- SSE for Live Updates: `/runs/{id}/events` and `/runs/{id}/logs/stream`
- CSRF Protection: Token-based on all mutation endpoints

**Important Decisions (Shape Architecture):**
- Template Organization: pages/ + partials/ + components/ hierarchy
- CSS-Only Charts: Server-rendered bar charts via CSS flex/height, no JS charting library
- Polling Strategy: 3s active runs, 15s recent runs, 30s stats (from UX spec)
- URL Structure: Hub-and-spoke navigation per UX spec

**Deferred Decisions (Post-MVP):**
- Authentication for LAN/remote access
- WebSocket upgrade path (SSE sufficient for MVP)
- Run comparison UI
- Task manager integration architecture

## Shared Server Architecture

**Decision:** APIRouter Composition with Feature-Based Factory

A shared `server/app.py` factory creates the FastAPI application and includes routers based on configuration. Both webhook and dashboard use the same factory, same config loading, same patterns — but run as separate server processes on different ports.

**Factory Pattern:**

```python
# server/app.py
def create_app(*, features: list[str], config: ServerConfig) -> FastAPI:
    app = FastAPI(title="ADW Server")

    # Shared infrastructure
    app.add_middleware(RequestIDMiddleware)

    # Feature-based router inclusion
    if "webhook" in features:
        from adw.webhook.routes import webhook_router
        app.include_router(webhook_router, prefix="/webhook")

    if "dashboard" in features:
        from adw.dashboard.routes import dashboard_router
        from adw.dashboard.partials import partials_router
        from adw.dashboard.sse import sse_router
        app.include_router(dashboard_router)
        app.include_router(partials_router, prefix="/partials")
        app.include_router(sse_router)
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    return app
```

**CLI Integration:**

- `adw webhook start` → `create_app(features=["webhook"], ...)` on :8000
- `adw dashboard` → `create_app(features=["dashboard"], ...)` on :8100

**Rationale:** APIRouter is the standard FastAPI pattern. Feature-based factory means each CLI command gets exactly the routes it needs. No webhook code loaded when running dashboard only, and vice versa. Both share the same server infrastructure (config, request ID middleware, error handling patterns).

## Server Process Model

**Decision:** Separate Processes, Shared Infrastructure

Dashboard and webhook run as independent processes on different ports (NFR27). They share the `server/` module for factory, config, and middleware — but they are independent at runtime.

**Port Assignment:**

| Process | Default Port | CLI Command |
|---------|-------------|-------------|
| Dashboard | 8100 | `adw dashboard` (or `adw global dashboard --web`) |
| Webhook | 8000 | `adw webhook start` |

**Rationale:** NFR27 requires concurrent operation without port conflicts. Separate processes means either can run independently. The shared factory ensures both follow identical patterns for config loading, error handling, and middleware.

## Middleware Strategy

**Decision:** Webhook Logging → Route Dependency; Global Middleware Only for Shared Concerns

**Global Middleware (in `server/app.py`):**
- `RequestIDMiddleware` — generates/extracts request IDs for all routes

**Route-Scoped Dependencies:**
- Webhook logging → `Depends(log_webhook_request)` on webhook router
- Dashboard-specific concerns → dependencies on dashboard router

**Rationale:** Middleware in FastAPI/Starlette is global by nature. Route-scoped concerns belong in dependencies. This is the standard FastAPI pattern and prevents webhook logging from processing dashboard requests.

## Data Layer Access

**Decision:** FastAPI Dependency Injection

Dashboard routes access `IndexManager`, `StatsAggregator`, and `ProjectRegistryManager` via FastAPI's `Depends()` mechanism.

**Pattern:**

```python
# dashboard/dependencies.py
from adw.core.index_manager import IndexManager
from adw.core.stats_aggregator import StatsAggregator
from adw.core.project_registry import ProjectRegistryManager

def get_index_manager() -> IndexManager:
    return IndexManager()

def get_stats_aggregator() -> StatsAggregator:
    return StatsAggregator()

def get_project_registry() -> ProjectRegistryManager:
    return ProjectRegistryManager()

# dashboard/routes.py
@router.get("/")
async def overview(
    request: Request,
    index: IndexManager = Depends(get_index_manager),
    stats: StatsAggregator = Depends(get_stats_aggregator),
    registry: ProjectRegistryManager = Depends(get_project_registry),
):
    ...
```

**Rationale:** Standard FastAPI pattern. Testable (swap dependencies in tests). Decoupled from app state. The webhook module can migrate to this pattern later.

## Routing Architecture

**Decision:** Hub-and-Spoke Navigation with Dual-Response Pattern (from UX Spec)

**Page Routes (dual response via `HX-Request` header):**

| Route | Page | Query Params |
|-------|------|-------------|
| `GET /` | Overview | `?project={name}` |
| `GET /runs` | Runs List | `?project=`, `?status=`, `?from=`, `?to=`, `?sort=`, `?page=` |
| `GET /runs/{run_id}` | Run Detail | — |
| `GET /analytics` | Analytics | `?range=7d|30d|90d|all`, `?project=` |

**Partial Routes (always return HTML fragments):**

| Route | Purpose | Polling |
|-------|---------|---------|
| `GET /partials/active-runs` | Active runs section | every 3s |
| `GET /partials/stats` | Stats row | every 30s |
| `GET /partials/recent-runs` | Recent runs table | every 15s |
| `GET /partials/status-bar` | Footer status | every 10s |
| `GET /partials/new-run` | New run modal | on demand |
| `GET /partials/abort/{id}` | Abort confirmation modal | on demand |
| `GET /runs/{id}/phases/{phase}` | Phase detail (lazy-load) | on demand |
| `GET /runs/{id}/artifacts/{path}` | Artifact content | on demand |
| `GET /runs/{id}/phases/{phase}/prompt` | LLM prompt text | on demand |
| `GET /runs/{id}/phases/{phase}/response` | LLM response text | on demand |
| `GET /runs/{id}/logs` | Log entries (search/filter) | on demand |

**SSE Streams:**

| Route | Events | Purpose |
|-------|--------|---------|
| `GET /runs/{id}/events` | `phase-update`, `run-complete`, `run-failed` | Live phase progression |
| `GET /runs/{id}/logs/stream` | `log-line` | Real-time log streaming |

**Mutation Routes (CSRF protected):**

| Route | Purpose |
|-------|---------|
| `POST /runs/start` | Start a new run |
| `POST /runs/{id}/abort` | Abort an active run |

**Webhook Routes (unchanged, on webhook server):**

| Route | Purpose |
|-------|---------|
| `GET /health` | Health check |
| `POST /webhook/{provider}` | Webhook receiver |

## Run Management from Dashboard

**Decision:** Extract Trigger Logic to Shared Core

The existing `WebhookRunTrigger` in `webhook/runner.py` spawns detached subprocesses to run ADW commands. This logic is extracted to `core/run_trigger.py` so both webhook and dashboard can trigger runs without depending on each other.

**Pattern:**

```python
# core/run_trigger.py (extracted from webhook/runner.py)
class RunTrigger:
    async def start_run(self, project_path: str, feature: str) -> str:
        """Start an ADW run, return the run ID."""
        ...

    async def abort_run(self, run_id: str) -> bool:
        """Abort an active run."""
        ...
```

**Rationale:** Dashboard needs to start/abort runs (FR12, FR13). Webhook already has this logic. Extracting to core prevents dashboard → webhook dependency and follows the existing boundary rules (core layer contains business logic).

## CSRF Protection

**Decision:** Token-Based CSRF via Hidden Form Input

All mutation endpoints (`POST /runs/start`, `POST /runs/{id}/abort`) include a CSRF token as a hidden form field. The token is generated server-side and validated on submission.

**Implementation:** Use a lightweight approach — generate a per-session token stored server-side (in-memory dict or signed cookie), include as `<input type="hidden" name="csrf_token">` in forms. Validate on POST.

**Rationale:** FR53 and NFR9 require CSRF protection. Since this is a localhost tool, the threat model is limited, but CSRF protection is good practice for mutation endpoints. No third-party library needed — FastAPI + Python `secrets` module suffice.

## SSE Implementation

**Decision:** FastAPI StreamingResponse with HTMX SSE Extension

SSE endpoints use FastAPI's `StreamingResponse` to push HTML fragments. The HTMX SSE extension (`htmx-ext-sse`) handles client-side connection management, auto-reconnect, and DOM swapping.

**Pattern:**

```python
# dashboard/sse.py
from starlette.responses import StreamingResponse

@router.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    async def event_stream():
        while True:
            # Check run status, yield SSE events
            yield f"event: phase-update\ndata: {html_fragment}\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Client-side (from UX spec):**
```html
<div hx-ext="sse" sse-connect="/runs/{id}/events" sse-swap="phase-update">
```

**Rationale:** Native FastAPI/Starlette support. No WebSocket complexity. HTMX SSE extension handles reconnect automatically (NFR18). SSE events carry HTML fragments that swap directly into the DOM — no client-side parsing needed.

## Charts

**Decision:** CSS-Only Bar Charts (from UX Spec)

All charts in the analytics page are rendered server-side as CSS flex containers with percentage-based heights. No JavaScript charting library.

**Pattern (from UX spec section 7.3):**

```html
<div class="chart-daily flex items-end gap-1 h-40">
  <div class="chart-bar flex flex-col justify-end w-full">
    <div class="bg-primary" style="height: 62%"></div>
    <div class="bg-primary/40" style="height: 38%"></div>
    <span class="text-xs text-center mt-1">M</span>
  </div>
</div>
```

**Rationale:** Aligns with zero-JS-build philosophy. Bar charts are simple enough for CSS. Server calculates percentages. UX spec design decision log confirms this choice.

## Template Organization

**Decision:** Pages + Partials + Components Hierarchy

```
dashboard/templates/
├── base.html              # Full page shell (head, header, main, footer)
├── pages/
│   ├── overview.html      # Overview content
│   ├── runs_list.html     # Runs list content
│   ├── run_detail.html    # Run detail content
│   └── analytics.html     # Analytics content
├── partials/
│   ├── stats_row.html     # Polling target (overview stats)
│   ├── active_runs.html   # Polling target (active runs cards)
│   ├── recent_runs.html   # Polling target (recent runs table)
│   ├── status_bar.html    # Polling target (footer)
│   ├── new_run_modal.html # Modal content
│   ├── abort_modal.html   # Modal content
│   ├── phase_detail.html  # Lazy-loaded phase accordion content
│   ├── artifact_viewer.html
│   ├── log_viewer.html
│   └── llm_viewer.html
└── components/
    ├── phase_pipeline.html  # Reusable phase steps visualization
    ├── run_row.html         # Table row for a run
    ├── stat_card.html       # Single stat card
    └── status_badge.html    # Status icon + label
```

**Dual-Response Pattern:**

The route handler checks `HX-Request` header. If present, returns just the page content block. If absent, wraps in `base.html` with full shell (head, header, nav, footer).

```python
@router.get("/runs/{run_id}")
async def run_detail(request: Request, run_id: str, ...):
    context = {"run": run, "request": request}
    template = "pages/run_detail.html"
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(template, context)
    return templates.TemplateResponse("base.html", {**context, "page_template": template})
```

`base.html` uses Jinja2 `{% include page_template %}` to embed the page content within the full shell.

**Rationale:** NFR21 requires component/partial structure for reuse. NFR23 requires dual-response. This structure cleanly separates full pages, polling fragments, and reusable components.

## Decision Impact Analysis

**Implementation Sequence:**

1. Shared server infrastructure (`server/app.py`, config, middleware)
2. Extract run trigger to `core/run_trigger.py`
3. Refactor webhook to use shared factory + route dependencies
4. Dashboard module scaffold (routes, templates, static assets)
5. Dashboard page routes with dual-response pattern
6. Polling partials and auto-refresh
7. SSE streams for live run monitoring
8. Mutation endpoints (start/abort) with CSRF
9. Analytics page with CSS charts

**Cross-Component Dependencies:**

- Dashboard routes depend on: data layer (IndexManager, StatsAggregator, ProjectRegistryManager), Jinja2 templates, shared server
- SSE streams depend on: data layer (IndexManager for run status)
- Mutation routes depend on: `core/run_trigger.py` (extracted from webhook)
- Shared server depends on: nothing new (pure infrastructure)
- Webhook refactor depends on: shared server (must migrate to new factory)
