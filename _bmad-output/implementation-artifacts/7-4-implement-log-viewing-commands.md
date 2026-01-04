# Story 7.4: Implement Log Viewing Commands

Status: review
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-03

---

## Story

As a user,
I want to view and search logs from CLI,
so that I can debug issues without navigating files manually.

## Acceptance Criteria

**Given** command `adw logs show <run_id>`
**When** executed
**Then** displays recent log entries from the run

**Given** command `adw logs follow <run_id>`
**When** run is active
**Then** streams new log entries in real-time (FR47)

**Given** command `adw logs search <pattern>`
**When** executed
**Then** searches logs across runs for matching entries (FR48)

**Given** command `adw logs llm <run_id>`
**When** executed
**Then** shows LLM prompts and responses for the run (FR49)

**Given** command `adw logs export <run_id>`
**When** executed
**Then** creates a shareable bundle of logs and state (FR52)

## Tasks / Subtasks

### Task 1: Create Logs CLI Subcommand (cli/logs.py)
- [x] Create `logs` Typer subapp
- [x] Register with main app in `cli/app.py`
- [x] Add common options (--run-id, --phase, --level)

### Task 2: Implement `logs show` Command
- [x] Accept run_id parameter
- [x] Load logs from `.adw/runs/<run_id>/logs/`
- [x] Display with Rich formatting
- [x] Support `--tail N` for last N entries
- [x] Support `--phase` filter
- [x] Support `--level` filter

### Task 3: Implement `logs follow` Command
- [x] Accept run_id parameter
- [x] Check if run is active (context.json status)
- [x] Use file watching for new log entries
- [x] Stream to console in real-time
- [x] Exit gracefully when run completes

### Task 4: Implement `logs search` Command
- [x] Accept pattern parameter (regex)
- [x] Search across all runs or specific run
- [x] Search in structured.jsonl files
- [x] Display matching entries with context
- [x] Support `--category` filter

### Task 5: Implement `logs llm` Command
- [x] Accept run_id parameter
- [x] Load files from `.adw/runs/<run_id>/llm/`
- [x] Display request/response pairs
- [x] Support `--phase` filter
- [x] Support `--request-only` and `--response-only`
- [x] Support `--tools` for tool calls only
- [x] Support `--stream` for token replay

### Task 6: Implement `logs export` Command
- [x] Accept run_id parameter
- [x] Create tarball/zip of run directory
- [x] Include: logs/, llm/, snapshots/, context.json
- [x] Support `--format json|html` for reports
- [x] Output to stdout or file with `--output`

### Task 7: Write Unit Tests
- [x] Test logs show with various filters
- [x] Test logs follow with mock file watcher
- [x] Test logs search pattern matching
- [x] Test logs llm output formatting
- [x] Test logs export bundle creation

---

## Relevant Feature Documentation

<!-- Debug commands defined in docs/arch-logging.md -->

---

## Developer Context

### Technical Requirements

**From PRD:**
- FR47: Real-time log streaming
- FR48: Log search across runs
- FR49: LLM prompt/response viewing
- FR52: Export shareable debug bundles

**Command Structure:**
```bash
adw logs show <run_id> [--tail N] [--phase PHASE] [--level LEVEL]
adw logs follow <run_id> [--phase PHASE]
adw logs search <pattern> [--run RUN_ID] [--category CAT]
adw logs llm <run_id> [--phase PHASE] [--request|--response|--tools|--stream]
adw logs export <run_id> [--format json|html] [--output FILE]
```

### Architecture Compliance

**Files to Create:**
```
src/adw/cli/
├── logs.py           # Logs subcommand group (NEW)
└── logs_display.py   # Display helpers for log output (NEW)
```

**Files to Modify:**
```
src/adw/cli/app.py    # Register logs subapp
```

**Integration Points:**
- Uses LogManager for log reading
- Uses RunLookup for run resolution
- Uses LLMCaptureManager for LLM file access

### Library & Framework Requirements

**Typer Subapp Pattern:**
```python
# cli/logs.py
import typer

logs_app = typer.Typer(name="logs", help="View and search logs")

@logs_app.command("show")
def logs_show(
    run_id: str = typer.Argument(..., help="Run ID to show logs for"),
    tail: int = typer.Option(50, "--tail", "-n", help="Last N entries"),
    phase: str | None = typer.Option(None, "--phase", help="Filter by phase"),
    level: str | None = typer.Option(None, "--level", help="Filter by level"),
):
    """Display log entries from a run."""
    ...

# cli/app.py
app.add_typer(logs_app, name="logs")
```

**File Watching for Follow:**
```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Or simpler polling approach
async def tail_file(path: Path):
    with open(path) as f:
        f.seek(0, 2)  # End of file
        while True:
            line = f.readline()
            if line:
                yield line
            else:
                await asyncio.sleep(0.1)
```

**Rich Output for Logs:**
```python
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

console = Console()

# Log entry display
table = Table(title=f"Logs for {run_id}")
table.add_column("Time", style="dim")
table.add_column("Level", style="bold")
table.add_column("Category")
table.add_column("Message")

for entry in log_entries:
    table.add_row(
        entry.timestamp,
        entry.level,
        entry.category,
        entry.message
    )
console.print(table)
```

### File Structure Requirements

**CLI Naming:**
- Subcommand: `logs` (noun)
- Commands: `show`, `follow`, `search`, `llm`, `export` (verbs)

**File Locations:**
- Logs: `.agent/runs/<run_id>/logs/structured.jsonl`
- LLM: `.agent/runs/<run_id>/llm/`
- Snapshots: `.agent/runs/<run_id>/snapshots/`

### Testing Requirements

**Test Cases:**
```python
def test_logs_show_displays_entries(tmp_path, runner):
    # Create mock log file
    # Run logs show command
    # Verify output contains expected entries

def test_logs_search_finds_pattern(tmp_path, runner):
    # Create logs with known content
    # Search for pattern
    # Verify matches returned

def test_logs_export_creates_bundle(tmp_path, runner):
    # Create run with logs
    # Run export command
    # Verify tarball created with expected contents
```

---

## Previous Story Intelligence

**From Story 7.1:**
- LogEvent model for parsing log entries
- File transports establish log file format
- structured.jsonl format for machine reading

**From Story 7.3:**
- LLMCaptureManager for accessing LLM files
- Request/response JSON format
- Stream JSONL format

**From Story 6.3-6.4:**
- `RunLookup` class for resolving run IDs
- Run ID validation patterns
- Status checking from context.json

**Dependencies:**
- Story 7.1 (log files exist)
- Story 7.3 (LLM captures for `logs llm` command)

---

## Git Intelligence

**Existing CLI patterns:**
- `cli/status.py` - shows run status
- `cli/list.py` - lists runs
- `cli/run_display.py` - display helpers
- Follow same patterns for logs commands

---

## Latest Technical Information

**Rich Live Display:**
```python
from rich.live import Live
from rich.table import Table

with Live(generate_table(), refresh_per_second=4) as live:
    while running:
        live.update(generate_table())
```

**JSONL Parsing:**
```python
import json

def read_jsonl(path: Path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Typer for CLI commands
- Rich for output formatting
- Context managers for file operations

---

## Dev Notes

- `logs follow` requires active run detection
- `logs search` should be efficient for large log files
- `logs export` creates self-contained debug bundles
- Consider pagination for large log outputs
- LLM viewing should handle large prompts/responses gracefully

### Project Structure Notes

- New CLI module: `cli/logs.py`
- Display helpers: `cli/logs_display.py`
- Register in main app

### References

- [Source: docs/arch-logging.md#Debug-Commands] - Command specifications
- [Source: src/adw/cli/status.py] - Similar CLI patterns
- [Source: src/adw/core/run_lookup.py] - Run ID resolution

---

## Dependencies

**Depends On:**
- Story 7.1: Multi-Tier Logging System (provides log files)
- Story 7.3: Capture LLM Interactions (provides `logs llm` data)

**Blocks:** None

**Parallel With:**
- Story 7.5: State Inspection Commands (similar CLI patterns)

---

## Dev Agent Record

### Context Reference
- Story 7.1 (LogEvent model, log file format)
- Story 7.3 (LLMCaptureManager, LLM file format)
- Story 7.5 (existing logs.py with state inspection commands)

### Agent Model Used
claude-opus-4-5-20250514

### Debug Log References
N/A

### Completion Notes List
- All 7 tasks completed successfully
- 24 new tests added for Story 7.4 commands (54 total CLI tests pass)
- Implemented 5 new CLI commands: show, follow, search, llm, export
- Follows existing patterns from Story 7.5 state inspection commands
- Export supports tar.gz, json, and html formats

### File List
**Modified:**
- `src/adw/cli/logs.py` - Added log viewing commands (show, follow, search, llm, export)
- `tests/unit/cli/test_logs.py` - Added comprehensive unit tests for new commands

**Architecture Compliance:**
- Uses existing RunLookup for run ID resolution
- Uses LogEvent model for parsing structured logs
- Uses Rich for terminal output formatting
- Integrates with existing logs_app Typer subcommand

