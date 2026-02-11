# Dashboard Base Template, Navigation & Theme

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/server.py`, `src/adw/dashboard/templates/base.html`, `src/adw/dashboard/static/dashboard.css`, `src/adw/dashboard/dependencies.py`

## Overview

The dashboard web UI uses a persistent shell (header + footer) with HTMX-powered content swapping. Navigation between pages replaces only `<main id="main">` without full page reloads, while direct URL access returns a complete HTML page. Theme preference persists across sessions via `localStorage`.

## What Was Built

- Persistent header with logo, nav links (Overview, Runs, Analytics), project filter dropdown, and theme toggle
- Dual-response route pattern: full HTML page for direct requests, partial fragment for HTMX requests
- Status bar footer with 10-second HTMX polling for live update time and active run count
- Dark/light theme toggle with `localStorage` persistence and flash-prevention inline script
- HTML-only error handling (banner fragment for HTMX, full error page for direct requests)
- CSS design tokens for phase colors, chart colors, and HTMX transition animations
- CSRF token generation and validation via HMAC-SHA256

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py`: Page routes with dual-response pattern and shared context builder
- `src/adw/dashboard/partials.py`: Fragment-only routes (status bar polling endpoint)
- `src/adw/dashboard/server.py`: App factory with Jinja2 templates, static files, and HTML exception handlers
- `src/adw/dashboard/dependencies.py`: FastAPI DI providers for IndexManager, StatsAggregator, ProjectRegistryManager, and CSRF
- `src/adw/dashboard/templates/base.html`: Shell template with header, nav, footer, theme toggle, error toast JS
- `src/adw/dashboard/static/dashboard.css`: Design tokens, HTMX transitions, loading indicator styles

### Key Patterns

- **Dual-Response Pattern**: Every page route checks `request.headers.get("HX-Request")`. If present, render `partials/<name>.html` (fragment). Otherwise, render `pages/<name>.html` (extends `base.html` for full page). This is the foundational pattern for all dashboard routes.

- **Shared Context Builder**: `_build_page_context()` in `routes.py` assembles the common template context (CSRF token, project list, active run count, last updated time, selected project). All page routes call this before rendering.

- **Project Filter Propagation**: Nav links include `?project={{ selected_project }}` in their `hx-get` and `hx-push-url` attributes so the filter persists across navigation. The `<select>` uses `hx-get` with `hx-push-url="true"` to update the URL when changed.

- **Theme Flash Prevention**: An inline `<script>` in `<head>` reads `localStorage.getItem('adw-theme')` and sets `data-theme` before any rendering occurs. This prevents a flash of the wrong theme on page load.

- **Status Bar OOB Polling**: The footer uses `hx-get="/partials/status-bar" hx-trigger="every 10s" hx-target="#status-bar" hx-swap="outerHTML"` to poll for fresh data without affecting page content.

- **HTML-Only Error Responses**: The app registers exception handlers for both `StarletteHTTPException` and generic `Exception`. For HTMX requests, errors render `partials/error_banner.html`. For direct requests, errors render `pages/error.html`. The dashboard never returns JSON errors.

### Code Examples

Adding a new page route following the dual-response pattern:

```python
# In routes.py
@router.get("/my-page", response_class=HTMLResponse)
async def my_page(
    request: Request,
    project: str = Query("", alias="project"),
    index_manager: object = Depends(get_index_manager),
    project_registry: object = Depends(get_project_registry),
) -> HTMLResponse:
    """Render my page (full or partial)."""
    templates = request.app.state.templates
    context = _build_page_context(
        request, "my_page",
        index_manager=index_manager,
        project_registry=project_registry,
        project=project,
    )
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/my_page.html", context)
    return templates.TemplateResponse(request, "pages/my_page.html", context)
```

Then create `templates/pages/my_page.html` (extends `base.html`) and `templates/partials/my_page.html` (standalone fragment with a root `<div id="my-page">`).

## How to Use

1. **Add a new page**: Create page route in `routes.py` following the dual-response pattern above. Create both `pages/` and `partials/` templates. Add nav link to `base.html` header with matching `data-page` attribute.
2. **Add a new partial endpoint**: Create route in `partials.py` — always returns HTML fragment, never full page. No dual-response needed.
3. **Add design tokens**: Define CSS custom properties in `dashboard.css` under `:root`. Use DaisyUI oklch color references for theme-aware colors.
4. **Propagate project filter**: Accept `project: str = Query("", alias="project")` in your route and pass `selected_project` in the template context.

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `data-theme` | `"dark"` / `"light"` | `"dark"` | DaisyUI theme, stored in `localStorage` key `adw-theme` |
| Status bar poll | interval | `10s` | `hx-trigger="every 10s"` on the footer element |
| HTMX swap transition | CSS | `100ms` out / `200ms` in | `.htmx-swapping` opacity fade out, `.htmx-settling` fade in |
| Min viewport width | CSS | `1024px` | `min-width: 1024px` enforced on `body` |

## Notes

- The `pages/` templates extend `base.html` and define `{% block content %}`. The `partials/` templates are standalone fragments with a root `<div id="...">`.
- The JS `htmx:pushedIntoHistory` event listener updates the active nav indicator client-side after HTMX navigation, keeping the UI consistent without a server round-trip.
- The project filter `<select>` dynamically updates its `hx-get` target path via the same `htmx:pushedIntoHistory` listener so it always posts to the current page.
- CSRF tokens use a per-request nonce signed with HMAC-SHA256 against `APP_SECRET_KEY` (falls back to a dev-only default).
