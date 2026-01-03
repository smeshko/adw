# Story 6.2: Resume Failed or Interrupted Run

Status: ready-for-dev
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-03

---

## Story

As a user,
I want to resume a run from where it failed or was interrupted,
So that I don't lose progress.

## Acceptance Criteria

**Given** a run that failed at the Build phase
**When** I run `adw resume <run_id>`
**Then** it continues from the Build phase using Plan artifacts

**Given** a run that was interrupted
**When** I run `adw resume` without run_id
**Then** it resumes the most recent incomplete run

**Given** a completed run
**When** resume is attempted
**Then** ConfigError is raised with message "Run already completed"

**Given** a run with corrupted state
**When** resume is attempted
**Then** StateError is raised with suggestion to check snapshots

**Given** successful resume
**When** the resumed phase completes
**Then** it continues to the next phase automatically

## Tasks / Subtasks

### Task 1: Implement CLI Resume Command
- [x] Create `src/adw/cli/resume.py` with resume command
- [x] Add optional `run_id` argument (positional)
- [x] Add `--from-phase` option to restart from specific phase
- [x] Add `--verbose/-v` flag for debug output
- [x] Register command in main app

### Task 2: Implement Run Lookup
- [x] Create `src/adw/core/run_lookup.py` with `RunLookup` class
- [x] Implement `find_by_id(run_id)` to load specific run
- [x] Implement `find_most_recent_incomplete()` to find resumable run
- [x] Return `None` if no matching run found
- [x] Validate run directory structure exists

### Task 3: Implement Resume Logic in Orchestrator
- [x] Add `resume(run_id: str, from_phase: str | None)` method to Orchestrator
- [x] Load existing RunContext from context.json
- [x] Determine resume phase (failed phase or from_phase parameter)
- [x] Load artifacts from completed phases
- [x] Continue phase sequence from resume point

### Task 4: Validate Run State for Resume
- [x] Check run status (must be "failed", "interrupted", or "running")
- [x] Raise ConfigError for "completed" runs
- [x] Validate context.json is not corrupted
- [x] Raise StateError with snapshot suggestion if corrupted
- [x] Check required artifacts exist for resume phase

### Task 5: Load Artifacts from Previous Phases
- [x] Retrieve artifacts from completed phases via ArtifactManager
- [x] Make previous phase outputs available to resumed phase
- [x] Handle missing artifacts gracefully
- [x] Log which artifacts were loaded for debugging

### Task 6: Display Resume Header
- [x] Show "Resuming Run" panel with run_id
- [x] Display: original feature, failed phase, resume phase
- [x] Show completed phases with checkmarks
- [x] Indicate which phase will resume

### Task 7: Handle Edge Cases
- [x] Handle run_id that doesn't exist → ConfigError "RUN_NOT_FOUND"
- [x] Handle no incomplete runs available → inform user
- [x] Handle concurrent resume attempts → file lock prevents double resume
- [x] Handle resume from last phase (document) → continue to completion

### Task 8: Write Unit Tests
- [x] Create `tests/unit/cli/test_resume.py`
- [x] Test resume with valid run_id
- [x] Test resume without run_id (most recent)
- [x] Test resume completed run → error
- [x] Test resume non-existent run → error
- [x] Create `tests/unit/core/test_run_lookup.py`
- [x] Test find_by_id
- [x] Test find_most_recent_incomplete
- [x] Target: >80% coverage (achieved 92.18%)

### Task 9: Write Integration Tests
- [ ] Create `tests/integration/cli/test_resume_integration.py`
- [ ] Test full resume flow from failed run
- [ ] Test resume from interrupted run
- [ ] Test artifact loading across phases
- [ ] Verify progress display works correctly

---

## Developer Context

### Technical Requirements

- **State Loading**: Load RunContext from `.adw/runs/<run_id>/context.json`
- **Phase Continuation**: Resume from `current_phase` in context
- **Artifact Access**: Load previous phase artifacts for context
- **File Locking**: Prevent concurrent resume of same run
- **Error Messages**: Clear guidance on resume failures

### Architecture Compliance

**From architecture.md - State Persistence:**
```
.adw/runs/<run_id>/
├── context.json          # RunContext - live updated
├── snapshots/
│   └── <seq>_<label>.json  # StateSnapshot at key moments
└── artifacts/
    └── <phase>/
        └── <artifact>.json
```

**From architecture.md - Exception Hierarchy:**
```python
class ADWError(Exception):
    code: str           # e.g., "RUN_NOT_FOUND", "RUN_COMPLETED"
    recoverable: bool   # Can this be retried?
    phase: str | None   # Which phase failed
    suggestion: str     # Actionable next step for user
```

**From architecture.md - CLI Command Patterns:**
```
adw resume <run_id>        # Resume specific run
adw resume                 # Resume most recent incomplete
adw resume --from-phase build  # Restart from specific phase
```

### Library & Framework Requirements

**Resume Command Implementation:**
```python
import typer
from rich.console import Console
from rich.panel import Panel

from adw.core.orchestrator import Orchestrator
from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError, StateError

console = Console()

@app.command()
def resume(
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to resume (defaults to most recent incomplete)",
    ),
    from_phase: str | None = typer.Option(
        None,
        "--from-phase",
        help="Phase to resume from (overrides saved state)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Resume a failed or interrupted run.

    If no run_id is provided, resumes the most recent incomplete run.

    Examples:
        adw resume                    # Resume most recent
        adw resume 01HQXK5P3Z...      # Resume specific run
        adw resume --from-phase build # Restart from build phase
    """
    lookup = RunLookup(runs_dir=get_runs_dir())

    # Find the run to resume
    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            )
    else:
        context = lookup.find_most_recent_incomplete()
        if not context:
            console.print("[yellow]No incomplete runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit()

    # Validate resumable
    if context.status == "completed":
        raise ConfigError(
            code="RUN_COMPLETED",
            message="Run already completed",
            suggestion="Start a new run with 'adw run'",
            recoverable=False,
        )

    # Show resume header
    show_resume_header(context, from_phase)

    # Resume the run
    try:
        orchestrator = create_orchestrator(verbose=verbose)
        result = orchestrator.resume(context.run_id, from_phase=from_phase)
        console.print(f"[green]Run completed:[/] {result.run_id}")
    except ADWError as e:
        console.print(Panel(
            f"[red]Error:[/] {e.message}\n\n"
            f"[dim]Suggestion:[/] {e.suggestion}",
            title=f"[red]{e.code}[/]",
            border_style="red",
        ))
        raise typer.Exit(code=1)
```

**Run Lookup Implementation:**
```python
from pathlib import Path
from datetime import datetime
from adw.models import RunContext
from adw.core.context_manager import ContextManager

class RunLookup:
    """Find and load runs from the runs directory."""

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir
        self.context_manager = ContextManager(runs_dir)

    def find_by_id(self, run_id: str) -> RunContext | None:
        """Find a run by its ID.

        Args:
            run_id: The ULID of the run.

        Returns:
            RunContext if found, None otherwise.
        """
        run_path = self.runs_dir / run_id
        if not run_path.exists():
            return None

        try:
            return self.context_manager.load(run_id)
        except Exception:
            return None

    def find_most_recent_incomplete(self) -> RunContext | None:
        """Find the most recent incomplete run.

        Incomplete runs have status: "running", "failed", or "interrupted".

        Returns:
            Most recent incomplete RunContext, or None if none found.
        """
        if not self.runs_dir.exists():
            return None

        incomplete_runs: list[tuple[datetime, RunContext]] = []

        for run_dir in self.runs_dir.iterdir():
            if not run_dir.is_dir():
                continue

            try:
                context = self.context_manager.load(run_dir.name)
                if context.status in ("running", "failed", "interrupted"):
                    incomplete_runs.append((context.started_at, context))
            except Exception:
                continue

        if not incomplete_runs:
            return None

        # Sort by started_at descending and return most recent
        incomplete_runs.sort(key=lambda x: x[0], reverse=True)
        return incomplete_runs[0][1]
```

**Orchestrator Resume Method:**
```python
def resume(
    self,
    run_id: str,
    from_phase: str | None = None,
) -> RunContext:
    """Resume a failed or interrupted run.

    Args:
        run_id: ID of the run to resume.
        from_phase: Phase to resume from (optional override).

    Returns:
        Final RunContext after completion.

    Raises:
        ConfigError: If run cannot be resumed.
        StateError: If run state is corrupted.
    """
    # Load existing context
    context = self.context_manager.load(run_id)

    if context.status == "completed":
        raise ConfigError(
            code="RUN_COMPLETED",
            message="Run already completed",
            suggestion="Start a new run with 'adw run'",
            recoverable=False,
        )

    # Determine resume phase
    resume_phase = from_phase or context.current_phase
    if resume_phase not in PHASE_SEQUENCE:
        raise ConfigError(
            code="INVALID_PHASE",
            message=f"Unknown phase: {resume_phase}",
            suggestion=f"Valid phases: {', '.join(PHASE_SEQUENCE)}",
            recoverable=False,
        )

    # Update status to running
    context = context.model_copy(update={"status": "running"})
    self.context_manager.save(context)

    logger.info(
        "Resuming run",
        extra={
            "run_id": run_id,
            "from_phase": resume_phase,
            "completed_phases": context.phase_history,
        },
    )

    # Find the index of the resume phase
    start_idx = PHASE_SEQUENCE.index(resume_phase)

    try:
        with self.interruption_handler.protected_execution(context):
            for phase in PHASE_SEQUENCE[start_idx:]:
                self.interruption_handler.set_context(context)
                self.interruption_handler.check_shutdown()

                context = self._execute_phase_with_transitions(context, phase)

            # All phases complete
            context = context.model_copy(
                update={
                    "status": "completed",
                    "completed_at": datetime.now(UTC),
                }
            )
            self.context_manager.save(context)

            # Show pipeline summary
            if self.progress_display:
                # ... same as run() method

            logger.info("Resume completed", extra={"run_id": run_id})

    except ShutdownRequested:
        logger.info("Resume interrupted", extra={"run_id": run_id})
        raise

    except ADWError as e:
        context = context.model_copy(
            update={
                "status": "failed",
                "completed_at": datetime.now(UTC),
            }
        )
        self.context_manager.save(context)
        raise

    return context
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   └── resume.py            # NEW - resume command
├── core/
│   └── run_lookup.py        # NEW - RunLookup class
tests/
├── unit/
│   ├── cli/
│   │   └── test_resume.py   # NEW
│   └── core/
│       └── test_run_lookup.py  # NEW
└── integration/
    └── cli/
        └── test_resume_integration.py  # NEW
```

**Files to modify:**
```
src/adw/
├── cli/
│   ├── __init__.py          # MODIFY - export resume command
│   └── app.py               # MODIFY - register resume command
├── core/
│   ├── __init__.py          # MODIFY - export RunLookup
│   └── orchestrator.py      # MODIFY - add resume() method
```

### Testing Requirements

**Test Framework:** pytest

**Test resume with valid run_id:**
```python
def test_resume_failed_run(tmp_path, mock_executor):
    """Test resuming a failed run continues from correct phase."""
    # Create a failed run at build phase
    context = create_test_run(
        tmp_path,
        status="failed",
        current_phase="build",
        phase_history=["plan"],
    )

    orchestrator = create_orchestrator(tmp_path, mock_executor)
    result = orchestrator.resume(context.run_id)

    assert result.status == "completed"
    assert "build" in result.phase_history
    assert "verify" in result.phase_history
```

**Test resume without run_id:**
```python
def test_resume_most_recent_incomplete(tmp_path, mock_executor):
    """Test resume without run_id uses most recent incomplete."""
    # Create multiple runs
    old_failed = create_test_run(tmp_path, status="failed", age_hours=2)
    recent_failed = create_test_run(tmp_path, status="failed", age_hours=0)
    completed = create_test_run(tmp_path, status="completed", age_hours=1)

    lookup = RunLookup(tmp_path)
    context = lookup.find_most_recent_incomplete()

    assert context.run_id == recent_failed.run_id
```

**Test resume completed run raises error:**
```python
def test_resume_completed_run_raises_error(tmp_path):
    """Test that resuming completed run raises ConfigError."""
    context = create_test_run(tmp_path, status="completed")

    orchestrator = create_orchestrator(tmp_path)

    with pytest.raises(ConfigError) as exc_info:
        orchestrator.resume(context.run_id)

    assert exc_info.value.code == "RUN_COMPLETED"
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Story 6.1:**
- CLI command pattern established
- Orchestrator wiring established
- ProgressDisplay integration pattern
- Error handling with Rich Panel

**From Epic 4 Stories (State Persistence):**
- ContextManager saves/loads RunContext
- Atomic writes prevent corruption
- Snapshots available for debugging
- File locking prevents concurrent access

**From Story 4.5 (Interruption Handling):**
- InterruptionHandler manages Ctrl+C
- ShutdownRequested exception for graceful shutdown
- State saved before shutdown

**Key patterns:**
- Load context with ContextManager.load(run_id)
- Resume from current_phase in context
- Use same phase execution logic as run()

---

## Git Intelligence

**Recent commits:**
- feat(story-5-3): Pass Artifacts Between Phases
- feat(story-5-5): Display Phase Progress with Rich Console Output

**Existing patterns:**
- Orchestrator.run() is the main entry point
- Phase iteration uses PHASE_SEQUENCE constant
- Context updates use model_copy(update={...})

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Error Handling**: Use ConfigError/StateError from exception hierarchy
2. **Immutable Updates**: Use context.model_copy(update={...})
3. **File Locking**: Use filelock for concurrent access prevention
4. **Structured Logging**: Log with extra={} for context

---

## Dev Notes

### Key Implementation Points

1. **Resume Phase Determination**:
   ```python
   # Resume from current_phase (where it failed)
   # or from --from-phase if specified
   resume_phase = from_phase or context.current_phase
   ```

2. **Resume Header Display**:
   ```
   ╭──────────────── Resuming Run ────────────────╮
   │ Run ID: 01HQXK5P3Z7V8R2M4N6T9W1Y3C          │
   │ Feature: Add user authentication             │
   │ Completed: ✓ plan                            │
   │ Resuming from: build                         │
   ╰──────────────────────────────────────────────╯
   ```

3. **Status Transitions**:
   - `failed` → `running` (on resume)
   - `interrupted` → `running` (on resume)
   - `running` → `running` (continue stale run)

4. **Artifact Loading**:
   ```python
   # Artifacts from completed phases are available
   # via ArtifactManager.get_phase_artifacts(run_id, phase)
   for phase in context.phase_history:
       artifacts = artifact_manager.get_phase_artifacts(
           context.run_id, phase
       )
   ```

### Project Structure Notes

- RunLookup centralizes run finding logic
- Resume reuses Orchestrator phase execution logic
- Same ProgressDisplay integration as run command

### References

- [Source: _bmad-output/architecture.md#State-Persistence]
- [Source: _bmad-output/architecture.md#Exception-Hierarchy]
- [Source: _bmad-output/prd.md#FR2] - Resume from failure point
- [Source: _bmad-output/prd.md#NFR8] - Resume from any phase

---

## Dev Agent Record

### Context Reference

Story 6.2 implements the resume command, enabling users to continue runs that failed or were interrupted.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- src/adw/cli/resume.py (NEW)
- src/adw/cli/app.py (MODIFIED - added resume import and registration)
- src/adw/cli/run_display.py (MODIFIED - added show_resume_header())
- src/adw/core/run_lookup.py (NEW)
- src/adw/core/__init__.py (MODIFIED - export RunLookup)
- src/adw/core/orchestrator.py (MODIFIED - added resume() method)
- tests/unit/cli/test_resume.py (NEW)
- tests/unit/core/test_run_lookup.py (NEW)

---

## Dependencies

- **Depends On:** Story 6.1 (needs runs to exist), Story 4.2 (context persistence), Story 4.5 (interruption handling)
- **Blocks:** None - other stories can run in parallel
- **Can Parallel With:** Story 6.3 (status), Story 6.4 (list), Story 6.5 (abort)

### Dependency Rationale
- Story 6.1: Resume needs runs created by run command
- Story 4.2: ContextManager loads persisted context
- Story 4.5: InterruptionHandler manages graceful shutdown

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-03 | BMAD Create-Epic | Initial story creation with comprehensive context |
