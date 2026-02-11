# Starter Template Evaluation

## Primary Technology Domain

**Brownfield Extension** — Server-rendered web dashboard added to existing Python CLI/SDK project. No starter template applicable. Architecture extends existing FastAPI + uv project.

## Starter Approach

No external starter template. New modules added to existing project structure with targeted dependency additions.

## New Dependencies

**Added to pyproject.toml:**

```bash
uv add jinja2
```

**Vendored Assets (in static directory):**
- `htmx.min.js` v2.0.8 — vendored locally, no CDN dependency (~14KB)

**CDN Assets (in base template `<head>`):**
- DaisyUI 5 CSS — `https://cdn.jsdelivr.net/npm/daisyui@5/dist/full.min.css` (34KB compressed)
- Tailwind CSS v4 browser — `https://cdn.tailwindcss.com` (runtime compiler)

## Selected Stack: FastAPI + Jinja2 + HTMX + DaisyUI/Tailwind

**Rationale:**
- Jinja2 is the standard FastAPI template engine, well-documented integration
- HTMX enables SPA-like interactions with zero client-side JS framework
- DaisyUI provides dashboard-ready components (stat, card, table, badge, collapse) that map directly to the existing TUI dashboard patterns
- Tailwind utility classes for layout and spacing with zero build tooling
- CDN delivery for CSS is appropriate for a local developer tool
- HTMX vendored locally to eliminate any CDN dependency for the interactive layer

## Architectural Decisions Provided by Stack Extension

**Template Engine (Jinja2 3.1.6):**
- FastAPI's `Jinja2Templates` for server-rendered HTML
- Template inheritance for layout consistency (base.html → page templates)
- HTMX partial rendering via separate partial templates for swappable fragments

**Hypermedia Engine (HTMX 2.0.8):**
- Server-driven interactions via HTML attributes (hx-get, hx-trigger, hx-swap)
- Polling for auto-refresh (hx-trigger="every 5s")
- Partial page updates without full reloads
- Vendored locally — no CDN dependency

**Component Library (DaisyUI 5 + Tailwind CSS v4):**
- Pre-built component classes: stat, card, table, badge, collapse, tabs, modal
- Tailwind utility classes for layout, spacing, responsive design
- Theme support via DaisyUI data-theme attribute (dark mode ready)
- CDN delivery — zero build tooling, two `<head>` includes
- 34KB compressed for all DaisyUI components + Tailwind runtime compiler

**Project Structure Addition:**
```
src/adw/
├── server/              # NEW — shared server infrastructure
│   ├── __init__.py
│   ├── app.py           # Shared FastAPI app factory
│   ├── config.py        # Unified server configuration
│   └── middleware.py     # Shared/route-scoped middleware
├── dashboard/           # NEW — web dashboard feature
│   ├── __init__.py
│   ├── routes.py        # Dashboard page routes
│   ├── api.py           # Dashboard data API endpoints
│   ├── templates/       # Jinja2 templates
│   │   ├── base.html    # Layout: head (CDN links), nav, content slot
│   │   ├── pages/       # Full page templates
│   │   └── partials/    # HTMX fragment responses
│   └── static/          # Vendored htmx.min.js, custom CSS overrides
├── webhook/             # EXISTING — refactored to register on shared server
│   ├── ...
```

**Note:** The webhook module's server.py factory will be refactored to use the shared server/app.py factory, registering webhook routes as a FastAPI router.
