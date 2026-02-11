# 6. Runs List Page

**Route:** `/runs`
**Purpose:** Full, filterable, sortable, paginated list of all runs across all projects.
**PRD FRs:** FR28-31

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (global)                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  All Runs                                     [+ New Run]   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Status: [All ▾]  Project: [All ▾]  From: [____]     │   │
│  │                                    To:   [____]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Showing 47 runs                              Sort: Newest  │
│                                                             │
│  ┌─────────┬────────────────┬────────┬────────┬──────────┐ │
│  │ Project │ Feature        │ Status │Duration│ Started  │ │
│  ├─────────┼────────────────┼────────┼────────┼──────────┤ │
│  │ my-api  │ Add CORS head  │ ✓ done │ 4m 12s │ 25m ago  │ │
│  │ sdk     │ Retry logic f  │ ✗ fail │ 2m 01s │ 1h ago   │ │
│  │ dashb.. │ Dark mode the  │ ✓ done │ 6m 44s │ 2h ago   │ │
│  │ my-api  │ Rate limiting  │ ✓ done │ 3m 55s │ 3h ago   │ │
│  │ sdk     │ Refactor exec  │ ✓ done │ 7m 20s │ 5h ago   │ │
│  │ my-api  │ Add healthche  │ ✓ done │ 2m 10s │ 6h ago   │ │
│  │ dashb.. │ Responsive la  │ ✓ done │ 5m 33s │ 8h ago   │ │
│  │ ...     │                │        │        │          │ │
│  │ sdk     │ Initial setup  │ ✓ done │ 8m 01s │ 3d ago   │ │
│  ├─────────┴────────────────┴────────┴────────┴──────────┤ │
│  │              ← Previous  Page 1 of 5  Next →          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  FOOTER (global)                                            │
└─────────────────────────────────────────────────────────────┘
```

## 6.1 Filter Bar

**DaisyUI:** Controls inside a `card card-compact bg-base-200 p-4` strip.

| Filter | Component | HTMX Behavior |
|--------|-----------|---------------|
| Status | `select select-bordered select-sm` with options: All, Running, Completed, Failed, Interrupted, Aborted | `hx-get="/runs" hx-target="#runs-content" hx-trigger="change" hx-push-url` |
| Project | `select select-bordered select-sm` with all registered projects + "All" | Same trigger pattern |
| Date From | `input input-bordered input-sm type="date"` | `hx-trigger="change"` |
| Date To | `input input-bordered input-sm type="date"` | `hx-trigger="change"` |

All filters combine into query params: `/runs?status=failed&project=my-api&from=2026-02-01&to=2026-02-10`

When any filter changes, the table and summary line refresh (but not the filter bar itself — it maintains its state via the URL params).

**Clear filters:** If any filter is active, show a "Clear all" link that resets to `/runs`.

## 6.2 Summary Line

```
Showing 47 runs                                Sort: Newest ▾
```

- Count of runs matching current filters
- Sort dropdown: `select select-bordered select-xs` with options: Newest, Oldest, Duration (longest), Duration (shortest), Project (A-Z)
- `hx-trigger="change"` with `?sort=` param

## 6.3 Runs Table

**DaisyUI:** `table table-zebra table-sm hover` inside the `#runs-content` target.

**Columns:** Same as overview recent runs table, but wider feature column since there's more space.

| Column | Width hint | Sortable |
|--------|-----------|----------|
| Project | `w-28` | No (use filter) |
| Feature | `flex-1` (takes remaining space) | No |
| Status | `w-24` | Yes (via sort dropdown) |
| Duration | `w-24` | Yes |
| Started | `w-28` | Yes (default) |

**Row click:** Each row → `hx-get="/runs/{id}" hx-target="#main" hx-push-url="/runs/{id}"`

**Row hover:** `hover` class gives a subtle background highlight.

## 6.4 Pagination

**DaisyUI:** `join` component with `btn btn-sm` buttons.

```html
<div class="join">
  <button class="join-item btn btn-sm" hx-get="/runs?page=1">«</button>
  <button class="join-item btn btn-sm" hx-get="/runs?page=2">2</button>
  <button class="join-item btn btn-sm btn-active">3</button>
  <button class="join-item btn btn-sm" hx-get="/runs?page=4">4</button>
  <button class="join-item btn btn-sm" hx-get="/runs?page=10">»</button>
</div>
```

- All pagination links use `hx-target="#runs-content" hx-push-url`
- Page size: 15 runs per page (reasonable density)
- Preserves current filter and sort params

---
