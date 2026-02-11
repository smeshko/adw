# Implementation Patterns & Consistency Rules

## Pattern Categories Defined

**Critical Conflict Points Identified:** 8 areas where AI agents could make different choices specific to the web dashboard extension. All existing `project-context.md` rules continue to apply (PEP 8, models in `models/`, exception hierarchy, type annotations, structured logging).

## Route Handler Patterns

**Dual-Response Pattern — every page route MUST follow this:**

```python
@router.get("/runs/{run_id}")
async def run_detail(
    request: Request,
    run_id: str,
    index: IndexManager = Depends(get_index_manager),
) -> HTMLResponse:
    run = index.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    context = {"run": run, "request": request}
    template = "pages/run_detail.html"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(template, context)
    return templates.TemplateResponse("base.html", {**context, "page_template": template})
```

**Route Category Rules:**

| Category | Files | Response Pattern |
|----------|-------|-----------------|
| Page routes | `dashboard/routes.py` | Dual-response (full page or HTMX fragment via `HX-Request` header) |
| Partial routes | `dashboard/partials.py` | Always HTML fragment — no dual check |
| SSE routes | `dashboard/sse.py` | `StreamingResponse` — no template |
| Mutation routes | `dashboard/mutations.py` | Redirect or HTMX swap — no dual-response |
| Dependencies | `dashboard/dependencies.py` | FastAPI `Depends()` providers |

## Naming Patterns

**Template Files:**

```
pages/overview.html          # snake_case, matches route function name
pages/run_detail.html        # snake_case
partials/active_runs.html    # snake_case, matches HTMX target id
partials/new_run_modal.html  # snake_case
components/phase_pipeline.html  # snake_case, reusable fragment
```

**Rules:**
- All template files: `snake_case.html`
- Page templates match their route function name
- Partial templates match their HTMX target `id`
- Component templates are named for the UI element they render

**SSE Event Names:** `kebab-case` (e.g., `phase-update`, `run-complete`, `log-line`)

**Custom CSS Class Names:** `kebab-case` (e.g., `chart-bar`, `phase-active`, `chart-daily`)

## HTMX Attribute Conventions

**Standard attribute order on HTMX elements:**

```html
<div hx-get="/partials/active-runs"
     hx-trigger="every 3s"
     hx-target="#active-runs"
     hx-swap="outerHTML"
     hx-indicator="#loading">
```

**Rules:**
- `hx-get`/`hx-post` first (the action)
- `hx-trigger` second (when)
- `hx-target` third (where)
- `hx-swap` fourth (how)
- `hx-push-url` only on navigation actions (page-level swaps to `#main`)
- `hx-indicator` last (loading state)
- Never use `hx-push-url` on polling or partial refreshes

## Error Handling in HTML Context

**Dashboard routes return HTML errors, not JSON:**

```python
# CORRECT — dashboard exception handler
@app.exception_handler(HTTPException)
async def dashboard_http_exception(request: Request, exc: HTTPException):
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/error_banner.html",
            {"message": exc.detail, "request": request}, status_code=exc.status_code)
    return templates.TemplateResponse("pages/error.html",
        {"message": exc.detail, "status_code": exc.status_code, "request": request},
        status_code=exc.status_code)

# WRONG — returning JSON from a dashboard route
raise HTTPException(status_code=404, detail={"error": "not found"})
```

**Rules:**
- Dashboard routes never return JSON
- HTMX request errors return an HTML fragment for the error banner
- Full page errors return a complete error page
- Use the `ADWError` hierarchy from `exceptions.py` — convert to HTTP in the handler

## Data & Model Patterns

**Template context is a plain dict — no Pydantic response models for HTML:**

```python
# CORRECT — template context is a dict
context = {
    "runs": index.get_recent_runs(limit=5),  # returns list[IndexEntry]
    "stats": stats.get_global_stats(),         # returns GlobalStatistics
    "request": request,
}

# WRONG — unnecessary Pydantic model for template context
class OverviewContext(BaseModel):  # NO
    runs: list[IndexEntry]
```

**Exception:** If the dashboard needs new data shapes not covered by existing models (e.g., `DashboardConfig`), those go in `models/dashboard.py` per project-context.md rules.

## CSS Conventions

```html
<!-- CORRECT — DaisyUI components + Tailwind utilities -->
<div class="card card-compact card-bordered">
  <div class="stat-value font-mono text-2xl">142</div>
</div>

<!-- CORRECT — custom CSS for dashboard-specific styling -->
<div class="chart-bar bg-primary" style="height: 62%"></div>

<!-- WRONG — inline styles for things Tailwind handles -->
<div style="display: flex; gap: 1rem;">  <!-- NO — use flex gap-4 -->
```

**Rules:**
- DaisyUI component classes first, then Tailwind utilities
- Custom CSS classes only for dashboard-specific patterns (charts, animations)
- Custom CSS lives in a single `dashboard/static/dashboard.css` file
- Never use inline styles except for dynamic values (chart bar heights)
- Custom CSS class names: `kebab-case`

## Enforcement Guidelines

**All AI Agents MUST:**

1. Follow the dual-response pattern for every page route
2. Use `snake_case` for all template files
3. Use the standard HTMX attribute order
4. Never return JSON from dashboard routes
5. Never create Pydantic models for template context (use dicts)
6. Put custom CSS in `dashboard/static/dashboard.css` only
7. Organize routes by category (pages, partials, SSE, mutations)
8. SSE event data is always an HTML fragment (not JSON)
9. All existing `project-context.md` rules continue to apply

**Anti-Patterns to Avoid:**

| Don't | Do Instead |
|-------|-----------|
| Return JSON from dashboard routes | Return HTML (full page or fragment) |
| Create Pydantic models for template context | Use plain dicts with existing model objects |
| Use inline styles for layout | Use Tailwind utility classes |
| Use `hx-push-url` on polling requests | Only push URL on navigation actions |
| Put business logic in route handlers | Delegate to data layer via dependencies |
| Mix route categories in one file | Separate pages, partials, SSE, mutations |
| Use `camelCase` in template names | Use `snake_case.html` |
