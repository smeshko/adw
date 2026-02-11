# Runs List Page with Table, Pagination & Sorting

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/core/index_manager.py`, `src/adw/dashboard/templates/partials/runs_table.html`, `src/adw/dashboard/templates/partials/runs_list.html`

## Overview

The runs list page (`/runs`) provides a full, sortable, paginated table of all ADW runs. It introduces the dashboard's first dedicated list page with server-side pagination, five sort options, and filter preservation across navigation. The route uses a triple-response pattern to serve full pages, HTMX page partials, and table-only partials depending on the request context.

## What Was Built

- Paginated runs query method on `IndexManager` with filter, sort, and pagination support
- `/runs` route handler with query parameter parsing (status, project, from/to dates, sort, page)
- `runs_table.html` partial with summary line, data table, sort dropdown, and DaisyUI pagination
- `runs_list.html` partial with page header ("All Runs" + "+ New Run" button) and content wrapper
- Full page template extending `base.html`
- Jinja2 URL macros for building pagination/sort/filter URLs with param preservation
- 60 tests (18 IndexManager unit + 42 dashboard integration)

## Technical Implementation

### Key Files

- `src/adw/core/index_manager.py`: `get_paginated_runs()` method — accepts page, page_size, status, project_name, since, until, sort params and returns a dict with entries, total_count, page, page_size, total_pages
- `src/adw/dashboard/routes.py`: `runs_list()` route handler — parses query params, calls IndexManager, builds context, discriminates response type
- `src/adw/dashboard/templates/partials/runs_table.html`: HTMX-swappable table partial with summary, table, pagination controls, and empty state
- `src/adw/dashboard/templates/partials/runs_list.html`: Page-level partial with header and `#runs-content` wrapper
- `src/adw/dashboard/templates/pages/runs_list.html`: Full page extending base.html

### Key Patterns

- **Triple-response pattern**: The `/runs` route serves three different templates based on request headers:
  1. No `HX-Request` header → full page (`pages/runs_list.html`)
  2. `HX-Request` without `HX-Target=runs-content` → page partial (`partials/runs_list.html`)
  3. `HX-Request` with `HX-Target=runs-content` → table-only partial (`partials/runs_table.html`)

  This allows HTMX navigation to swap just `#main`, while sort/page changes swap only `#runs-content`.

- **Pagination URL macros**: Two Jinja2 macros handle URL construction:
  - `runs_url(p, s, st, proj, fd, td)` — builds full URL preserving all current params
  - `runs_base_url(p, st, proj, fd, td)` — builds URL without sort param (used by sort dropdown with `hx-include="this"`)

- **Context key namespacing**: The paginated page number is stored as `current_page` in template context (not `page`) to avoid collision with the `page` key used by `_build_page_context()` for nav active state.

- **Sort dropdown with hx-include**: The sort dropdown uses `hx-include="this"` with `name="sort"` to append the selected sort value to the request URL built by `hx-get`. Combined with `hx-push-url="true"`, this keeps the browser URL in sync.

- **Page clamping**: `get_paginated_runs()` clamps the page number to `[1, total_pages]` to handle out-of-range requests gracefully.

- **Date-only expansion**: When the `to` date filter is a date-only string (no `T` separator), the route handler expands it to end-of-day (`23:59:59.999999`) so the filter is inclusive of the entire day.

### Code Examples

```python
# Using get_paginated_runs() from IndexManager
result = index_manager.get_paginated_runs(
    page=2,
    page_size=15,
    status="completed",
    project_name="my-api",
    sort="duration_longest",
)
# result = {
#     "entries": [...],       # list[IndexEntry] for page 2
#     "total_count": 47,      # total matching entries
#     "page": 2,              # current page (clamped)
#     "page_size": 15,
#     "total_pages": 4,
# }
```

```python
# Triple-response pattern in route handler
hx_target = request.headers.get("HX-Target", "")
if request.headers.get("HX-Request"):
    if hx_target == "runs-content":
        return templates.TemplateResponse(request, "partials/runs_table.html", context)
    return templates.TemplateResponse(request, "partials/runs_list.html", context)
return templates.TemplateResponse(request, "pages/runs_list.html", context)
```

## How to Use

1. Navigate to `/runs` to see the full paginated runs list
2. Use the sort dropdown to change ordering (Newest, Oldest, Duration longest/shortest, Project A-Z)
3. Add query parameters for filtering: `?status=completed&project=my-api&from=2026-01-01&to=2026-02-01`
4. Pagination links automatically preserve all current filter and sort params

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| page_size | int | 15 | Runs per page (hardcoded in route) |
| sort | string | "newest" | Default sort order |
| page | int | 1 | Default page number |

## Notes

- The page size of 15 is hardcoded in the route handler, not configurable via query param
- Sort dropdown resets to page 1 via `runs_base_url(p=1)` to avoid empty pages after filter changes
- Running runs use elapsed time (now - started_at) for duration sorting instead of 0
- The `current_page` context key naming was chosen to avoid collision with `_build_page_context()`'s `page` key used for nav highlighting
