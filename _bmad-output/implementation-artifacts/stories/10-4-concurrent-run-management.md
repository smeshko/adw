# Story 10.4: Concurrent Run Management

Status: ready-for-dev
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want to run multiple ADW workflows simultaneously,
so that I can process multiple features in parallel.

## Acceptance Criteria

**Given** multiple `adw run` commands
**When** executed in parallel
**Then** each gets its own worktree and port allocation

**Given** maximum concurrent runs (15)
**When** a 16th run is attempted
**Then** error is raised: "Maximum concurrent runs reached. Use `adw list --running` to see active runs."

**Given** command `adw list --running`
**When** executed
**Then** shows all currently executing runs with their worktree paths and ports

**Given** orphaned worktrees (from crashed runs)
**When** `adw cleanup` is executed
**Then** stale worktrees are removed after confirmation

## Tasks / Subtasks

### Task 1: Create ConcurrentRunManager
- [x] Create `src/adw/worktree/concurrent.py` with `ConcurrentRunManager` class
- [x] Track active runs via lock files in `trees/.locks/`
- [x] Implement `can_start_run() -> bool` to check slot availability
- [x] Implement `register_run(run_id: str) -> None` to claim a slot
- [x] Implement `unregister_run(run_id: str) -> None` to release slot

### Task 2: Implement Run Slot Tracking
- [x] Create lock file per active run: `trees/.locks/<run_id>.lock`
- [x] Store run metadata in lock file (PID, start time, worktree path)
- [x] Check for stale locks (PID no longer running)
- [x] Implement `get_active_runs() -> list[ActiveRun]`

### Task 3: Add Maximum Concurrent Limit
- [ ] Check `len(get_active_runs()) < max_concurrent` before starting
- [ ] Raise `MaxConcurrentRunsError` with actionable message
- [ ] Include list of active runs in error for context

### Task 4: Implement --running Flag for List Command
- [ ] Add `--running` / `-r` flag to `adw list` command
- [ ] Filter to show only runs with status "running"
- [ ] Display worktree path and allocated ports for each
- [ ] Show elapsed time since start

### Task 5: Implement Cleanup Command
- [ ] Add `adw cleanup` command to CLI
- [ ] Find orphaned worktrees (worktree exists but no lock or stale lock)
- [ ] Show list of orphaned worktrees with confirmation prompt
- [ ] Remove worktrees and associated branches on confirmation
- [ ] Add `--force` flag to skip confirmation

### Task 6: Integrate with Orchestrator
- [ ] Call `can_start_run()` before worktree creation
- [ ] Call `register_run()` after successful worktree creation
- [ ] Call `unregister_run()` in finally block of run execution

### Task 7: Write Tests
- [ ] Test concurrent run limit enforcement
- [ ] Test lock file creation and cleanup
- [ ] Test stale lock detection
- [ ] Test --running filter for list command
- [ ] Test cleanup command identifies orphaned worktrees

---

## Dependencies

**Depends On:**
- 10-3: Port Allocation System (needs port allocation for display)
- 10-6: Worktree Branch Management (cleanup needs branch deletion)

**Blocks:** None (this is Wave 3)

**Can Parallel With:** None

---

## Developer Context

### Technical Requirements

1. **Lock File Management**
   - Use `filelock` for atomic lock acquisition
   - Store JSON metadata in lock file for inspection
   - Check PID validity using `os.kill(pid, 0)`

2. **Stale Lock Detection**
   - Lock is stale if PID doesn't exist
   - Lock is stale if older than configured timeout (e.g., 24 hours)
   - Clean up stale locks automatically during `get_active_runs()`

3. **Orphan Detection**
   - Worktree exists but no corresponding lock file
   - Worktree exists with stale lock (PID dead)
   - Worktree's run_id not in any context.json

### Architecture Compliance

**New Files:**
```
src/adw/
├── worktree/
│   ├── concurrent.py   # NEW: ConcurrentRunManager
│   └── ...
└── cli/
    └── cleanup.py      # NEW: Cleanup command
```

**ConcurrentRunManager Implementation:**
```python
# src/adw/worktree/concurrent.py
import json
import os
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

from adw.models.config import WorktreeConfig
from adw.exceptions import MaxConcurrentRunsError


class ActiveRun(BaseModel):
    run_id: str
    pid: int
    start_time: datetime
    worktree_path: Path
    backend_port: int | None = None
    frontend_port: int | None = None


class ConcurrentRunManager:
    def __init__(self, project_root: Path, config: WorktreeConfig):
        self.project_root = project_root
        self.config = config
        self.locks_dir = project_root / config.base_dir / ".locks"

    def _lock_path(self, run_id: str) -> Path:
        return self.locks_dir / f"{run_id}.lock"

    def _is_pid_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def get_active_runs(self) -> list[ActiveRun]:
        """Get all currently active runs, cleaning stale locks."""
        if not self.locks_dir.exists():
            return []

        active = []
        for lock_file in self.locks_dir.glob("*.lock"):
            try:
                data = json.loads(lock_file.read_text())
                if self._is_pid_running(data["pid"]):
                    active.append(ActiveRun(**data))
                else:
                    # Clean up stale lock
                    lock_file.unlink()
            except (json.JSONDecodeError, KeyError, OSError):
                # Corrupt lock file, remove it
                lock_file.unlink(missing_ok=True)

        return active

    def can_start_run(self) -> bool:
        return len(self.get_active_runs()) < self.config.max_concurrent

    def register_run(
        self,
        run_id: str,
        worktree_path: Path,
        backend_port: int | None = None,
        frontend_port: int | None = None,
    ) -> None:
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_data = {
            "run_id": run_id,
            "pid": os.getpid(),
            "start_time": datetime.now().isoformat(),
            "worktree_path": str(worktree_path),
            "backend_port": backend_port,
            "frontend_port": frontend_port,
        }
        self._lock_path(run_id).write_text(json.dumps(lock_data))

    def unregister_run(self, run_id: str) -> None:
        lock_path = self._lock_path(run_id)
        lock_path.unlink(missing_ok=True)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| os | stdlib | PID checking |
| json | stdlib | Lock file serialization |
| pathlib | stdlib | File operations |
| datetime | stdlib | Timestamps |

### File Structure Requirements

**Lock Directory Structure:**
```
trees/
├── .locks/                    # Lock file directory
│   ├── 01HQXK5.../           # Active run lock
│   │   └── (JSON metadata)
│   └── 01HQXK6.../           # Another active run
├── 01HQXK5.../               # Worktree
└── 01HQXK6.../               # Another worktree
```

**Lock File Format:**
```json
{
  "run_id": "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
  "pid": 12345,
  "start_time": "2026-01-05T10:30:00",
  "worktree_path": "/path/to/trees/01HQXK5...",
  "backend_port": 9100,
  "frontend_port": 9200
}
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/worktree/test_concurrent.py
class TestConcurrentRunManager:
    def test_can_start_run_when_under_limit(self, manager):
        """Returns True when under max_concurrent limit."""

    def test_cannot_start_run_at_limit(self, manager, max_active_runs):
        """Returns False when at max_concurrent limit."""

    def test_register_creates_lock_file(self, manager, tmp_path):
        """Lock file is created with correct metadata."""

    def test_unregister_removes_lock_file(self, manager, tmp_path):
        """Lock file is removed on unregister."""

    def test_stale_lock_cleaned_automatically(self, manager, stale_lock):
        """Stale locks (dead PID) are cleaned during get_active_runs."""


class TestOrphanDetection:
    def test_detect_worktree_without_lock(self, manager, orphan_worktree):
        """Identifies worktree without corresponding lock."""

    def test_detect_worktree_with_stale_lock(self, manager, stale_worktree):
        """Identifies worktree with dead PID lock."""
```

**CLI Tests:**
```python
# tests/unit/cli/test_cleanup.py
class TestCleanupCommand:
    def test_lists_orphaned_worktrees(self, runner, orphaned_setup):
        """Lists orphaned worktrees for confirmation."""

    def test_removes_on_confirmation(self, runner, orphaned_setup):
        """Removes worktrees when user confirms."""

    def test_force_skips_confirmation(self, runner, orphaned_setup):
        """--force removes without confirmation."""
```

---

## Previous Story Intelligence

**From Story 10-3:**
- Port allocation provides backend_port and frontend_port for display

**From Story 10-6:**
- Branch management provides cleanup of `adw/<run_id>` branches

---

## Git Intelligence

**Relevant Patterns:**
- Lock file patterns from Epic 4 (State Persistence)
- CLI command patterns from existing `cli/run.py`

---

## Latest Technical Information

**PID Checking Best Practices:**
- `os.kill(pid, 0)` doesn't actually send signal, just checks existence
- OSError raised if process doesn't exist
- Works cross-platform on Unix-like systems

**Lock File Considerations:**
- JSON format allows human inspection
- Include timestamp for debugging
- Clean up stale locks automatically to prevent accumulation

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- **CLI commands**: Follow existing patterns in `cli/`
- **Rich output**: Use tables for list display
- **Exception hierarchy**: Create `MaxConcurrentRunsError`

---

## Dev Notes

### Exception to Add

```python
# src/adw/exceptions.py
class MaxConcurrentRunsError(ADWError):
    """Raised when maximum concurrent runs limit is reached."""
    pass
```

### CLI Output for List --running

```
$ adw list --running

Active Runs (3 of 15)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Run ID                      ┃ Elapsed   ┃ Ports           ┃ Worktree    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ 01HQXK5P3Z7V8R2M4N6T9W1Y3C │ 5m 23s    │ 9100/9200       │ trees/01HQ… │
│ 01HQXK6A2B3C4D5E6F7G8H9I0J │ 2m 10s    │ 9101/9201       │ trees/01HQ… │
│ 01HQXK7B3C4D5E6F7G8H9I0J1K │ 45s       │ 9102/9202       │ trees/01HQ… │
└────────────────────────────┴───────────┴─────────────────┴─────────────┘
```

### CLI Output for Cleanup

```
$ adw cleanup

Found 2 orphaned worktrees:

1. trees/01HQOLD... (no lock file, created 2 days ago)
2. trees/01HQSTALE... (stale lock, PID 12345 not running)

Remove these worktrees and their branches? [y/N]: y

Removed: trees/01HQOLD...
Removed: trees/01HQSTALE...

Cleanup complete. 2 worktrees removed.
```

### References

- [Source: _bmad-output/epics/epic-10-worktree-isolation.md#Story 10.4]
- [Source: _bmad-output/architecture.md#CLI Command Patterns]

---

## Dev Agent Record

### Context Reference

Epic 10: Worktree Isolation - Story 10.4

### Agent Model Used

<!-- To be filled by dev agent -->

### Debug Log References

<!-- To be filled during implementation -->

### Completion Notes List

<!-- To be filled during implementation -->

### File List

<!-- To be filled during implementation -->
