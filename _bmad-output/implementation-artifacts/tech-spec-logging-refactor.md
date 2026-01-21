# Tech-Spec: Logging System Refactor

**Created:** 2026-01-21
**Status:** Ready for Development

## Overview

### Problem Statement

The current ADW logging system is overcomplicated and broken:

1. **`adw logs follow` doesn't work** - Only 6 sparse entries logged to `logs.jsonl` with null context (`run_id`, `phase` are null). The command seeks to end of file and waits, but almost nothing is written.

2. **Console output bypasses logging** - Rich terminal output goes directly to stdout, not through the logging infrastructure. The interesting stuff (LLM tokens, progress) never reaches log files.

3. **Too many commands** - 9 log commands when only 2-3 are useful:
   - `show` - useless (duplicates stdout with less info)
   - `follow` - broken
   - `llm` - poor visualization
   - `tools` - poor visualization
   - `snapshots`, `diff`, `search` - niche/redundant
   - `state` - actually useful
   - `export` - useful for sharing

4. **Too many log files** - Multiple files created that provide no value:
   - `logs.jsonl` - structured but sparse, context is null
   - `raw.log` - redundant
   - `llm/*.json` - separate capture, poor visualization
   - `tools.jsonl` - separate from main flow

### Solution

Simplify to a single real-time stream that captures everything:

1. **One log file**: `live.log` - human-readable, formatted, real-time stream of all activity
2. **Three commands**: `follow` (real-time), `state` (inspect), `export` (share)
3. **LLM tokens always captured** - No flag needed, tokens stream to `live.log`
4. **Main terminal stays clean** - Progress display only, use `follow` for verbose output

### Scope

**In Scope:**
- Create `LiveStreamTransport` for real-time formatted logging
- Route all output (LLM tokens, tool calls, progress) to live stream
- Rewrite `follow` command to tail `live.log` with ANSI color support
- Remove `--show-llm-output` flag (always capture, never show on main terminal)
- Remove 6 redundant commands (`show`, `llm`, `search`, `tools`, `snapshots`, `diff`)
- Update `export` to work with new file structure
- Delete unused logging infrastructure

**Out of Scope:**
- Backwards compatibility
- Performance optimization
- Changes to `state` command (keep as-is)

## Context for Development

### Codebase Patterns

**Logging module structure:**
```
src/adw/logging/
├── __init__.py      # Exports, convenience functions
├── manager.py       # LogManager class - coordinates transports
├── handler.py       # LogManagerHandler - bridges Python logging
├── console.py       # ConsoleTransport - Rich terminal output
├── file.py          # DELETE: RawFileTransport, StructuredFileTransport
├── llm_capture.py   # DELETE: LLMCaptureManager
├── stream.py        # DELETE: StreamLogger
├── redactor.py      # KEEP: Secret redaction
└── live_stream.py   # CREATE: LiveStreamTransport
```

**Current transport registration** (`bootstrap.py:119-128`):
```python
if run_dir:
    logs_dir = run_dir / "logs"
    jsonl_transport = StructuredFileTransport(logs_dir / "logs.jsonl")
    log_manager.register(jsonl_transport)
    raw_transport = RawFileTransport(logs_dir / "raw.log")
    log_manager.register(raw_transport)
```

**LLM token streaming** (`claude_code.py:388-396`):
```python
if self.show_llm_output:
    display_text = self._extract_display_text(decoded)
    if display_text:
        self.console.print(display_text, end="")

if stream_logger:
    stream_logger.token(decoded)
```

### Files to Reference

| File | Line | Purpose |
|------|------|---------|
| `src/adw/logging/manager.py` | 1-289 | LogManager API, transport protocol |
| `src/adw/logging/console.py` | 1-200 | ConsoleTransport pattern to follow |
| `src/adw/cli/bootstrap.py` | 78-157 | `create_log_manager()` setup |
| `src/adw/cli/app.py` | 192-195, 364-365 | `--show-llm-output` flag |
| `src/adw/executors/claude_code.py` | 66, 376-396 | LLM streaming logic |
| `src/adw/cli/logs.py` | 998-1093 | Current `follow` implementation |
| `src/adw/cli/logs.py` | 1439-1548 | Current `export` implementation |

### Technical Decisions

1. **`live.log` format**: Human-readable with ANSI colors, not JSONL. Format:
   ```
   [2026-01-21 14:32:01] [PHASE] Starting build phase
   [2026-01-21 14:32:02] [LLM] ▶ Token stream begins
   Here is my analysis of the code...
   [2026-01-21 14:32:15] [LLM] ◀ Token stream ends (1,234 tokens)
   [2026-01-21 14:32:15] [TOOL] Read: src/main.py
   ```

2. **Unbuffered writes**: Each write to `live.log` must flush immediately for real-time tailing

3. **ANSI preservation**: `follow` outputs with colors intact; user can pipe through `cat` to strip if needed

4. **No structured fallback**: We're fully removing JSONL - if someone needs structured data, they parse `live.log` or use `export`

## Implementation Plan

### Tasks

- [ ] **Task 1: Create LiveStreamTransport**
  - Create `src/adw/logging/live_stream.py`
  - Implement `LiveStreamTransport` class following `Transport` protocol
  - Write to `live.log` with timestamps, categories, ANSI formatting
  - Ensure unbuffered/flushed writes
  - Add methods for LLM token streaming (start/token/end markers)

- [ ] **Task 2: Update bootstrap to use LiveStreamTransport**
  - Modify `create_log_manager()` in `bootstrap.py`
  - Remove `StructuredFileTransport` and `RawFileTransport` registration
  - Add `LiveStreamTransport` registration when `run_dir` provided
  - Remove `LLMCaptureManager` setup
  - Remove `show_llm_output` parameter

- [ ] **Task 3: Update ClaudeCodeExecutor for live streaming**
  - Remove `show_llm_output` flag from constructor and all references
  - Always write tokens to live stream transport
  - Remove console printing of LLM output (main terminal stays clean)
  - Add token stream markers (start/end) for clear boundaries in `live.log`

- [ ] **Task 4: Remove --show-llm-output CLI flag**
  - Remove from `app.py` CLI definition
  - Remove from `create_orchestrator()` call
  - Update any help text or documentation references

- [ ] **Task 5: Rewrite `follow` command**
  - Change to tail `live.log` instead of `logs.jsonl`
  - For running processes: poll file for new content
  - For completed runs: output entire file (replay mode)
  - Preserve ANSI colors in output
  - Handle file not yet existing (wait with message)

- [ ] **Task 6: Update `export` command**
  - Update `_load_log_entries()` to read `live.log` as plain text
  - Remove `_load_llm_files()` calls and LLM interactions from JSON export
  - Update HTML report generation to use `live.log`
  - Keep snapshots and context.json handling

- [ ] **Task 7: Remove redundant commands**
  - Delete from `logs.py`: `show`, `llm`, `search`, `tools`, `snapshots`, `diff`
  - Remove associated helper functions
  - Update `logs_app` command group

- [ ] **Task 8: Delete unused files**
  - Delete `src/adw/logging/file.py`
  - Delete `src/adw/logging/llm_capture.py`
  - Delete `src/adw/logging/stream.py`
  - Delete `src/adw/security/tool_logger.py`

- [ ] **Task 9: Update logging __init__.py**
  - Remove exports: `RawFileTransport`, `StructuredFileTransport`, `LLMCaptureManager`, `StreamLogger`
  - Add export: `LiveStreamTransport`
  - Update `__all__` list

- [ ] **Task 10: Clean up models**
  - Check if `LLMRequest`, `LLMResponse`, `LLMStreamEvent`, etc. in `models/logging.py` are used elsewhere
  - Remove if unused

- [ ] **Task 11: Update tests**
  - Remove tests for deleted components
  - Add tests for `LiveStreamTransport`
  - Update `follow` command tests
  - Update `export` command tests

### Acceptance Criteria

- [ ] **AC1**: `adw logs follow <run_id>` shows real-time LLM token output during a run
- [ ] **AC2**: `adw logs follow <run_id>` replays full output for completed runs
- [ ] **AC3**: Main terminal during `adw run` shows only progress, no LLM tokens
- [ ] **AC4**: `--show-llm-output` flag is removed and produces error if used
- [ ] **AC5**: Run directory contains only: `context.json`, `live.log`, `snapshots/`
- [ ] **AC6**: `adw logs export` produces valid tar/json/html with new structure
- [ ] **AC7**: `adw logs state` continues to work unchanged
- [ ] **AC8**: Commands `show`, `llm`, `search`, `tools`, `snapshots`, `diff` are removed
- [ ] **AC9**: All existing tests pass (after updates)
- [ ] **AC10**: No Python import errors from removed modules

## Additional Context

### Dependencies

- `filelock` - for concurrent write safety (keep using)
- `rich` - for ANSI formatting in `live.log`

### Testing Strategy

1. **Unit tests**: `LiveStreamTransport` write/flush behavior
2. **Integration tests**: Full run with `follow` in parallel
3. **Manual testing**: Run `adw run` in one terminal, `adw logs follow` in another

### Notes

- The `state` command uses snapshots directory which is preserved - no changes needed
- `export` tar format just copies the directory, so it automatically adapts
- Consider adding `--no-color` flag to `follow` for piping (future enhancement)
- Tool calls should be logged through the normal logging system, not separate file
