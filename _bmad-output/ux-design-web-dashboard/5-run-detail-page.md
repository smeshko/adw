# 5. Run Detail Page

**Route:** `/runs/{run_id}`
**Purpose:** Deep-dive into a single run. Full metadata, phase-by-phase breakdown, artifacts, logs, LLM interactions.
**PRD FRs:** FR13-14, FR16-27

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (global)                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ← Back to Overview                          [Abort] [Re-run]│
│                                                             │
│  my-api / Add CORS headers                     ✓ Completed  │
│  01HQ8K3M... · feature/add-cors · 4m 12s · 25 min ago      │
│                                                             │
│  PHASE PIPELINE                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ✓ Plan     ✓ Build     ✓ Validate   ✓ Doc    ✓ Ship│   │
│  │   22s        1m 48s      58s          32s       12s  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ METADATA ──────────────────────────────────────────┐    │
│  │  Run ID     01HQ8K3M...FULL_ID           [📋 Copy]  │    │
│  │  Project    my-api (/Users/ivo/code/my-api)          │    │
│  │  Feature    Add CORS headers for frontend access      │    │
│  │  Branch     feature/add-cors                          │    │
│  │  Started    2026-02-10 14:32:01                      │    │
│  │  Completed  2026-02-10 14:36:13                      │    │
│  │  Duration   4m 12s                                    │    │
│  │  Tokens     48,200 (in: 12,400 / out: 35,800)        │    │
│  │  Cost       $0.38                                     │    │
│  │  PR         #142 ↗                                    │    │
│  │  Linear     ADW-89 ↗                                  │    │
│  │  Artifacts  .adw/runs/01HQ8K3M.../                    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                             │
│  PHASES                                                     │
│                                                             │
│  ▸ Plan        22s    ✓   1,200 tokens    $0.01            │
│  ▸ Build      1m 48s  ✓  32,000 tokens    $0.25            │
│  ▾ Validate    58s    ✓   8,400 tokens    $0.07            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ┌─ Hooks ──────────────────────────────────────┐    │   │
│  │  │ pre:  ✓ git-setup.sh (0.4s)                  │    │   │
│  │  │ post: ✓ run-tests.sh (12.8s)                 │    │   │
│  │  │ post: ✓ lint.sh (0.8s)                       │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  ┌─ Artifacts ──────────────────────────────────┐    │   │
│  │  │ • validation-report.md          [View]        │    │   │
│  │  │ • test-results.json             [View]        │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  ┌─ LLM Interaction ───────────────────────────┐     │   │
│  │  │ Prompt: 2,100 tokens                [View]  │     │   │
│  │  │ Response: 6,300 tokens              [View]  │     │   │
│  │  └─────────────────────────────────────────────┘     │   │
│  │                                                      │   │
│  │  ┌─ Logs ──────────────────────────────────────┐     │   │
│  │  │ [Search...] [All ▾] [Phase: Validate ▾]     │     │   │
│  │  │                                              │     │   │
│  │  │ 14:34:01  INFO   Running test suite...       │     │   │
│  │  │ 14:34:08  INFO   42 tests passed             │     │   │
│  │  │ 14:34:09  INFO   Lint check passed           │     │   │
│  │  │ 14:34:12  INFO   Validation complete         │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ▸ Document    32s    ✓   4,200 tokens    $0.03            │
│  ▸ Ship        12s    ✓   2,400 tokens    $0.02            │
│                                                             │
│  FOOTER (global)                                            │
└─────────────────────────────────────────────────────────────┘
```

## 5.1 Run Header

**Back link:** `← Back to Overview` (or "← Back to Runs" if navigated from Runs List).
- Uses the `Referer` header or a query param `?from=runs` to determine context
- `hx-get="/" hx-target="#main" hx-push-url="/"`

**Title line:** `{project} / {feature}` with a status badge on the right.
- Project name: `font-semibold`
- Feature: normal weight
- Status badge: DaisyUI `badge badge-lg badge-{status}`

**Meta line:** Run ID (truncated, monospace), branch name, duration, relative time.
- `text-sm text-base-content/60 font-mono`

**Action buttons (top-right, aligned with back link):**
- **Abort** (only for active runs): `btn btn-error btn-outline btn-sm` → opens confirmation modal
- **Re-run**: `btn btn-primary btn-outline btn-sm` → opens New Run modal pre-populated with this run's project + feature

## 5.2 Phase Pipeline

Full-width horizontal phase visualization. Larger than the mini version on overview cards.

**DaisyUI:** `steps steps-horizontal w-full`

Each step:
- Label: Phase name
- Sub-label: Duration (`font-mono text-xs`)
- State: `step-success` (completed), `step-error` (failed), `step-warning` (active/running), default (pending)

**Active run behavior:**
- Current phase step shows `loading loading-dots loading-sm` next to the label
- Duration updates via SSE: `hx-ext="sse" sse-connect="/runs/{id}/events" sse-swap="phase-update"`

**Failed run behavior:**
- Failed phase is `step-error`
- Phases after the failure are default (grey) — they never ran

## 5.3 Metadata Card

**DaisyUI:** `card card-bordered bg-base-200`

Key-value layout using a 2-column CSS grid:
```css
.metadata-grid {
  display: grid;
  grid-template-columns: 8rem 1fr;
  gap: 0.25rem 1rem;
}
```

**Fields:**

| Key | Value | Notes |
|-----|-------|-------|
| Run ID | Full ULID | `font-mono text-sm` + copy button |
| Project | Name + path | Path in `text-base-content/50 text-xs` |
| Feature | Full description | Untruncated |
| Branch | Branch name | `font-mono text-sm` |
| Started | ISO timestamp | `font-mono text-sm` |
| Completed | ISO timestamp | `font-mono text-sm` (or "—" if active/failed) |
| Duration | `Xm Ys` | `font-mono` |
| Tokens | Total (in: X / out: Y) | `font-mono text-sm` |
| Cost | `$X.XX` | `font-mono text-sm` |
| PR | Link with `↗` icon | Only if available. Links to GitHub. |
| Linear | Link with `↗` icon | Only if webhook-triggered. Links to Linear. |
| Artifacts | File path | `font-mono text-xs` |

**Copy button (Run ID):** Inline button with clipboard icon. Uses a minimal inline `onclick` to copy to clipboard (the only client-side JS in the app besides HTMX and theme toggle).

## 5.4 Phase Accordion

Each phase is a collapsible section. This is the core of the detail page.

**DaisyUI:** `collapse collapse-arrow bg-base-200` for each phase.

**Collapsed state (always visible):**
```
▸ Build      1m 48s   ✓   32,000 tokens   $0.25
```
- Phase name (`font-semibold`)
- Duration (`font-mono text-sm`)
- Status icon (color-coded)
- Token count (`font-mono text-sm text-base-content/60`)
- Cost (`font-mono text-sm text-base-content/60`)

**Expanded state (lazy-loaded):**

The expanded content is **not loaded until the user clicks**. This keeps initial page load fast.

```html
<div class="collapse collapse-arrow bg-base-200">
  <input type="checkbox" />
  <div class="collapse-title">▸ Build 1m 48s ✓ 32,000 tokens $0.25</div>
  <div class="collapse-content"
       hx-get="/runs/{id}/phases/build"
       hx-trigger="click once"
       hx-swap="innerHTML">
    <!-- Content loads on first expand -->
  </div>
</div>
```

**Phase detail content (loaded via HTMX partial):**

### 5.4.1 Hooks Sub-section

```
┌─ Hooks ─────────────────────────────────────┐
│ pre:  ✓ git-setup.sh (0.4s)                │
│ post: ✓ run-tests.sh (12.8s)               │
│ post: ✓ lint.sh (0.8s)                     │
└─────────────────────────────────────────────┘
```

- DaisyUI `card card-compact bg-base-300` (slightly darker than parent)
- Each hook: type label (`pre`/`post`), status icon, script name, duration
- Failed hooks: red icon + error message inline

### 5.4.2 Artifacts Sub-section

```
┌─ Artifacts ─────────────────────────────────┐
│ • plan-output.md                    [View]  │
│ • 4 files modified                  [View]  │
└─────────────────────────────────────────────┘
```

- List of artifact files produced by this phase
- **[View] button:** `hx-get="/runs/{id}/artifacts/{path}" hx-target="#artifact-viewer"` — loads artifact content into an inline viewer panel (below the artifacts list)
- **Artifact viewer:** `card bg-base-300` with:
  - File name as title
  - Content in a `pre` block with `font-mono text-sm` (for text files)
  - Close button to collapse the viewer
  - For markdown files: server-side rendered HTML

### 5.4.3 LLM Interaction Sub-section

```
┌─ LLM Interaction ──────────────────────────┐
│ Prompt:    2,100 tokens             [View] │
│ Response:  6,300 tokens             [View] │
└────────────────────────────────────────────┘
```

- Summary line showing token counts for prompt and response
- **[View] button:** Lazy-loads the full prompt or response text
  - `hx-get="/runs/{id}/phases/{phase}/prompt"` or `.../response"`
  - Renders in a scrollable `pre` block with `max-h-96 overflow-y-auto`
  - `font-mono text-xs` for readability of long LLM text

### 5.4.4 Logs Sub-section

The log viewer is embedded within each phase's expanded content, pre-filtered to that phase.

**Controls bar:**
- Search input: `input input-bordered input-sm` with `hx-get` triggered on `keyup changed delay:300ms`
- Severity filter: `select select-bordered select-sm` (All, INFO, WARN, ERROR)
- Phase is pre-set to the current phase but can be changed

**Log display:**
- DaisyUI `mockup-code` or custom `bg-base-300 rounded-lg p-4 font-mono text-xs`
- Each line: `{timestamp} {level} {message}`
- Level coloring: INFO = default, WARN = `text-warning`, ERROR = `text-error`
- Scrollable container: `max-h-80 overflow-y-auto`
- Most recent entries at the bottom (chronological order)

**Streaming (active runs):**
- When the run is active and this phase is the current phase, the log viewer streams in real-time
- `hx-ext="sse" sse-connect="/runs/{id}/logs/stream" sse-swap="log-line"` with `hx-swap="beforeend"` to append new lines
- Auto-scrolls to bottom as new lines arrive (CSS `scroll-snap-align: end` trick or small inline JS)

## 5.5 Failed Run Variant

When a run has failed:
- The phase pipeline shows the failed phase in red (`step-error`)
- The failed phase's accordion is **auto-expanded** on page load (server renders it open)
- An `alert alert-error` block appears above the phases section:
  ```
  ⚠ Run failed during Build phase. See phase details below for error output.
  ```
- The failed phase's log section is pre-filtered to ERROR severity

## 5.6 Active Run Variant

When viewing an active/running run:
- The phase pipeline animates the current phase (pulsing dot)
- Elapsed time updates via SSE
- The "Abort" button is visible in the header
- The current phase's accordion can be expanded to see streaming logs
- Completed phases show their final content (lazy-loaded as usual)
- Pending phases show "Waiting..." in collapsed state

---
