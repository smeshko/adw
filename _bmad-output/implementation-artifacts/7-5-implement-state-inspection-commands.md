# Story 7.5: Implement State Inspection Commands

Status: done
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-03

---

## Story

As a user,
I want to inspect and diff state snapshots,
so that I can debug state-related issues.

## Acceptance Criteria

**Given** command `adw logs state <run_id>`
**When** executed
**Then** displays current or final state of the run (FR50)

**Given** command `adw logs state <run_id> --snapshot <seq>`
**When** executed
**Then** displays state at that specific snapshot

**Given** command `adw logs diff <run_id> <phase1> <phase2>`
**When** executed
**Then** shows differences between states at those phases (FR51)

**Given** command `adw logs snapshots <run_id>`
**When** executed
**Then** lists all available snapshots with labels (FR53)

**Given** snapshot inspection
**When** debugging
**Then** enables "time travel" to understand state evolution (NFR13)

## Tasks / Subtasks

### Task 1: Extend Logs CLI (cli/logs.py)
- [x] Add `state` subcommand
- [x] Add `diff` subcommand
- [x] Add `snapshots` subcommand

### Task 2: Implement `logs snapshots` Command
- [x] Accept run_id parameter
- [x] List all files in `.adw/runs/<run_id>/snapshots/`
- [x] Display table: #, Timestamp, Label, Trigger
- [x] Sort by sequence number

### Task 3: Implement `logs state` Command
- [x] Accept run_id parameter
- [x] Default: show current/final context.json
- [x] With `--snapshot <seq>`: load specific snapshot
- [x] With `--phase <name> --at start|end`: show phase boundary state
- [x] Format with Rich (JSON syntax highlighting)

### Task 4: Implement `logs diff` Command
- [x] Accept run_id and two phase identifiers
- [x] Load snapshots for both phases
- [x] Compute JSON diff (additions, removals, changes)
- [x] Display diff with color coding
- [x] Support `--from-snapshot` and `--to-snapshot` for specific snapshots

### Task 5: Create Diff Utility (utils/diff.py)
- [x] Implement `json_diff(a, b)` function
- [x] Return structured diff with paths
- [x] Support nested object comparison
- [x] Handle arrays appropriately

### Task 6: Write Unit Tests
- [x] Test snapshots listing
- [x] Test state display at different points
- [x] Test diff computation
- [x] Test CLI command integration

---

## Relevant Feature Documentation

<!-- State Snapshotter defined in docs/arch-logging.md -->

---

## Developer Context

### Technical Requirements

**From PRD:**
- FR50: Display run state
- FR51: State diff between phases
- FR53: List available snapshots
- NFR13: Time-travel debugging capability

**Command Structure:**
```bash
adw logs snapshots <run_id>
adw logs state <run_id> [--snapshot SEQ] [--phase PHASE --at start|end]
adw logs diff <run_id> --from-phase PHASE1 --to-phase PHASE2
adw logs diff <run_id> --from-snapshot SEQ1 --to-snapshot SEQ2
```

### Architecture Compliance

**Files to Create:**
```
src/adw/utils/
└── diff.py           # JSON diff utility (NEW)
```

**Files to Modify:**
```
src/adw/cli/logs.py   # Add state/diff/snapshots commands
```

**Snapshot File Structure:**
```
.adw/runs/<run_id>/snapshots/
├── 001_run_start.json
├── 002_plan_start.json
├── 003_plan_end.json
├── 004_build_start.json
├── 005_build_error.json
└── 006_build_retry_1.json
```

### Library & Framework Requirements

**JSON Diff:**
```python
from deepdiff import DeepDiff  # Or implement custom

def json_diff(old: dict, new: dict) -> dict:
    diff = DeepDiff(old, new, ignore_order=True)
    return {
        "added": diff.get("dictionary_item_added", {}),
        "removed": diff.get("dictionary_item_removed", {}),
        "changed": diff.get("values_changed", {}),
    }
```

**Rich Diff Display:**
```python
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()

# Show additions in green
console.print("[green]+ run.phase_results.build.status: 'success'[/]")
# Show removals in red
console.print("[red]- run.errors[0]: {...}[/]")
# Show changes in yellow
console.print("[yellow]~ run.current_phase: 'plan' → 'build'[/]")
```

**State Display:**
```python
from rich.syntax import Syntax

json_str = json.dumps(state, indent=2)
syntax = Syntax(json_str, "json", theme="monokai")
console.print(Panel(syntax, title=f"State at {snapshot_label}"))
```

### File Structure Requirements

**Snapshot Naming:**
- Format: `<seq>_<label>.json`
- Sequence: 3-digit zero-padded (001, 002, ...)
- Labels: run_start, phase_start, phase_end, error, etc.

**Parsing Snapshots:**
```python
import re

def parse_snapshot_name(filename: str) -> tuple[int, str]:
    match = re.match(r"(\d+)_(.+)\.json", filename)
    return int(match.group(1)), match.group(2)
```

### Testing Requirements

**Test Cases:**
```python
def test_snapshots_lists_all(tmp_path, runner):
    # Create mock snapshots
    # Run snapshots command
    # Verify all listed in order

def test_state_shows_specific_snapshot(tmp_path, runner):
    # Create run with snapshots
    # Request specific snapshot
    # Verify correct state displayed

def test_diff_shows_changes(tmp_path, runner):
    # Create two snapshots with differences
    # Run diff command
    # Verify additions/removals/changes shown
```

---

## Previous Story Intelligence

**From Story 4.3 (State Snapshots):**
- `SnapshotManager` class in `core/snapshot_manager.py`
- Creates snapshots at phase boundaries
- Labels: `<phase>_start`, `<phase>_end`

**From Story 7.4:**
- Logs CLI subapp structure
- Run ID resolution patterns
- Rich display patterns

**Dependency:** Story 7.1 must be completed first.

---

## Git Intelligence

**Existing patterns:**
- `core/snapshot_manager.py` - creates snapshots
- `cli/logs.py` (from 7.4) - logs command structure
- JSON handling in models

---

## Latest Technical Information

**DeepDiff Library:**
```bash
uv add deepdiff
```

Or implement minimal diff:
```python
def simple_diff(old: dict, new: dict, path: str = "") -> list[str]:
    changes = []
    all_keys = set(old.keys()) | set(new.keys())
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        if key not in old:
            changes.append(f"+ {current_path}: {new[key]}")
        elif key not in new:
            changes.append(f"- {current_path}: {old[key]}")
        elif old[key] != new[key]:
            if isinstance(old[key], dict) and isinstance(new[key], dict):
                changes.extend(simple_diff(old[key], new[key], current_path))
            else:
                changes.append(f"~ {current_path}: {old[key]} → {new[key]}")
    return changes
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Utilities in `src/adw/utils/`
- CLI commands delegate to core logic
- Rich for all formatted output

---

## Dev Notes

- Snapshots already exist from Story 4.3
- This story adds CLI commands to view them
- Diff utility useful beyond just this story
- Consider limiting diff output for large states
- Phase boundaries are the primary use case

### Project Structure Notes

- Extend existing logs CLI from Story 7.4
- New utility module for diff
- Reuse SnapshotManager from Epic 4

### References

- [Source: docs/arch-logging.md#State-Snapshotter] - Snapshot specification
- [Source: src/adw/core/snapshot_manager.py] - Existing snapshot logic
- [Source: docs/arch-logging.md#Snapshot-Viewer-CLI] - CLI examples

---

## Dependencies

**Depends On:**
- Story 7.1: Multi-Tier Logging System (provides logging infrastructure)
- Story 4.3: State Snapshots (provides snapshot files)

**Blocks:** None

**Parallel With:**
- Story 7.2, 7.3, 7.4, 7.6 can run in parallel

---

## Dev Agent Record

### Context Reference
- Story 7.4 (Logs CLI structure)
- Story 4.3 (State Snapshots - SnapshotManager)
- Architecture: docs/arch-logging.md

### Agent Model Used
claude-opus-4-5-20251101

### Debug Log References
N/A - Implementation completed successfully

### Completion Notes List
- All 6 tasks completed across 7 commits
- 38 unit tests passing (20 CLI tests, 18 diff utility tests)
- Commands registered in main app via `app.add_typer(logs_app, name="logs")`
- Custom json_diff implementation (no external dependency like deepdiff)
- Rich formatting for all output (tables, panels, syntax highlighting)

- Task 1: Created logs CLI subapp with state, diff, snapshots commands. Registered with main app.
- Task 2: Implemented snapshots command with table display showing sequence, timestamp, label, and trigger.
- Task 3: Implemented state command with Rich JSON syntax highlighting, supports --snapshot and --phase --at options.
- Task 4: Implemented diff command with color-coded output for additions (green), removals (red), and changes (yellow).
- Task 5: Created diff utility module with DiffResult class, supports nested dicts and arrays.
- Task 6: All 38 unit tests written and passing (20 CLI tests, 18 diff utility tests).

### File List
| File | Action | Description |
|------|--------|-------------|
| `src/adw/cli/app.py` | Modified | Added `logs_app` import and registration via `app.add_typer()` |
| `src/adw/cli/logs.py` | Created | State inspection CLI commands (snapshots, state, diff) - 536 lines |
| `src/adw/utils/__init__.py` | Modified | Added exports for `DiffResult` and `json_diff` |
| `src/adw/utils/diff.py` | Created | JSON diff utility with recursive comparison - 163 lines |
| `tests/unit/cli/test_logs.py` | Created | Unit tests for logs CLI commands - 407 lines, 20 tests |
| `tests/unit/utils/test_diff.py` | Created | Unit tests for diff utility - 174 lines, 18 tests |

