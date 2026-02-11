# Epic 2: Run Detail & Deep Inspection

User can deep-dive into any run to see full metadata, phase-by-phase progression, browse artifacts inline, view LLM prompt/response exchanges, and search/stream logs — enabling the full "Debug Detective" workflow for understanding what happened in any run.

**FRs covered:** FR16-FR27 (12 FRs)

### Story 2.1: Run Detail Page Layout & Metadata

As a developer,
I want to view a run's full metadata, phase pipeline, and key information on a dedicated detail page,
So that I can understand the complete context of any run at a glance.

**Acceptance Criteria:**

**Given** the user navigates to `/runs/{run_id}`
**When** the page renders
**Then** the run detail page displays with dual-response pattern (full page for direct nav, partial for HTMX) (FR16)
**And** the URL is bookmarkable and directly accessible

**Given** the run detail page is displayed
**When** the header section renders
**Then** a context-aware back link is shown: "← Back to Overview" (if from overview) or "← Back to Runs" (if from runs list)
**And** the back link is determined via `Referer` header or `?from=runs` query param
**And** the back link uses `hx-get` with `hx-target="#main" hx-push-url` (UX §5.1)

**Given** the run detail page is displayed
**When** the title section renders
**Then** it shows: `{project} / {feature}` with project name in `font-semibold` and feature in normal weight
**And** a status badge on the right using `badge badge-lg badge-{status}` with the design vocabulary colors
**And** a meta line below with: truncated run ID (`font-mono`), branch name, duration, relative time in `text-sm text-base-content/60 font-mono` (FR16)

**Given** the run detail page is displayed
**When** the action buttons render
**Then** for active runs: an "Abort" button (`btn btn-error btn-outline btn-sm`) is shown that opens the abort confirmation modal
**And** for all runs: a "Re-run" button (`btn btn-primary btn-outline btn-sm`) is shown that opens the New Run modal pre-populated (UX §5.1)
**And** buttons are top-right aligned with the back link

**Given** the run detail page is displayed
**When** the phase pipeline renders
**Then** a full-width horizontal phase visualization is shown using `steps steps-horizontal w-full` (FR17)
**And** each step shows: phase name label, duration (`font-mono text-xs`), and status: `step-success` (completed), `step-error` (failed), `step-warning` (active/running), default (pending)

**Given** the run detail page is displayed
**When** the metadata card renders
**Then** a `card card-bordered bg-base-200` shows a 2-column CSS grid (`.metadata-grid { grid-template-columns: 8rem 1fr; gap: 0.25rem 1rem; }`) with:
| Key | Value | Style |
|-----|-------|-------|
| Run ID | Full ULID | `font-mono text-sm` + clipboard copy button |
| Project | Name + path | Path in `text-base-content/50 text-xs` |
| Feature | Full description | Untruncated |
| Branch | Branch name | `font-mono text-sm` |
| Started | ISO timestamp | `font-mono text-sm` |
| Completed | ISO timestamp (or "—" if active/failed) | `font-mono text-sm` |
| Duration | `Xm Ys` | `font-mono` |
| Tokens | Total (in: X / out: Y) | `font-mono text-sm` |
| Cost | `$X.XX` | `font-mono text-sm` |
| PR | Link with `↗` icon | Only if available (FR27) |
| Linear | Link with `↗` icon | Only if webhook-triggered (FR27) |
| Artifacts | File path | `font-mono text-xs` (FR24) |

**Given** the Run ID is displayed in the metadata card
**When** the user clicks the copy button (inline clipboard icon)
**Then** the full run ID is copied to clipboard via minimal inline `onclick` JS (UX §5.3)

**Technical notes:**
- Route: `/runs/{run_id}` with dual-response pattern
- Data from `IndexManager` via `Depends()`
- The copy button is one of the minimal inline JS pieces (alongside HTMX, theme toggle, keyboard shortcuts)
- PR/Linear links only shown when data is available in run metadata

---

### Story 2.2: Phase Accordion with Hooks & Artifacts

As a developer,
I want to expand any phase to see its hooks execution results and browse artifacts inline,
So that I can inspect what happened in each phase and review generated files.

**Acceptance Criteria:**

**Given** the run detail page is displayed
**When** the phases section renders
**Then** each phase is a collapsible `collapse collapse-arrow bg-base-200` accordion (FR17)
**And** the collapsed state shows: phase name (`font-semibold`), duration (`font-mono text-sm`), status icon (color-coded), token count (`font-mono text-sm text-base-content/60`), cost (`font-mono text-sm text-base-content/60`)

**Given** a phase accordion is collapsed
**When** the user clicks to expand it
**Then** the phase content loads via `hx-get="/runs/{id}/phases/{phase}" hx-trigger="click once" hx-swap="innerHTML"` — content is NOT loaded until clicked (lazy loading) (UX §5.4)
**And** a `loading loading-dots loading-md` indicator shows centered in the target area while loading (UX §9.5, §11.3)
**And** subsequent clicks toggle the accordion open/closed without re-fetching (the `once` modifier)

**Given** a phase accordion is expanded
**When** the hooks sub-section renders
**Then** hooks are displayed in a `card card-compact bg-base-300` (slightly darker than parent) (UX §5.4.1)
**And** each hook shows: type label (`pre`/`post`), status icon (✓ or ✗), script name, and duration
**And** failed hooks show a red icon with error message inline

**Given** a phase accordion is expanded
**When** the artifacts sub-section renders
**Then** a list of artifact files produced by this phase is shown (FR18)
**And** each artifact has a `[View]` button

**Given** an artifact's `[View]` button is clicked
**When** the artifact content loads
**Then** it loads via `hx-get="/runs/{id}/artifacts/{path}" hx-target="#artifact-viewer"` into an inline viewer panel below the artifacts list (FR19)
**And** the viewer is a `card bg-base-300` with: file name as title, content in a `pre` block with `font-mono text-sm` (for text files), and a close button to collapse the viewer
**And** markdown files are rendered as server-side HTML (UX §5.4.2)

**Given** the artifacts path is shown in the metadata card
**When** the user views it
**Then** the file system path is visible so they can locate files on disk (FR24)
**And** no additional file system paths are exposed beyond what the data layer provides (NFR10)

**Technical notes:**
- Lazy-loaded partials: `/runs/{id}/phases/{phase}` returns HTML fragment
- Artifact viewer: `/runs/{id}/artifacts/{path}` returns rendered content
- Template hierarchy: phase detail as a partial in `partials/`, artifact viewer as a component
- Server should not expose file system paths beyond what `IndexManager` provides (NFR10)

---

### Story 2.3: LLM Interaction Viewer & Log Viewer

As a developer,
I want to view LLM prompts/responses for each phase and search/filter run logs by keyword, severity, and phase,
So that I can debug issues by examining what the LLM received and produced, and find specific log entries quickly.

**Acceptance Criteria:**

**Given** a phase accordion is expanded
**When** the LLM interaction sub-section renders
**Then** a summary line shows token counts for prompt and response with `[View]` buttons (FR25)
**And** displayed in a `card card-compact bg-base-300` format (UX §5.4.3)

**Given** the user clicks `[View]` on the LLM prompt or response
**When** the content loads
**Then** the full text loads via `hx-get="/runs/{id}/phases/{phase}/prompt"` (or `.../response"`)
**And** it renders in a scrollable `pre` block with `max-h-96 overflow-y-auto font-mono text-xs` (FR25, UX §5.4.3)
**And** per-exchange token counts are shown

**Given** a phase accordion is expanded
**When** the logs sub-section renders
**Then** a log viewer is displayed pre-filtered to the current phase (FR26)
**And** a controls bar shows: search input (`input input-bordered input-sm`), severity filter (`select select-bordered select-sm` with All/INFO/WARN/ERROR), and phase filter (pre-set to current phase but changeable) (FR20, FR22, FR26)

**Given** the log viewer is displayed
**When** log entries render
**Then** logs show in `bg-base-300 rounded-lg p-4 font-mono text-xs` (or `mockup-code`)
**And** each line shows: `{timestamp} {level} {message}`
**And** level coloring: INFO = default, WARN = `text-warning`, ERROR = `text-error`
**And** the container is scrollable with `max-h-80 overflow-y-auto`
**And** most recent entries are at the bottom (chronological order) with most recent visible by default (FR20)

**Given** the user types in the search input
**When** text is entered with a 300ms debounce
**Then** logs filter via `hx-get="/runs/{id}/logs?q={query}&level={level}&phase={phase}" hx-trigger="keyup changed delay:300ms"` targeting `#log-content` (FR21)

**Given** the user changes the severity filter
**When** a severity level is selected
**Then** logs reload filtered by that severity level (FR22)

**Given** the user changes the phase filter
**When** a different phase is selected
**Then** logs reload filtered by the selected phase (FR26)

**Technical notes:**
- Log search endpoint: `GET /runs/{id}/logs?q=&level=&phase=` returns HTML log content fragment
- LLM content endpoints: `GET /runs/{id}/phases/{phase}/prompt` and `.../response`
- All endpoints return HTML fragments (never JSON) per architecture requirements
- Log viewer is embedded within each phase's expanded content

---

### Story 2.4: Active & Failed Run Variants with SSE

As a developer,
I want the run detail page to show real-time updates for active runs (streaming logs, phase progression) and auto-highlight failures for failed runs,
So that I can monitor live runs and quickly diagnose failures.

**Acceptance Criteria:**

**Given** the user views an active/running run's detail page
**When** the page renders
**Then** the phase pipeline shows the current phase with `step-warning` and a `loading loading-dots loading-sm` animation next to the label (UX §5.6)
**And** a CSS `phase-pulse` animation pulses the active phase indicator
**And** the elapsed time updates in real-time via SSE
**And** the "Abort" button is visible in the header action buttons

**Given** the user is viewing an active run
**When** SSE is connected
**Then** the page connects to `hx-ext="sse" sse-connect="/runs/{id}/events"` (UX §9.2)
**And** `phase-update` events update the phase pipeline and elapsed time via `hx-swap-oob="true"` (FR8, FR10)
**And** `run-complete` / `run-failed` events refresh the run header + pipeline and swap action buttons (remove Abort, ensure Re-run visible)

**Given** the user expands the current (active) phase's accordion
**When** the log viewer renders for the active phase
**Then** logs stream in real-time via `hx-ext="sse" sse-connect="/runs/{id}/logs/stream" sse-swap="log-line"` with `hx-swap="beforeend"` (FR23)
**And** the viewer auto-scrolls to bottom as new lines arrive (UX §5.4.4)
**And** log streaming displays output within 1 second of generation (NFR4)

**Given** an active run
**When** pending phases are shown in the accordion
**Then** they display "Waiting..." in their collapsed state (UX §5.6)

**Given** the user navigates away from an active run's detail page
**When** the SSE element is removed from the DOM
**Then** the SSE connection disconnects automatically (HTMX handles cleanup) (UX §9.2)

**Given** an SSE connection is interrupted
**When** a network interruption occurs
**Then** the connection automatically reconnects (HTMX SSE extension default behavior) (NFR18)

**Given** the user views a failed run's detail page
**When** the page renders
**Then** the phase pipeline shows the failed phase as `step-error` with all subsequent phases in default/grey (they never ran) (UX §5.5)
**And** an `alert alert-error` block appears above the phases section: "Run failed during {phase} phase. See phase details below for error output." (UX §5.5)
**And** the failed phase's accordion is auto-expanded on page load (server renders it open with content pre-loaded) (UX §5.5)
**And** the failed phase's log viewer is pre-filtered to ERROR severity (UX §5.5)

**Technical notes:**
- SSE streams: `/runs/{id}/events` (phase updates) and `/runs/{id}/logs/stream` (log lines) — FastAPI `StreamingResponse` with HTMX SSE extension
- SSE events: `phase-update`, `run-complete`, `run-failed`, `log-line`
- SSE connections consume minimal server resources (NFR7)
- Auto-scroll: CSS `scroll-snap-align: end` trick or minimal inline JS
- Failed run: server pre-renders the failed phase accordion as open with content included (not lazy-loaded)
