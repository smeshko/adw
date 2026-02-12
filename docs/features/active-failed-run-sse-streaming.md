# Active & Failed Run Variants with SSE Streaming

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/run_detail.html`, `src/adw/dashboard/templates/partials/phase_detail.html`, `src/adw/dashboard/static/dashboard.css`, `src/adw/dashboard/templates/base.html`, `src/adw/dashboard/static/htmx-sse.js`

## Overview

Adds real-time Server-Sent Events (SSE) streaming to the run detail page for active runs, enabling live phase pipeline updates, elapsed time tracking, and streaming log output. Also adds a failed run variant with an error banner, auto-expanded failed phase accordion, and ERROR severity pre-filter on the log viewer.

## What Was Built

- **SSE event stream** (`/runs/{id}/events`): Emits `phase-update`, `run-complete`, and `run-failed` events with OOB swap HTML
- **SSE log stream** (`/runs/{id}/logs/stream`): Tails `live.log` and emits `log-line` events with formatted HTML divs
- **Active run template variant**: SSE wrapper with `sse-connect`, loading dots animation, pending phase "Waiting..." labels
- **Failed run template variant**: `alert-error` banner, auto-expanded failed phase accordion, ERROR severity pre-filter
- **Auto-scroll CSS**: Uses `overflow-anchor` to keep streaming log viewer pinned to bottom
- **HTMX SSE extension**: Bundled `htmx-sse.js` v2.2.2 in static assets

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py`: SSE streaming endpoints (`run_events_sse`, `log_stream_sse`), helper functions (`_format_sse_event`, `_render_phase_pipeline_oob`, `_render_log_line_html`), updated `_build_run_detail_context` for active/failed variants
- `src/adw/dashboard/templates/partials/run_detail.html`: SSE wrapper, OOB targets (`#run-phase-pipeline`, `#run-elapsed`), error banner, auto-expanded accordion
- `src/adw/dashboard/templates/partials/phase_detail.html`: SSE streaming log viewer for active phases, severity pre-filter for static viewer
- `src/adw/dashboard/static/dashboard.css`: Auto-scroll CSS with `overflow-anchor`
- `src/adw/dashboard/templates/base.html`: Includes `htmx-sse.js` extension
- `tests/unit/dashboard/test_active_failed_runs.py`: 45 unit tests covering all variants

### Key Patterns

- **SSE with async generators**: Each SSE endpoint uses a `StreamingResponse` wrapping an async generator that polls `RunContext` or tails a log file. The generator yields formatted SSE strings and terminates on terminal run states. Use this pattern for any future real-time dashboard endpoint.

- **OOB (out-of-band) swap rendering**: The `_render_phase_pipeline_oob` function builds HTML fragments with `hx-swap-oob="innerHTML"` attributes. When HTMX receives these via SSE, it swaps the content into matching element IDs without a full page reload. Use this for any partial UI update pushed from the server.

- **SSE event formatting**: The `_format_sse_event(event, data)` helper handles multi-line data per the SSE spec (each line prefixed with `data:`). Always use this helper rather than formatting SSE strings manually.

- **Log file tailing with offset tracking**: `log_stream_sse` tracks a `file_offset` to read only new content from `live.log`. On terminal state, it flushes remaining lines before closing. This avoids re-reading the entire file on each poll.

- **Auto-scroll via overflow-anchor**: The `.log-stream-container` CSS disables `overflow-anchor` on the container and enables it on `:last-child`, causing the browser to auto-scroll as new elements are appended. This is a pure CSS solution — no JavaScript needed.

### Code Examples

```python
# Creating a new SSE endpoint
from starlette.responses import StreamingResponse

@router.get("/runs/{run_id}/my-events")
async def my_sse_endpoint(run_id: str) -> StreamingResponse:
    async def generator():
        while True:
            data = "<div>Updated content</div>"
            yield _format_sse_event("my-event", data)
            await asyncio.sleep(2)
    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

```html
<!-- Connecting to SSE in a template -->
<div hx-ext="sse"
     sse-connect="/runs/{{ run_id }}/my-events"
     sse-close="terminal-event">
  <!-- Content that receives OOB swaps -->
  <div id="target-element">Initial content</div>
</div>
```

## How to Use

1. **Active runs** are detected via `status == "running"` in `_build_run_detail_context`, which sets `is_active=True`
2. The `run_detail.html` template conditionally wraps the page in an SSE container when `is_active` is true
3. SSE events update the phase pipeline and elapsed time via OOB swaps targeting `#run-phase-pipeline` and `#run-elapsed`
4. Terminal events (`run-complete`, `run-failed`) trigger a full page refresh via `hx-get` and close the SSE connection via `sse-close`
5. **Failed runs** are detected via `status == "failed"`, which renders an error banner, sets `failed_phase_name`, and auto-expands the failed phase accordion with `checked` checkbox
6. The failed phase loads with `hx-trigger="load"` (instead of `click once`) and passes `?severity=ERROR` for pre-filtering

## Configuration

No additional configuration required. The SSE endpoints use the existing `RunContext` and `live.log` file infrastructure.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| SSE poll interval (events) | int | 2s | Polling frequency for run state changes |
| SSE poll interval (logs) | int | 1s | Polling frequency for new log lines |

## Notes

- SSE connections are automatically cleaned up when the HTMX element is removed from the DOM or when `sse-close` events fire
- The `X-Accel-Buffering: no` header prevents nginx from buffering SSE responses
- Log file tailing starts from the end of the file (existing lines are not replayed)
- ANSI escape codes are stripped from log lines before rendering
- Log line messages are HTML-escaped to prevent XSS
