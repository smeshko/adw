# 5. Run Detail Page

**Route:** `/runs/{run_id}`
**Purpose:** Deep-dive into a single run. Full metadata, phase-by-phase breakdown, token usage, activity log, and special viewing modes (Terminal, Focus).
**PRD FRs:** FR13-14, FR16-27, FR36

## Layout

```
+-------------------------------------------------------------+
|  HEADER (global)                                            |
+=============================================================+
|                                                             |
|  RUNS / #01KH4F                                 (breadcrumb)|
|                                                             |
|  ADD PHASE PIPELINE VALIDATION    [RE-RUN] [ABORT]          |
|  adw-core . feature/adw-11                                  |
|  #01KH4F3SKGN3CJENGNPK3A3GB4                               |
|  =========================================================  |
|   3px accent-cream divider                                  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | [*] COMPLETED         Started 2 hours ago . 5m 12s    |  |
|  +-------------------------------------------------------+  |
|    ^ cream border + red offset shadow                       |
|                                                             |
|  +----------+----------+----------+----------+----------+   |
|  | PLAN     | BUILD    | VALIDATE | DOCUMENT | SHIP     |   |
|  | 0m 42s   | 2m 18s   | 1m 05s   | 0m 34s   | 0m 33s   |  |
|  +----------+----------+----------+----------+----------+   |
|    ^ green/amber/#333/red top borders per status            |
|    ^ cream border + red offset shadow                       |
|                                                             |
|  +---------------------------+---------------------------+  |
|  | // RUN DETAILS            | // TOKEN USAGE            |  |
|  | Run ID    #01KH4F...     | Input  [========--] 46,200|  |
|  | Project   adw-core       | Output [=====-----] 25,210|  |
|  | Branch    feature/adw-11 | Cache  [==--------] 12,602|  |
|  | Started   Feb 11, 2026   |                           |  |
|  | Duration  5m 12s          | API Calls     12          |  |
|  | Model     claude-opus-4-6 | Avg per Call  7,001       |  |
|  | Tokens    84,012          | Cache Hit %   15%         |  |
|  | Est Cost  $3.18           |                           |  |
|  +---------------------------+---------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | // ACTIVITY LOG                                       |  |
|  | +---------------------------------------------------+ |  |
|  | | 14:22:08  PLAN   Starting planning phase...       | |  |
|  | | 14:22:15  PLAN   Reading story file...            | |  |
|  | | 14:22:50  PLAN   Plan approved -- 3 tasks         | |  |
|  | | 14:25:09  BUILD  Build complete -- 2 created      | |  |
|  | | 14:26:15  VALID  All 14 tests passed              | |  |
|  | | 14:27:14  SHIP   PR #42 created -> staging        | |  |
|  | | 14:27:20  DONE   Run completed successfully       | |  |
|  | +---------------------------------------------------+ |  |
|  |   ^ bg-header, 1px #333 border, max-height 260px     |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  FOOTER (global)                                            |
+-------------------------------------------------------------+
```

## 5.1 Run Header

### Breadcrumb

Replaces the previous "Back to Overview" link with a structured breadcrumb trail.

```html
<div class="breadcrumb">
  <a href="/runs"
     hx-get="/runs"
     hx-target="#main"
     hx-push-url="/runs">Runs</a>
  <span class="sep">/</span>
  <span>#01KH4F</span>
</div>
```

**Styling:**
- Font: Azeret Mono, 10px, weight 600, uppercase, `letter-spacing: 0.08em`
- Color: `--text-muted`
- Link hover: `--accent-red`
- Separator: `/` character with `margin: 0 6px`
- `margin-bottom: 1rem`

The breadcrumb target adapts based on navigation context. If the user arrived from the overview (`?from=overview`), the first crumb links to `/` instead of `/runs`.

### Title Block

```html
<div class="run-header">
  <div class="run-title-block">
    <div class="run-title">Add phase pipeline validation</div>
    <div class="run-subtitle">adw-core &middot; feature/adw-11</div>
    <span class="run-id-tag">#01KH4F3SKGN3CJENGNPK3A3GB4</span>
  </div>
  <div class="run-actions">
    <button class="btn-outline">&#8635; RE-RUN</button>
    <button class="btn-danger">&#9632; ABORT</button>
  </div>
</div>
```

**Title:** Azeret Mono, 22px, weight 900, uppercase, `letter-spacing: 0.04em`, `--text-primary`.

**Subtitle:** Project name + branch, 13px, `--text-secondary`. Separated by a middle dot.

**Run ID tag:** Inline tag displaying the full ULID.
- Font: Azeret Mono, 10px, weight 600
- Color: `--text-muted`
- Background: `#252525`
- Border: `1px solid #444`
- Padding: `2px 8px`

**Action buttons (top-right, aligned with title block):**

| Button | Class | Style |
|--------|-------|-------|
| Re-run | `btn-outline` | Azeret Mono 10px weight 700 uppercase. `background: transparent`, `border: 2px solid #444`, `color: --text-secondary`. Hover: `border-color: --accent-cream`, `color: --text-primary`. |
| Abort | `btn-danger` | Azeret Mono 10px weight 700 uppercase. `background: transparent`, `border: 2px solid var(--accent-red)`, `color: --accent-red`. Hover: `background: --accent-red`, `color: white`. |

- **Abort** is only visible for active runs. Server omits it for completed/failed runs.
- **Re-run** opens the New Run modal pre-populated with this run's project + feature.

**Page header divider:** `border-bottom: 3px solid var(--accent-cream)` on `.run-header`, with `padding-bottom: 14px` and `margin-bottom: 1.5rem`.

## 5.2 Status Banner

A full-width card that consolidates run status into a single prominent row. Replaces the previous inline badge approach.

```html
<div class="status-banner" id="run-status-banner"
     hx-ext="sse"
     sse-connect="/runs/{id}/events"
     sse-swap="status-update">
  <div class="status-indicator"></div>
  <span class="status-text" style="color: var(--accent-green);">Completed</span>
  <span class="status-meta">Started 2 hours ago &middot; Duration 5m 12s</span>
</div>
```

**Container styling:**
- Background: `--bg-card`
- Border: `var(--border-harsh)` (2px solid cream)
- Box shadow: `var(--shadow-offset)` (4px 4px 0 accent-red)
- Padding: `14px 18px`
- `display: flex; align-items: center; gap: 12px`
- `margin-bottom: 1.5rem`

**Status indicator (left):** 14px square block. No border-radius.

| Status | Color | Animation |
|--------|-------|-----------|
| Completed | `--accent-green` | None |
| Running | `--accent-amber` | `pulse 2s ease-in-out infinite` (0% opacity 1 / 50% opacity 0.4) |
| Failed | `--accent-red` | None |
| Aborted | `--text-muted` | None |

**Status text (center):** Azeret Mono, 12px, weight 800, uppercase, `letter-spacing: 0.08em`. Color matches the status indicator color.

**Metadata (right, pushed to end):** `margin-left: auto`. Font size 12px, `--text-muted`. Displays relative start time and duration separated by a middle dot. For active runs the duration updates in real-time via SSE.

## 5.3 Phase Timeline

Replaces the previous DaisyUI `steps` component with a brutalist horizontal bar divided into phase segments.

```html
<div class="phase-timeline" id="phase-timeline"
     hx-ext="sse"
     sse-connect="/runs/{id}/events"
     sse-swap="phase-update">
  <div class="phase-step completed">
    <div class="phase-name">Plan</div>
    <div class="phase-duration">0m 42s</div>
    <span class="phase-icon" style="color: var(--accent-green);">&#10003;</span>
  </div>
  <div class="phase-step active">
    <div class="phase-name">Build</div>
    <div class="phase-duration">2m 18s</div>
    <span class="phase-icon">&#9696;</span><!-- spinner via CSS animation -->
  </div>
  <div class="phase-step pending">
    <div class="phase-name">Validate</div>
    <div class="phase-duration">&mdash;</div>
  </div>
  <!-- ... -->
</div>
```

**Container styling:**
- `display: flex; gap: 0`
- Border: `var(--border-harsh)` (2px solid cream)
- Box shadow: `var(--shadow-offset)` (4px 4px 0 accent-red)
- `margin-bottom: 1.5rem`

**Each `.phase-step`:**
- `flex: 1`
- Padding: `14px 16px`
- `border-right: 1px solid #333` (last child: none)
- Background: `--bg-card`
- Position: relative (for icon placement)

**Top border (3px) by status:**

| Status | Top border | Background |
|--------|-----------|------------|
| Completed | `3px solid var(--accent-green)` | `--bg-card` |
| Active | `3px solid var(--accent-amber)` | `--bg-card-hover` (`#252525`) |
| Pending | `3px solid #333` | `--bg-card` |
| Failed | `3px solid var(--accent-red)` | `--bg-card` |

**Phase name:** Azeret Mono, 10px, weight 800, uppercase, `letter-spacing: 0.1em`. Color matches status:
- Completed: `--accent-green`
- Active: `--accent-amber`
- Pending: `--text-muted`
- Failed: `--accent-red`

**Phase duration:** 11px, `--text-muted`. Displays `--` for pending phases.

**Phase icon:** 14px, positioned `top: 12px; right: 12px` (absolute within the step).
- Completed: `checkmark` in accent-green
- Active: CSS spinner animation (rotating element) in accent-amber
- Failed: `X` in accent-red
- Pending: no icon

**Active run behavior:**
- The active phase step has `--bg-card-hover` background for visual emphasis
- Duration updates via SSE: `sse-swap="phase-update"` replaces the entire timeline bar
- The spinner icon animates continuously

**Failed run behavior:**
- Failed phase gets `3px solid var(--accent-red)` top border
- All subsequent (pending) phases remain with `3px solid #333`

## 5.4 Detail Grid

Replaces the previous phase accordion with a 2-column CSS grid layout showing run metadata, token usage, and an activity log.

```css
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 1.5rem;
}
.detail-grid .full-width {
  grid-column: 1 / -1;
}
```

All cards within the grid use:
- Background: `--bg-card`
- Border: `var(--border-harsh)` (2px solid cream)
- Box shadow: `var(--shadow-offset)` (4px 4px 0 accent-red)
- Padding: `16px 18px`

### 5.4.1 Run Details Card (Left Column)

Section header: `// RUN DETAILS` (Azeret Mono 13px weight 800 uppercase, with `//` prefix in accent-red via `::before`).

Key-value metadata table:

```html
<table class="meta-table">
  <tr><th>Run ID</th><td>#01KH4F3SKGN3CJENGNPK3A3GB4</td></tr>
  <tr><th>Project</th><td>adw-core</td></tr>
  <tr><th>Branch</th><td>feature/adw-11</td></tr>
  <tr><th>Started</th><td>Feb 11, 2026 14:22:08 UTC</td></tr>
  <tr><th>Duration</th><td>5m 12s</td></tr>
  <tr><th>Model</th><td>claude-opus-4-6</td></tr>
  <tr><th>Total Tokens</th><td>84,012</td></tr>
  <tr><th>Est. Cost</th><td>$3.18</td></tr>
</table>
```

**Table styling:**
- `width: 100%; border-collapse: collapse`
- Row border: `border-bottom: 1px solid #2A2A2A` (last row: none)
- Key (`th`): Azeret Mono, 9px, uppercase, `letter-spacing: 0.12em`, weight 700, `--text-muted`, `text-align: left`, `width: 140px`, `padding: 8px 0`
- Value (`td`): 13px, `--text-primary`, `padding: 8px 0`

**Fields:**

| Key | Value | Notes |
|-----|-------|-------|
| Run ID | Full ULID with `#` prefix | Copy button (clipboard icon) inline |
| Project | Project name | |
| Branch | Branch name | `font-family: var(--font-body)` |
| Started | ISO timestamp | |
| Completed | ISO timestamp | `--` if active or failed |
| Duration | `Xm Ys` | Updates via SSE for active runs |
| Model | Model identifier | |
| Total Tokens | Formatted with commas | |
| Est. Cost | `$X.XX` | |
| PR | Link with external icon | Only if available |
| Linear | Link with external icon | Only if webhook-triggered |

**Copy button (Run ID):** Inline button with clipboard icon. Uses a minimal `onclick` to copy the full ULID to clipboard.

### 5.4.2 Token Usage Card (Right Column)

Section header: `// TOKEN USAGE`.

**Horizontal bar breakdown:**

```html
<div class="token-breakdown">
  <div class="token-row">
    <span class="token-label">Input</span>
    <div class="token-bar-track">
      <div class="token-bar-fill input" style="width: 55%;"></div>
    </div>
    <span class="token-count">46,200</span>
  </div>
  <div class="token-row">
    <span class="token-label">Output</span>
    <div class="token-bar-track">
      <div class="token-bar-fill output" style="width: 30%;"></div>
    </div>
    <span class="token-count">25,210</span>
  </div>
  <div class="token-row">
    <span class="token-label">Cache</span>
    <div class="token-bar-track">
      <div class="token-bar-fill cache" style="width: 15%;"></div>
    </div>
    <span class="token-count">12,602</span>
  </div>
</div>
```

**Bar styling:**
- `.token-label`: 12px, `--text-secondary`, `min-width: 60px`
- `.token-bar-track`: `flex: 1; height: 14px; background: #2A2A2A`
- `.token-bar-fill.input`: `background: var(--accent-red)`
- `.token-bar-fill.output`: `background: var(--accent-orange)`
- `.token-bar-fill.cache`: `background: var(--accent-amber)`
- `.token-count`: 11px, `--text-muted`, `min-width: 60px`, `text-align: right`, `font-variant-numeric: tabular-nums`

Bar widths are calculated server-side as percentages of the total token count and rendered as inline `style="width: XX%"`.

**API summary table (below bars):** Separated by `border-top: 1px solid #2A2A2A` with `margin-top: 16px; padding-top: 12px`. Uses the same `.meta-table` styling as Run Details.

| Key | Value |
|-----|-------|
| API Calls | Integer count |
| Avg per Call | Formatted token count |
| Cache Hit % | Percentage |

### 5.4.3 Activity Log Card (Full Width)

Spans both grid columns via `.full-width` (`grid-column: 1 / -1`).

Section header: `// ACTIVITY LOG`.

```html
<div class="card full-width">
  <div class="card-header"><h2>Activity Log</h2></div>
  <div class="log-output" id="activity-log">
    <div class="log-line">
      <span class="log-time">14:22:08</span>
      <span class="log-phase" style="color: var(--accent-amber);">PLAN</span>
      <span class="log-msg">Starting planning phase...</span>
    </div>
    <!-- ... more log lines ... -->
  </div>
</div>
```

**Log container (`.log-output`):**
- Background: `--bg-header` (`#0A0A0A`)
- Border: `1px solid #333`
- Padding: `14px`
- Font size: 12px
- Color: `--text-secondary`
- `max-height: 260px; overflow-y: auto`
- `line-height: 1.7`

**Log line structure (`.log-line`):**

Each line is a flex row with three parts:

| Part | Class | Style |
|------|-------|-------|
| Timestamp | `.log-time` | `--text-muted`, `min-width: 70px`, `flex-shrink: 0` |
| Phase label | `.log-phase` | Azeret Mono, 9px, weight 700, uppercase, `min-width: 50px`, `flex-shrink: 0`. Color per phase (see below). |
| Message | `.log-msg` | `--text-secondary` by default |

**Phase label colors:**
- Plan: `--accent-amber`
- Build: `--accent-orange`
- Validate: `--accent-green`
- Document: `--text-secondary`
- Ship: `--accent-red`
- Done: `--accent-green`

**Message severity classes:**
- `.log-success`: `color: var(--accent-green)` -- applied to success messages
- `.log-error`: `color: var(--accent-red)` -- applied to error messages
- `.log-warn`: `color: var(--accent-amber)` -- applied to warning messages

**Streaming (active runs):**

When the run is active, the activity log streams in real-time:

```html
<div class="log-output" id="activity-log"
     hx-ext="sse"
     sse-connect="/runs/{id}/logs/stream"
     sse-swap="log-line"
     hx-swap="beforeend">
  <!-- Existing log lines -->
  <!-- New lines appended via SSE -->
</div>
```

Auto-scrolls to bottom as new lines arrive using CSS `scroll-snap-align: end` on the last child, or a small inline JS snippet that scrolls on `htmx:sseMessage`.

## 5.5 Failed Run Variant

When a run has failed:

- **Status banner:** Indicator square is `--accent-red` (no animation). Status text reads `FAILED` in accent-red.
- **Phase timeline:** The failed phase has `3px solid var(--accent-red)` top border and its name is colored `--accent-red`. Phases after the failure show `3px solid #333` (they never ran).
- **Error alert:** A full-width alert block appears between the status banner and the phase timeline:

```html
<div class="status-banner" style="border-color: var(--accent-red);">
  <div class="status-indicator" style="background: var(--accent-red);"></div>
  <span class="status-text" style="color: var(--accent-red);">
    Failed during Build phase. See activity log for error output.
  </span>
</div>
```

- The activity log pre-filters to show ERROR-level entries highlighted in `--accent-red`.
- The failed phase step in the timeline is visually prominent (accent-red name + icon).

## 5.6 Active Run Variant

When viewing an active/running run:

- **Status banner:** Indicator square is `--accent-amber` with the `pulse` animation. Status text reads `RUNNING` in accent-amber. Duration in metadata updates via SSE.
- **Phase timeline:** The current phase has `--bg-card-hover` background and an accent-amber spinner icon. Completed phases show green checkmarks. Pending phases remain muted.
- **Abort button:** Visible in the run header. Clicking opens a confirmation modal before sending `POST /runs/{id}/abort`.
- **Activity log:** Streams new entries in real-time via SSE (`sse-connect="/runs/{id}/logs/stream"`). Auto-scrolls.
- **Token usage:** Updates via SSE with each completed API call. Bar widths and counts refresh.
- **Duration fields:** Both the status banner duration and the Run Details duration field update via SSE.

**SSE event types:**

| Event | Target | Behavior |
|-------|--------|----------|
| `status-update` | `#run-status-banner` | Replaces status banner (indicator, text, metadata) |
| `phase-update` | `#phase-timeline` | Replaces entire phase timeline bar |
| `log-line` | `#activity-log` | Appends new log line (`hx-swap="beforeend"`) |
| `stats-update` | `#run-details-card` | Updates token counts, cost, duration in metadata table |

When the run completes or fails, the server sends a final SSE event that swaps the entire page content to the completed/failed variant, closing the SSE connection.

## 5.7 Terminal Mode

**Activation:** Press `t` or click the "Terminal" button in the run header action bar. Available on the run detail page.

**Purpose:** Full-screen raw log view for monitoring a run without distraction. Provides a terminal-like experience with auto-scrolling monospace output.

### Layout

```
+-------------------------------------------------------------+
| #01KH4F  |  PLAN > BUILD  |  02:18 elapsed  |  [x] EXIT    |
+=============================================================+
|                                                             |
| 14:22:08  Starting planning phase...                        |
| 14:22:15  Reading story file: docs/stories/adw-11.md        |
| 14:22:32  Analyzing codebase structure (14 files scanned)   |
| 14:22:50  Plan approved -- 3 tasks identified               |
| 14:22:51  Starting implementation...                        |
| 14:23:04  Created: src/adw/dashboard/templates/...          |
| 14:23:28  Modified: src/adw/dashboard/templates/...         |
| 14:24:12  Created: tests/dashboard/test_phase_pipeline.py   |
| 14:25:09  Build complete -- 2 created, 1 modified           |
| ...                                                         |
|                                                    [auto-scroll]
+-------------------------------------------------------------+
```

### Behavior

**Activation:**
- Pressing `t` on the run detail page adds class `terminal-mode-active` to `<body>`
- Alternatively, clicking a "Terminal" button (`btn-outline`) in the run header actions triggers the same behavior
- URL updates to `/runs/{id}?mode=terminal` via `hx-push-url`

**Terminal header:** Minimal single-row bar at the top.
- Background: `--bg-header`
- Height: `40px`
- Border-bottom: `2px solid #333`
- Content: Run ID tag (`.run-id-tag` style), current phase label (Azeret Mono 10px uppercase, colored by phase), elapsed time (`--accent-amber`, updates via SSE), exit button (`btn-outline` with X icon, right-aligned)

**Log area:**
- Takes full viewport height minus the terminal header: `height: calc(100vh - 40px)`
- Background: `--bg-header` (`#0A0A0A`)
- Padding: `16px`
- `overflow-y: auto`
- Font: Inconsolata, 0.8rem (approximately 12.8px), weight 400
- Line height: 1.6
- Color: `--text-secondary`

**Log entry styling:**
- Each entry: `{timestamp}  {message}` (no phase label in terminal mode for density)
- Timestamp: `--text-muted`
- Error lines: `--accent-red`
- Warning lines: `--accent-orange`
- Success lines: `--accent-green`
- Default lines: `--text-secondary`

**Auto-scroll:** Log area auto-scrolls to the bottom as new entries arrive. A small "auto-scroll" indicator appears bottom-right when auto-scroll is active. If the user scrolls up manually, auto-scroll pauses and a "Resume auto-scroll" button appears.

**Global footer:** Hidden. `body.terminal-mode-active #status-bar { display: none; }`.
**Global header:** Hidden. `body.terminal-mode-active header { display: none; }`.

**Exit:** Press `t`, `Escape`, or click the exit button. Removes `terminal-mode-active` class, restores normal page layout, and updates URL back to `/runs/{id}`.

**SSE connection:** Reuses the same SSE connection as the normal activity log. `sse-connect="/runs/{id}/logs/stream"` with `sse-swap="log-line"` and `hx-swap="beforeend"`.

## 5.8 Focus Mode

**Activation:** Press `f` or click the "Focus" button in the run header action bar. Available on the run detail page.

**Purpose:** Distraction-free monitoring mode that shows only the essential run progress information in a clean vertical stack. Designed for "watching the run complete" without the detail overhead.

### Layout

```
+-------------------------------------------------------------+
|                        [x] EXIT FOCUS                        |
|                                                             |
|  +-------------------------------------------------------+  |
|  | PLAN [v] | BUILD [*] | VALIDATE | DOCUMENT | SHIP     |  |
|  +-------------------------------------------------------+  |
|    ^ brutalist border + shadow, full-width pipeline          |
|                                                             |
|                        02:18                                 |
|                     elapsed time                             |
|    ^ Azeret Mono 2rem weight 700, centered                   |
|                                                             |
|  +-------------------------------------------------------+  |
|  | 14:22:50  Plan approved -- 3 tasks identified          |  |
|  | 14:22:51  Starting implementation...                   |  |
|  | 14:23:04  Created: src/adw/dashboard/templates/...     |  |
|  | 14:25:09  Build complete -- 2 created, 1 modified      |  |
|  | ...                                                    |  |
|  +-------------------------------------------------------+  |
|    ^ scrollable log stream, auto-scroll                      |
|                                                             |
|  +-------------------------------------------------------+  |
|  |              RUN COMPLETED SUCCESSFULLY                |  |
|  +-------------------------------------------------------+  |
|    ^ completion banner, colored border by status             |
+-------------------------------------------------------------+
```

### Vertical Stack Components

**1. Focus Pipeline:**
Full-width phase timeline identical to section 5.3, but centered within the focus layout.
- Same brutalist border (`var(--border-harsh)`) and shadow (`var(--shadow-offset)`)
- Same per-phase status coloring

**2. Focus Elapsed Timer:**
- Centered block
- Font: Azeret Mono, 2rem (32px), weight 700
- Color: `--text-primary`
- Updates via SSE every second for active runs
- Below the timer: label "elapsed" in 10px Azeret Mono uppercase, `--text-muted`

**3. Focus Log Stream:**
- Scrollable log viewer similar to section 5.4.3
- `max-height: calc(100vh - 22rem)` to fill remaining viewport
- Auto-scroll behavior identical to Terminal Mode
- Same log line styling (timestamp + phase label + message)
- Background: `--bg-header`, border: `1px solid #333`
- Font: Inconsolata, 12px

**4. Focus Status Banner:**
- Centered completion message
- Appears when the run completes or fails
- Border color matches status: `--accent-green` (completed), `--accent-red` (failed)
- Font: Azeret Mono, 12px, weight 800, uppercase
- Background: `--bg-card`

### Behavior

**Activation:**
- Pressing `f` on the run detail page adds class `focus-mode-active` to `<body>`
- URL updates to `/runs/{id}?mode=focus` via `hx-push-url`

**Global header:** Hidden. `body.focus-mode-active header { display: none; }`.
**Global footer:** Hidden. `body.focus-mode-active #status-bar { display: none; }`.

**Exit button:** Top-right corner of the focus layout. `btn-outline` style. Exits on click, `f`, or `Escape`.

**Exit:** Removes `focus-mode-active` class, restores normal layout, updates URL to `/runs/{id}`.

**SSE connection:** Reuses the same SSE endpoint as the normal page. Events update the pipeline, timer, and log stream.

---
