# Filter Bar with Status, Project & Date Range

**Date:** 2026-02-11
**Related Files:** `src/adw/dashboard/templates/partials/runs_filter_bar.html`, `src/adw/dashboard/templates/partials/runs_list.html`, `src/adw/dashboard/templates/partials/runs_table.html`

## Overview

The runs list filter bar provides controls for narrowing the run history by status, project, and date range. It sits between the page header and the `#runs-content` div in the runs list page, ensuring it persists across table-only HTMX swaps triggered by filter changes, sorting, and pagination.

## What Was Built

- `runs_filter_bar.html` partial template with Status dropdown, Project dropdown, Date From/To inputs, combined `hx-include` selector for sort preservation, and conditional "Clear all" link
- Integration into `runs_list.html` via `{% include %}` outside `#runs-content`
- Conditional empty state message (filter-aware vs no-runs-yet)
- 20 integration tests covering filter rendering, pre-population, HTMX attributes, structural correctness, and combined filter scenarios

## Technical Implementation

### Key Files

- `src/adw/dashboard/templates/partials/runs_filter_bar.html`: Filter bar partial with all filter controls
- `src/adw/dashboard/templates/partials/runs_list.html`: Includes filter bar above `#runs-content`
- `src/adw/dashboard/templates/partials/runs_table.html`: Enhanced empty state message
- `tests/unit/dashboard/test_runs_list.py`: `TestRunsFilterBar` test class

### Key Patterns

- **Filter bar outside swap target**: The filter bar is included in `runs_list.html` above the `#runs-content` div. When filters/sort/pagination change, only `#runs-content` is swapped (table-only partial), so the filter bar persists without re-rendering.

- **`hx-include` with combined selector for sort preservation**: All filter controls live inside a `<form id="filter-form">`. Each control uses `hx-include="#filter-form, #runs-content [name='sort']"` so that every change sends ALL current filter values plus the live sort value from the sort dropdown inside `#runs-content`. This avoids a stale hidden sort input problem — since the filter bar is outside the swap target, a hidden sort input would become stale when the user changes sort. The combined CSS selector pulls the current sort directly from the dropdown.

- **"Clear all" targets `#main`**: Unlike filter changes (which target `#runs-content`), the "Clear all" link targets `#main` with `hx-push-url="/runs"` to reset the entire page including the filter bar itself.

- **No backend changes required**: The route handler already parses status, project, from, and to query parameters and passes them to `IndexManager.get_paginated_runs()`. The filter bar is purely a frontend template addition.

- **Global project filter sync**: When the header's global project filter changes, it targets `#main`, re-rendering the full `runs_list.html` partial. The filter bar's project dropdown reflects the `project_filter` context variable automatically.

### DaisyUI & HTMX Classes

- Container: `card card-compact bg-base-200 p-4 mb-4`
- Selects: `select select-bordered select-sm`
- Date inputs: `input input-bordered input-sm`
- Clear all button: `btn btn-ghost btn-xs`
- Layout: `flex flex-wrap items-end gap-4` (wrapping form)

### Code Examples

```html
{# Each filter control uses hx-include to send all filter values #}
<select class="select select-bordered select-sm"
        name="status"
        hx-get="/runs"
        hx-trigger="change"
        hx-target="#runs-content"
        hx-swap="innerHTML"
        hx-push-url="true"
        hx-include="#filter-form, #runs-content [name='sort']">
  <option value="">All Statuses</option>
  <option value="running" {% if status_filter == "running" %}selected{% endif %}>Running</option>
  ...
</select>
```

```html
{# Conditional "Clear all" link resets entire page #}
{% if status_filter or project_filter or from_date or to_date %}
<a hx-get="/runs"
   hx-target="#main"
   hx-push-url="/runs"
   class="btn btn-ghost btn-xs">Clear all</a>
{% endif %}
```

## How to Use

1. Navigate to `/runs` to see the filter bar above the runs table
2. Use the Status dropdown to filter by run status (Running, Completed, Failed, Interrupted, Aborted)
3. Use the Project dropdown to filter by registered project
4. Use Date From/To inputs to filter by date range
5. Combine multiple filters — all are sent together on each change
6. Use "Clear all" to reset all filters
7. Bookmark filtered URLs — all filter params are in the URL (e.g., `/runs?status=failed&project=my-api&from=2026-01-01`)

## Notes

- Filter changes reset to page 1 implicitly (page param is omitted from filter requests)
- Sort order is preserved when filters change via `hx-include` referencing the sort dropdown in `#runs-content`
- The "Clear all" link only appears when at least one filter is active
- Empty state shows a filter adjustment suggestion when filters are active, or "No runs recorded yet" when no filters are active
- The filter bar uses `<form>` with no submit action — all interaction is via HTMX `change` events
