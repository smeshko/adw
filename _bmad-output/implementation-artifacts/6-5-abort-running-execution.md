# Story 6.5: Abort Running Execution

Status: ready-for-dev
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-03

---

## Story

As a user,
I want to abort a running execution,
So that I can stop a stuck or unwanted run.

## Acceptance Criteria

**Given** Ctrl+C during a run
**When** pressed
**Then** prompt "Abort run?" with Y/N confirmation (UX-8)

**Given** abort confirmed
**When** processed
**Then** current state is saved, run status set to "aborted"

**Given** abort cancelled
**When** processed
**Then** run continues from where it was

**Given** command `adw abort <run_id>`
**When** a run is in progress
**Then** the run is aborted remotely (if supported)

**Given** abort of a run not in progress
**When** attempted
**Then** ConfigError is raised with "Run is not active"

## Tasks / Subtasks

### Task 1: Implement Ctrl+C Confirmation (UX-8)
- [x] Modify InterruptionHandler to show confirmation prompt
- [x] Display "Abort run? [Y/n]" on first Ctrl+C
- [x] On 'Y' or Enter: proceed with abort
- [x] On 'N': cancel abort and continue run
- [x] On second Ctrl+C: force immediate abort

### Task 2: Implement Graceful Abort
- [x] Save current state before aborting
- [x] Update run status to "aborted" (distinct from "interrupted")
- [x] Create abort snapshot with reason
- [x] Stop any running LLM processes
- [x] Display abort confirmation message

### Task 3: Implement CLI Abort Command
- [x] Create `src/adw/cli/abort.py` with abort command
- [x] Add `run_id` required argument
- [x] Add `--force/-f` flag to skip confirmation
- [x] Validate run exists and is active
- [x] Display result of abort operation

### Task 4: Implement Remote Abort Logic
- [x] Add `abort()` method to Orchestrator
- [x] Check if run is in "running" status
- [x] Set abort flag that InterruptionHandler checks
- [x] Handle race condition with phase completion
- [x] Update context with "aborted" status

### Task 5: Handle Edge Cases
- [ ] Run not in progress → ConfigError "RUN_NOT_ACTIVE"
- [ ] Run already aborted → ConfigError "RUN_ALREADY_ABORTED"
- [ ] Run not found → ConfigError "RUN_NOT_FOUND"
- [ ] Multiple abort attempts → handle gracefully

### Task 6: Update Run Status Enum
- [ ] Add "aborted" as valid run status
- [ ] Update status transitions documentation
- [ ] Update StatusDisplay to handle "aborted" status
- [ ] Use distinct color for aborted (e.g., orange)

### Task 7: Write Unit Tests
- [ ] Create `tests/unit/cli/test_abort.py`
- [ ] Test abort active run succeeds
- [ ] Test abort inactive run fails
- [ ] Test abort non-existent run fails
- [ ] Test force flag skips confirmation
- [ ] Test Ctrl+C confirmation flow
- [ ] Target: >80% coverage

### Task 8: Write Integration Tests
- [ ] Create `tests/integration/cli/test_abort_integration.py`
- [ ] Test full abort flow
- [ ] Test state is saved on abort
- [ ] Test aborted run can be resumed
- [ ] Verify abort snapshot created

---

## Developer Context

### Technical Requirements

- **Ctrl+C Handling**: Intercept SIGINT with confirmation prompt (UX-8)
- **State Preservation**: Save state before aborting
- **Status Update**: Set status to "aborted"
- **Snapshot**: Create abort snapshot with reason
- **Remote Abort**: CLI command to abort from another terminal

### Architecture Compliance

**From PRD - UX-8:**
```
UX-8: Ctrl+C prompts "Abort run?" with Y/N confirmation
```

**From architecture.md - InterruptionHandler:**
```python
# Existing handler modified for confirmation
class InterruptionHandler:
    def handle_signal(self, signum, frame):
        if self._confirmation_pending:
            # Second Ctrl+C - force abort
            self._force_abort()
        else:
            # First Ctrl+C - show confirmation
            self._show_confirmation()
```

### Library & Framework Requirements

**Confirmation Prompt Implementation:**
```python
from rich.console import Console
from rich.prompt import Confirm

class InterruptionHandler:
    """Handle Ctrl+C with confirmation prompt."""

    def __init__(
        self,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
        console: Console | None = None,
    ) -> None:
        self.context_manager = context_manager
        self.snapshot_manager = snapshot_manager
        self.console = console or Console()
        self._confirmation_pending = False
        self._context: RunContext | None = None

    def handle_interrupt(self) -> bool:
        """Handle interrupt signal.

        Returns:
            True if run should abort, False to continue.
        """
        if self._confirmation_pending:
            # Second Ctrl+C - force abort
            self.console.print("\n[red]Forcing abort...[/]")
            return True

        # First Ctrl+C - show confirmation (UX-8)
        self._confirmation_pending = True
        self.console.print()

        try:
            if Confirm.ask("Abort run?", default=False):
                return True
            else:
                self.console.print("[green]Continuing...[/]")
                self._confirmation_pending = False
                return False
        except KeyboardInterrupt:
            # Ctrl+C during prompt - force abort
            self.console.print("\n[red]Forcing abort...[/]")
            return True

    def abort_gracefully(self, context: RunContext, reason: str = "user_abort") -> None:
        """Abort run gracefully with state preservation.

        Args:
            context: Current run context.
            reason: Reason for abort.
        """
        # Update status to aborted
        context = context.model_copy(
            update={
                "status": "aborted",
                "completed_at": datetime.now(UTC),
            }
        )

        # Save state
        self.context_manager.save(context)

        # Create abort snapshot
        self.snapshot_manager.create_snapshot(
            context,
            label=f"abort_{reason}",
            metadata={"reason": reason},
        )

        self.console.print(
            f"[yellow]Run aborted:[/] {context.run_id}\n"
            f"[dim]Resume with:[/] adw resume {context.run_id}"
        )
```

**Abort Command Implementation:**
```python
import typer
from rich.console import Console
from rich.prompt import Confirm

from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError

console = Console()

@app.command()
def abort(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to abort",
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Abort without confirmation",
    ),
) -> None:
    """Abort a running execution.

    The run must be in 'running' status to be aborted.
    Use --force to skip the confirmation prompt.

    Examples:
        adw abort 01HQXK5P3Z...
        adw abort 01HQXK5P3Z... --force
    """
    lookup = RunLookup(runs_dir=get_runs_dir())
    context = lookup.find_by_id(run_id)

    if not context:
        raise ConfigError(
            code="RUN_NOT_FOUND",
            message=f"Run {run_id} not found",
            suggestion="Use 'adw list' to see available runs",
            recoverable=False,
        )

    if context.status not in ("running",):
        raise ConfigError(
            code="RUN_NOT_ACTIVE",
            message=f"Run is not active (status: {context.status})",
            suggestion="Only running executions can be aborted",
            recoverable=False,
        )

    if not force:
        if not Confirm.ask(f"Abort run {run_id}?", default=False):
            console.print("[green]Abort cancelled[/]")
            return

    # Perform abort
    orchestrator = get_orchestrator()
    orchestrator.abort(run_id, reason="cli_abort")

    console.print(f"[yellow]Run aborted:[/] {run_id}")
    console.print(f"[dim]Resume with:[/] adw resume {run_id}")
```

**Orchestrator.abort() Method:**
```python
def abort(self, run_id: str, reason: str = "remote_abort") -> None:
    """Abort a running execution.

    Args:
        run_id: ID of the run to abort.
        reason: Reason for abort.

    Raises:
        ConfigError: If run is not active.
    """
    context = self.context_manager.load(run_id)

    if context.status != "running":
        raise ConfigError(
            code="RUN_NOT_ACTIVE",
            message=f"Run is not active (status: {context.status})",
            suggestion="Only running executions can be aborted",
            recoverable=False,
        )

    # Update status to aborted
    context = context.model_copy(
        update={
            "status": "aborted",
            "completed_at": datetime.now(UTC),
        }
    )

    # Save state
    self.context_manager.save(context)

    # Create abort snapshot
    self.snapshot_manager.create_snapshot(
        context,
        label=f"abort_{reason}",
        metadata={"reason": reason},
    )

    logger.info(
        "Run aborted",
        extra={"run_id": run_id, "reason": reason},
    )
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   └── abort.py             # NEW - abort command
tests/
├── unit/
│   └── cli/
│       └── test_abort.py    # NEW
└── integration/
    └── cli/
        └── test_abort_integration.py  # NEW
```

**Files to modify:**
```
src/adw/
├── cli/
│   ├── __init__.py          # MODIFY - export abort command
│   └── app.py               # MODIFY - register abort command
├── core/
│   ├── orchestrator.py      # MODIFY - add abort() method
│   └── interruption.py      # MODIFY - add confirmation prompt
├── models/
│   └── context.py           # MODIFY - add "aborted" status
```

### Testing Requirements

**Test Framework:** pytest

**Test abort active run:**
```python
def test_abort_active_run(tmp_path, mock_executor):
    """Test aborting an active run succeeds."""
    context = create_test_run(tmp_path, status="running")

    orchestrator = create_orchestrator(tmp_path)
    orchestrator.abort(context.run_id)

    # Verify status changed
    updated = lookup.find_by_id(context.run_id)
    assert updated.status == "aborted"

def test_abort_inactive_run_fails(tmp_path):
    """Test aborting inactive run raises error."""
    context = create_test_run(tmp_path, status="completed")

    orchestrator = create_orchestrator(tmp_path)

    with pytest.raises(ConfigError) as exc_info:
        orchestrator.abort(context.run_id)

    assert exc_info.value.code == "RUN_NOT_ACTIVE"
```

**Test Ctrl+C confirmation:**
```python
def test_ctrlc_confirmation_abort(monkeypatch):
    """Test Ctrl+C confirmation leads to abort."""
    handler = InterruptionHandler(context_manager, snapshot_manager)

    # Mock user input to confirm abort
    monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: True)

    result = handler.handle_interrupt()
    assert result is True

def test_ctrlc_confirmation_continue(monkeypatch):
    """Test Ctrl+C confirmation can continue."""
    handler = InterruptionHandler(context_manager, snapshot_manager)

    # Mock user input to cancel abort
    monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: False)

    result = handler.handle_interrupt()
    assert result is False
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Story 4.5 (Interruption Handling):**
- InterruptionHandler exists for Ctrl+C
- ShutdownRequested exception for graceful shutdown
- State saved on interruption

**From Story 6.1-6.4:**
- CLI command patterns established
- RunLookup for finding runs
- Error handling with ConfigError

**Key modifications:**
- Add confirmation prompt to InterruptionHandler
- Add "aborted" status distinct from "interrupted"
- Add abort() method to Orchestrator

---

## Git Intelligence

**Existing patterns:**
- InterruptionHandler in `src/adw/core/interruption.py`
- Signal handling for Ctrl+C/SIGTERM
- Context saving on interruption

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Rich Prompts**: Use `rich.prompt.Confirm` for Y/N prompts
2. **State Preservation**: Always save state before status change
3. **Snapshots**: Create snapshot on significant events
4. **Structured Logging**: Log abort events with context

---

## Dev Notes

### Key Implementation Points

1. **Ctrl+C Confirmation Flow (UX-8)**:
   ```
   ^C
   Abort run? [y/N]: y
   Run aborted: 01HQXK5P3Z7V8R2M4N6T9W1Y3C
   Resume with: adw resume 01HQXK5P3Z7V8R2M4N6T9W1Y3C
   ```

2. **Force Abort (Double Ctrl+C)**:
   ```
   ^C
   Abort run? [y/N]: ^C
   Forcing abort...
   Run aborted: 01HQXK5P3Z7V8R2M4N6T9W1Y3C
   ```

3. **Status Transitions**:
   - `running` → `aborted` (user abort)
   - `running` → `interrupted` (graceful shutdown)
   - Distinction: `aborted` = user chose to abort, `interrupted` = external signal

4. **Abort Snapshot**:
   ```json
   {
     "label": "abort_user_abort",
     "metadata": {
       "reason": "user_abort",
       "phase_at_abort": "build"
     }
   }
   ```

### Project Structure Notes

- Modifies existing InterruptionHandler
- Adds abort command to CLI
- Adds abort method to Orchestrator
- "aborted" is distinct from "interrupted"

### References

- [Source: _bmad-output/prd.md#UX-8] - Ctrl+C confirmation
- [Source: src/adw/core/interruption.py] - Existing handler
- [Source: _bmad-output/architecture.md#State-Persistence]

---

## Dev Agent Record

### Context Reference

Story 6.5 implements abort functionality for stopping running executions.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 6.1 (runs must exist), Story 4.5 (InterruptionHandler)
- **Blocks:** None
- **Can Parallel With:** Story 6.2 (resume), Story 6.3 (status), Story 6.4 (list), Story 6.6 (init)

### Dependency Rationale
- Story 6.1: Abort needs running executions
- Story 4.5: Modifies InterruptionHandler for confirmation

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-03 | BMAD Create-Epic | Initial story creation with comprehensive context |
