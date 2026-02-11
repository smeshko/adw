# Epic 4: Runs List & Filtering

User can browse, filter, sort, and paginate through their complete run history across all projects — enabling efficient navigation of large run histories.

**FRs covered:** FR28-FR31 (4 FRs)

### Story 4.1: Runs List Page with Table & Pagination

As a developer,
I want to view a full, sortable, paginated list of all my runs,
So that I can browse my complete run history and find specific runs efficiently.

**Acceptance Criteria:**

**Given** the user navigates to `/runs`
**When** the page renders
**Then** the runs list page displays with dual-response pattern (full page for direct nav, partial for HTMX)
**And** the page title "All Runs" is shown with a "+ New Run" button on the right (`btn btn-primary btn-sm`) (UX §6)
**And** the URL is bookmarkable with all query params preserved (FR52)

**Given** the runs list page is displayed
**When** the table renders
**Then** runs are shown in a `table table-zebra table-sm hover` inside a `#runs-content` target (UX §6.3)
**And** table columns are:
| Column | Width | Content | Style |
|--------|-------|---------|-------|
| Project | `w-28` | Project name | `text-sm` |
| Feature | `flex-1` | Description (wider than overview) | `text-sm text-base-content/70 truncate` |
| Status | `w-24` | Icon + label | `badge badge-sm badge-{status}` per design vocabulary |
| Duration | `w-24` | `Xm Ys` | `font-mono text-xs` |
| Started | `w-28` | Relative time | `text-xs text-base-content/50` |

**Given** a row in the runs table
**When** the user hovers over it
**Then** a subtle background highlight appears via `hover` class (UX §6.3)

**Given** a row in the runs table
**When** the user clicks it
**Then** navigation occurs via `hx-get="/runs/{id}" hx-target="#main" hx-push-url="/runs/{id}"` (UX §6.3)

**Given** the runs list page is displayed
**When** a summary line renders above the table
**Then** it shows: count of runs matching current filters (e.g., "Showing 47 runs") and a sort dropdown on the right (UX §6.2)
**And** the sort dropdown is `select select-bordered select-xs` with options: Newest (default), Oldest, Duration (longest), Duration (shortest), Project (A-Z) (FR30)
**And** changing the sort triggers `hx-trigger="change"` with `?sort=` param and refreshes the table

**Given** more than 15 runs match the current filters
**When** pagination renders
**Then** DaisyUI `join` component with `btn btn-sm` buttons shows page navigation (UX §6.4)
**And** the current page button has `btn-active`
**And** all pagination links use `hx-target="#runs-content" hx-push-url` and preserve current filter and sort params (FR31)
**And** page size is 15 runs per page

**Given** the runs list at compact widths (1024-1279px)
**When** the table doesn't fit horizontally
**Then** a `overflow-x-auto` wrapper enables horizontal scrolling (UX §12)
**And** the feature column `max-w` shrinks

**Given** the dashboard has 1000+ runs in the index
**When** the runs list loads
**Then** the page remains responsive and loads quickly (NFR5)

**Technical notes:**
- Route: `/runs` with query params: `?status=`, `?project=`, `?from=`, `?to=`, `?sort=`, `?page=`
- Runs table partial: `runs_table.html` for HTMX filter/sort/page swaps via `#runs-content` target
- No independent polling on this page — manual refresh or filter change only (UX §9.3)

---

### Story 4.2: Filter Bar with Status, Project & Date Range

As a developer,
I want to filter runs by status, project, and date range,
So that I can narrow down my run history to find exactly what I'm looking for.

**Acceptance Criteria:**

**Given** the runs list page is displayed
**When** the filter bar renders
**Then** it shows controls inside a `card card-compact bg-base-200 p-4` strip (UX §6.1)
**And** it contains:
| Filter | Component | Options |
|--------|-----------|---------|
| Status | `select select-bordered select-sm` | All, Running, Completed, Failed, Interrupted, Aborted |
| Project | `select select-bordered select-sm` | All (default) + all registered projects |
| Date From | `input input-bordered input-sm type="date"` | Open date picker |
| Date To | `input input-bordered input-sm type="date"` | Open date picker |

**Given** the user changes any filter
**When** a filter value changes
**Then** the table and summary line refresh via `hx-get="/runs?status=...&project=...&from=...&to=..." hx-target="#runs-content" hx-trigger="change" hx-push-url` (FR28, FR29)
**And** all filters combine into query params in the URL
**And** the filter bar itself does NOT refresh — it maintains its state via URL params (UX §6.1)

**Given** the user filters by status "Failed"
**When** the table refreshes
**Then** only failed runs are shown (FR28)
**And** the summary line updates to show the filtered count

**Given** the user sets a date range
**When** "From" and/or "To" dates are set
**Then** only runs within the date range are shown (FR29)

**Given** any filter is active
**When** the filter bar renders
**Then** a "Clear all" link appears that resets to `/runs` with no filters (UX §6.1)

**Given** filters are applied and no runs match
**When** the table area renders
**Then** an empty state message is shown: "No runs match your filters. Try adjusting the status or date range." with a `[Clear filters]` link (UX §11.1)

**Given** the user navigates directly to a filtered URL (e.g., `/runs?status=failed&project=my-api`)
**When** the page loads
**Then** the filter controls reflect the URL parameters
**And** the table shows only matching runs (FR52)

**Given** the global project filter in the header is active
**When** the runs list loads
**Then** the project filter in the filter bar syncs with the global filter

**Technical notes:**
- All filter combinations produce clean query param URLs for bookmarkability
- Filter changes trigger HTMX swaps of `#runs-content` only (not the filter bar itself)
- Date filters use native HTML5 date inputs
