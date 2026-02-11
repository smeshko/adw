# 2. Information Architecture

## Page Map

```
Overview (/)
├── Stat cards              → Summary metrics
├── Active runs             → Compact cards → click → /runs/{id}
├── Recent runs (last 5)    → Compact table → "View All" → /runs
├── Project breakdown       → Mini cards → click sets global project filter
└── Cost summary            → Preview strip → "View Details" → /analytics

Run Detail (/runs/{id})     → Full run deep-dive
Runs List (/runs)           → Filterable, sortable, paginated list
Analytics (/analytics)      → Token usage and cost trends
```

## Navigation Model

- **Persistent header** — Always visible. Contains: logo/title, page nav links, project filter, theme toggle.
- **No sidebar** — Content-first layout. Navigation is horizontal.
- **Content area** — `<main id="main">` swaps via `hx-target="#main"`. The header never reloads.
- **URL-driven** — Every view has a unique URL. `hx-push-url` on all navigation actions. Browser back/forward works natively.
- **Breadcrumb context** — Detail pages show "← Back to [previous]" as a contextual link, not a breadcrumb trail.

## URL Structure

| Page | URL | Query Params |
|------|-----|-------------|
| Overview | `/` | `?project={name}` (optional filter) |
| Run Detail | `/runs/{run_id}` | — |
| Runs List | `/runs` | `?project=`, `?status=`, `?from=`, `?to=`, `?sort=`, `?page=` |
| Analytics | `/analytics` | `?range=7d\|30d\|90d\|all`, `?project=` |

All query params are optional. Defaults: no project filter, all statuses, last 7 days for analytics, sorted by most recent.

---
