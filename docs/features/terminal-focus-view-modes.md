# Terminal Mode & Focus Mode View Modes

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/templates/partials/terminal_mode.html`, `src/adw/dashboard/templates/partials/focus_mode.html`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/static/dashboard.css`, `src/adw/dashboard/templates/base.html`, `src/adw/dashboard/templates/partials/run_detail.html`, `src/adw/dashboard/templates/partials/keyboard_help.html`

## Overview

Adds two alternate view modes to the ADW dashboard: **Terminal Mode** for raw monospace log output, and **Focus Mode** for dedicated single-run monitoring with a prominent phase pipeline, elapsed timer, and streaming logs. Both modes replace the `#main` content area via HTMX partial swap, reuse existing SSE infrastructure, and can be toggled via keyboard shortcuts or UI buttons.

## What Was Built

- **Terminal Mode**: Full-screen monospace log viewer with SSE streaming for active runs and static log loading for completed runs
- **Focus Mode**: Dedicated single-run monitoring with full-width phase pipeline, large elapsed timer, streaming logs, and completion/failure status banners
- **Keyboard shortcuts**: `t` toggles terminal mode, `f` activates focus mode (run detail only), `Escape` exits both modes
- **UI toggle buttons**: "Terminal" and "Focus" buttons in the run detail action bar
- **View mode CSS**: ~150 lines of mode-specific styling using brutalist theme variables
- **3 new partial routes**: `/partials/terminal-mode/{run_id}`, `/partials/terminal-logs/{run_id}`, `/partials/focus-mode/{run_id}`

## Technical Implementation

### Key Files

- `src/adw/dashboard/templates/partials/terminal_mode.html`: Terminal mode template with SSE streaming (active) and HTMX static load (completed) variants
- `src/adw/dashboard/templates/partials/focus_mode.html`: Focus mode template with phase pipeline, elapsed time, SSE log streaming, and completion event listeners
- `src/adw/dashboard/partials.py`: Three route handlers — `terminal_mode` (context builder + template), `terminal_logs` (static log parser with ANSI stripping and severity coloring), `focus_mode` (RunContext loader with phase pipeline builder)
- `src/adw/dashboard/static/dashboard.css`: `.terminal-mode`, `.focus-mode`, and related CSS classes for both modes
- `src/adw/dashboard/templates/base.html`: Keyboard shortcut handlers for `t`, `f`, and `Escape` with mode state tracking
- `src/adw/dashboard/templates/partials/run_detail.html`: Terminal and Focus UI buttons in the action bar

### Key Patterns

- **View mode toggle pattern**: Each mode follows the same structure: (1) keyboard shortcut or button activates the mode, (2) `htmx.ajax('GET', '/partials/{mode}/{runId}', {target:'#main'})` swaps content, (3) a `data-{mode}` attribute on the root element signals mode is active, (4) Escape or the `✕` button exits by loading the run detail partial back into `#main`. Use this pattern for any future view modes.

- **Dual state detection**: Mode state is tracked via both a JavaScript flag (`terminalModeActive`/`focusModeActive`) AND a DOM attribute check (`document.querySelector('[data-terminal-mode]')`). The dual check is necessary because modes can be activated via UI buttons (which don't set the JS flag) or keyboard shortcuts (which do). Always check both when detecting mode state.

- **SSE stream reuse**: Both modes connect to the existing SSE endpoints (`/runs/{id}/events` and `/runs/{id}/logs/stream`) rather than creating new ones. Terminal mode uses only the log stream; Focus mode uses both the event stream (for phase pipeline OOB updates) and the log stream.

- **Mode exit via explicit navigation**: Exiting a mode uses `htmx.ajax('GET', '/runs/' + runId, {target:'#main'})` rather than `history.back()`. This is intentional — modes don't push URL state, so `history.back()` would navigate away from the run entirely. The exit functions (`exitTerminalMode`, `exitFocusMode`) are defined in inline `<script>` blocks within the mode templates.

- **Escape key hierarchy**: The Escape handler checks for active view modes first, then modals, then falls through to history navigation. This ensures mode exit takes priority over other Escape behaviors.

- **Run ID extraction**: The `getRunId()` helper first checks the `#run-detail` element's `sse-connect` attribute (parsing `/runs/{id}/events`), then falls back to URL path matching. This works both on the normal run detail page and within mode templates.

### Code Examples

Adding a new view mode following this pattern:

```html
{# new_mode.html #}
<div class="my-mode" data-my-mode data-run-id="{{ run_id }}">
  {# Mode content here #}
  <button onclick="exitMyMode()">Exit</button>
</div>

<script>
function exitMyMode() {
  var el = document.querySelector('[data-my-mode]');
  var runId = el ? el.getAttribute('data-run-id') : null;
  if (runId) {
    htmx.ajax('GET', '/runs/' + runId, {target:'#main'});
  }
}
</script>
```

```javascript
// In base.html keyboard handler — add shortcut
if (key === 'm') {
  if (document.querySelector('[data-my-mode]')) {
    // Exit mode
    var el = document.querySelector('[data-my-mode]');
    var exitId = el ? el.getAttribute('data-run-id') : getRunId();
    if (exitId) htmx.ajax('GET', '/runs/' + exitId, {target:'#main'});
  } else if (isRunDetailPage()) {
    var runId = getRunId();
    if (runId) htmx.ajax('GET', '/partials/my-mode/' + runId, {target:'#main'});
  }
  return;
}
```

```css
/* In dashboard.css — mode-specific styling */
.my-mode {
  display: flex;
  flex-direction: column;
  /* Use theme variables */
  background-color: var(--bg-void, #111111);
  color: var(--text-primary, #E8E4DF);
}
```

## How to Use

1. **Terminal Mode**: Navigate to any run detail page, press `t` or click the "Terminal" button. Logs display in monospace format. Active runs stream via SSE; completed runs load statically. Press `t` again or `Escape` to exit.
2. **Focus Mode**: Navigate to an active run detail page, press `f` or click the "Focus" button. See the full-width phase pipeline, large elapsed timer, and streaming logs. The view auto-updates on completion/failure. Press `f` again or `Escape` to exit.
3. **Adding new modes**: Create a partial template with a `data-{mode}` attribute, add a partial route, add CSS classes, and wire up a keyboard shortcut following the patterns above.

## Configuration

No configuration options. Both modes use the existing SSE infrastructure and run data.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| N/A | — | — | Both modes are zero-config |

## Notes

- Terminal mode adds `terminal-mode-active` class to `<body>` to hide the footer status bar, maximizing log real estate
- Focus mode reuses the `_build_phase_pipeline` and `_format_elapsed` helpers from existing partials code
- The `terminal_logs` route strips ANSI escape codes and HTML-escapes log content to prevent XSS
- Log severity coloring uses theme variables: `--accent-red` (ERROR), `--accent-orange` (WARN), `--text-primary` (INFO)
- SSE log styling in terminal mode requires explicit overrides for `[sse-swap] > div` selectors because SSE-streamed HTML uses different classes than statically rendered logs
- The `htmx:afterSettle` listener resets mode flags and removes the `terminal-mode-active` body class when `#main` content changes (e.g., via navigation links)
