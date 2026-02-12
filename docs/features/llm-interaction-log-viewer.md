# LLM Interaction Viewer & Log Viewer

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/phase_detail.html`

## Overview

The LLM Interaction Viewer and Log Viewer add two new sub-sections to each phase accordion on the run detail page. The LLM viewer displays token counts and allows viewing the full prompt/response text for each phase. The Log Viewer provides searchable, filterable log output from the run's `live.log` file with severity coloring and phase pre-filtering.

## What Was Built

- LLM Interaction sub-section showing prompt/response token counts with inline [View] buttons that load full text via HTMX
- LLM prompt and response content endpoints (`GET /runs/{id}/phases/{phase}/prompt` and `.../response`) returning HTML fragments with XSS-safe pre blocks
- Log Viewer sub-section with search input (300ms debounce), severity filter (All/INFO/WARN/ERROR), and phase filter
- Log search endpoint (`GET /runs/{id}/logs?q=&level=&phase=`) returning filtered HTML log content fragments
- Three helper functions for data loading: `_load_llm_stats`, `_load_llm_content`, `_load_log_entries`
- ANSI escape code stripping for clean log display from colored terminal output
- Word-boundary regex phase filtering to prevent false positives (e.g., "plan" won't match "explain")

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py`: Three new route handlers (`llm_prompt`, `llm_response`, `log_search`), three new helper functions (`_load_llm_stats`, `_load_llm_content`, `_load_log_entries`), and updated `phase_detail` route to pass `llm_stats` to template context
- `src/adw/dashboard/templates/partials/phase_detail.html`: Two new card sections — LLM Interaction with token counts and View buttons, Log Viewer with search/filter controls bar and auto-loading log content div
- `tests/unit/dashboard/test_llm_viewer.py`: Unit tests for LLM stats loading, content endpoints, token display, and XSS prevention
- `tests/unit/dashboard/test_log_viewer.py`: Unit tests for log parsing, ANSI stripping, severity/phase/keyword filtering, and HTML rendering
- `tests/unit/dashboard/test_llm_log_integration.py`: Integration tests validating all acceptance criteria across the full request lifecycle

### Key Patterns

- **HTMX Debounced Multi-Filter Search**: The log viewer uses `hx-trigger="keyup changed delay:300ms"` on the search input with `hx-include="closest .card-body"` to send all filter values (search query, severity level, phase) in a single request. The severity dropdown uses `hx-trigger="change"` with the same `hx-include` pattern. A hidden `<input type="hidden" name="phase" value="{{ phase }}">` passes the pre-filtered phase value. Use this pattern for any dashboard section needing multi-parameter filtering with debounce.

- **Decoupled Data Loading**: LLM stats loading (`_load_llm_stats`) is wrapped in its own try/catch block, independent from artifact loading. This ensures that an artifact loading failure (e.g., corrupted directory) doesn't prevent LLM token counts from displaying. Apply this pattern when loading independent data sources for the same view — each should fail gracefully without affecting others.

- **ANSI-Aware Log Parsing**: `_load_log_entries` strips ANSI escape codes (`\x1b[...m`) before parsing timestamps and categories from `live.log`. The stripping happens both on the full line (for pattern matching) and on the extracted message (for display). Use `re.compile(r"\x1b\[[0-9;]*m")` to strip ANSI codes from any terminal output being displayed in the dashboard.

- **Word-Boundary Phase Filtering**: Phase filtering uses `re.compile(rf"\b{re.escape(phase)}\b")` to match whole words only. This prevents "plan" from matching "explain" or "planning" from matching "plan". Use word-boundary regex whenever filtering log content by phase name.

- **Latest-File LLM Stats Strategy**: `_load_llm_stats` iterates sorted files matching `*_{phase}_response.json` and keeps overwriting the result, so the last (highest-numbered) file wins. This correctly handles phase retries where `002_plan_response.json` should take precedence over `001_plan_response.json`.

### Code Examples

HTMX debounced search with multi-filter `hx-include`:

```html
<div class="card-body">
  <input type="text" name="q"
         hx-get="/runs/{{ run_id }}/logs"
         hx-trigger="keyup changed delay:300ms"
         hx-target="#log-content-{{ phase }}"
         hx-include="closest .card-body" />
  <select name="level"
          hx-get="/runs/{{ run_id }}/logs"
          hx-trigger="change"
          hx-target="#log-content-{{ phase }}"
          hx-include="closest .card-body">
    <option value="">All</option>
    <option value="INFO">INFO</option>
  </select>
  <input type="hidden" name="phase" value="{{ phase }}" />
  <div id="log-content-{{ phase }}"
       hx-get="/runs/{{ run_id }}/logs?phase={{ phase }}"
       hx-trigger="load">
  </div>
</div>
```

Log entry parsing with ANSI stripping:

```python
import re

ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
line_pattern = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+\[(\w+)\]\s+(.*)"
)

clean_line = ansi_pattern.sub("", raw_line).strip()
match = line_pattern.match(clean_line)
if match:
    timestamp, category, message = match.groups()
    message = ansi_pattern.sub("", message).strip()
```

## How to Use

1. **View LLM interaction**: Expand any phase accordion on the run detail page. The LLM Interaction card shows prompt and response token counts. Click "View" to load the full text inline.
2. **Search logs**: Use the search input in the Logs card. Typing triggers a filtered request after 300ms of inactivity.
3. **Filter by severity**: Select INFO, WARN, or ERROR from the severity dropdown. Combined with any active search query.
4. **Phase pre-filtering**: When opened from a phase accordion, logs are automatically filtered to entries mentioning that phase. The phase filter is passed as a hidden input.
5. **Add new log viewer filters**: Add new `<input>` or `<select>` elements inside the same `.card-body` — `hx-include="closest .card-body"` will automatically include them in filter requests.

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| Debounce delay | HTML attribute | `300ms` | `hx-trigger="keyup changed delay:300ms"` on search input |
| Log container height | CSS class | `max-h-80` | Maximum height for scrollable log container |
| LLM content height | CSS class | `max-h-96` | Maximum height for prompt/response pre blocks |
| Severity levels | Python sets | `ERROR/FATAL`, `WARN/WARNING` | Category-to-level mapping in `_load_log_entries` |
| Phase matching | Regex | Word-boundary `\b` | Prevents partial phase name matches in log filtering |

## Notes

- LLM prompt content requires `{phase}_prompt.txt` to exist in the artifacts directory. This file is only created if the phase runner persists the prompt. If not available, the View button returns "Prompt not found".
- LLM response content reads from `{phase}_output.md` in the artifacts directory, which is always created by the phase runner.
- LLM stats are read from `{NNN}_{phase}_response.json` files in the `llm/` directory. The latest numbered file is used to handle retry scenarios.
- Log parsing relies on the `[timestamp] [CATEGORY] message` format produced by ADW's logging setup. Lines not matching this pattern are silently skipped.
- The log viewer loads all matching entries at once (no pagination). For very large log files, this could be slow — pagination may be needed in the future.
