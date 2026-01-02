# Story 5.5: Display Phase Progress

Status: ready-for-dev
Linear Issue: not-configured
Epic: 5 - Pipeline Orchestration
Created: 2026-01-02

---

## Story

As a developer,
I want phase progress displayed in the console,
so that users understand what's happening.

## Acceptance Criteria

**Given** a phase starts
**When** displayed to user
**Then** shows `[PLAN] Starting phase...` with Rich formatting

**Given** LLM execution is in progress
**When** streaming
**Then** shows spinner + token count + elapsed time (UX-9)

**Given** a phase completes
**When** displayed
**Then** shows completion status, duration, and artifact count

**Given** the full pipeline
**When** running
**Then** progress bar shows overall progress across phases (UX-2)

## Tasks / Subtasks

### Task 1: Create ProgressDisplay Class
- [x] Create `src/adw/cli/progress.py`
- [x] Implement `ProgressDisplay` class using Rich
- [x] Accept `Console` instance for output
- [x] Track current phase and overall progress

### Task 2: Implement Phase Start Display
- [x] Add `on_phase_start(phase: str)` method
- [x] Format: `[PLAN] Starting phase...` with color
- [x] Update overall progress bar
- [x] Use Rich Panel for phase header

### Task 3: Implement LLM Progress Display
- [x] Add `on_llm_streaming(tokens: int, elapsed: float)` method
- [x] Show spinner while LLM is working
- [x] Display token count (updating)
- [x] Display elapsed time (updating)
- [x] Use Rich Live for real-time updates

### Task 4: Implement Phase Completion Display
- [ ] Add `on_phase_complete(phase: str, result: PhaseResult)` method
- [ ] Show ✓ checkmark with green color
- [ ] Display duration in human-readable format
- [ ] Display artifact count
- [ ] Update overall progress bar

### Task 5: Implement Overall Progress Bar
- [ ] Create Rich Progress bar for pipeline
- [ ] Show: `[Plan] ✓ [Build] ► [Verify] · [Validate] · [Document]`
- [ ] Update as phases complete
- [ ] Show percentage complete

### Task 6: Implement Error Display
- [ ] Add `on_phase_error(phase: str, error: ADWError)` method
- [ ] Show ✗ with red color
- [ ] Display error message
- [ ] Display suggestion
- [ ] Format with Rich Panel

### Task 7: Integrate with Orchestrator
- [ ] Add `progress_display` to Orchestrator
- [ ] Call `on_phase_start()` before each phase
- [ ] Call `on_phase_complete()` after each phase
- [ ] Call `on_phase_error()` on failures

### Task 8: Integrate with PhaseRunner
- [ ] Pass progress callback to LLM executor
- [ ] Update token count during streaming
- [ ] Update elapsed time during execution

### Task 9: Write Unit Tests
- [ ] Create `tests/unit/cli/test_progress.py`
- [ ] Test phase start display
- [ ] Test phase completion display
- [ ] Test progress bar updates
- [ ] Test error display
- [ ] Target: >80% coverage

### Task 10: Write Integration Tests
- [ ] Test full pipeline progress display
- [ ] Test single phase progress display
- [ ] Test error scenarios
- [ ] Verify Rich output formatting

---

## Developer Context

### Technical Requirements

- **Rich Library**: Use for all console output
- **Live Updates**: Spinner and token count update in place
- **Progress Bar**: Show overall pipeline progress
- **Color Coding**: Green for success, red for error, yellow for in-progress

### Architecture Compliance

**From architecture.md - Rich Integration:**
```
Terminal Output (Rich 14.1.0):
- `Console` for styled output and logging
- `Progress` for multi-phase progress display
- `Live` for real-time updating displays
- `Panel`, `Table` for structured output
```

**From PRD - UX Requirements:**
```
UX-2: Progress bar shows overall progress across phases
UX-9: Shows spinner + token count + elapsed time during LLM execution
```

**From architecture.md - CLI Output:**
```python
from rich.console import Console
console = Console()

# Progress/status - use Rich components
console.print("[bold green]✓[/] Phase completed: plan")
```

### Library & Framework Requirements

**Rich Progress Components:**
```python
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
```

**Phase Progress Display:**
```python
class ProgressDisplay:
    """Display progress for ADW pipeline execution.

    Uses Rich library for formatted console output with:
    - Phase headers with status indicators
    - Real-time LLM progress with spinner
    - Overall pipeline progress bar
    """

    PHASE_COLORS = {
        "plan": "blue",
        "build": "cyan",
        "verify": "yellow",
        "validate": "magenta",
        "document": "green",
    }

    STATUS_ICONS = {
        "pending": "·",
        "running": "►",
        "completed": "✓",
        "failed": "✗",
    }

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._current_phase: str | None = None
        self._live: Live | None = None
        self._progress: Progress | None = None

    def on_phase_start(self, phase: str) -> None:
        """Display phase starting message.

        Args:
            phase: Phase name starting
        """
        self._current_phase = phase
        color = self.PHASE_COLORS.get(phase, "white")

        self.console.print()
        self.console.print(
            Panel(
                f"[bold {color}]{phase.upper()}[/] Starting phase...",
                title=f"Phase {PHASE_SEQUENCE.index(phase) + 1}/{len(PHASE_SEQUENCE)}",
                border_style=color,
            )
        )

    def on_llm_start(self) -> None:
        """Start LLM progress display with spinner."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("·"),
            TextColumn("[cyan]Tokens: {task.fields[tokens]}"),
            TextColumn("·"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )
        self._live = Live(self._progress, console=self.console, refresh_per_second=4)
        self._live.start()
        self._task_id = self._progress.add_task(
            "LLM executing...",
            total=None,
            tokens=0,
        )

    def on_llm_progress(self, tokens: int) -> None:
        """Update LLM progress display.

        Args:
            tokens: Current token count
        """
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, tokens=tokens)

    def on_llm_complete(self) -> None:
        """Complete LLM progress display."""
        if self._live:
            self._live.stop()
            self._live = None
        self._progress = None

    def on_phase_complete(self, phase: str, result: PhaseResult) -> None:
        """Display phase completion.

        Args:
            phase: Phase that completed
            result: Phase result with metrics
        """
        color = self.PHASE_COLORS.get(phase, "white")
        duration = f"{result.duration_ms / 1000:.1f}s" if result.duration_ms else "N/A"
        artifacts = len(result.artifacts)

        self.console.print(
            f"[bold green]✓[/] [{color}]{phase.upper()}[/] completed "
            f"[dim]({duration}, {artifacts} artifacts, {result.tokens_used} tokens)[/]"
        )

    def on_phase_error(self, phase: str, error: ADWError) -> None:
        """Display phase error.

        Args:
            phase: Phase that failed
            error: The error that occurred
        """
        self.on_llm_complete()  # Stop any live display

        self.console.print()
        self.console.print(
            Panel(
                f"[bold red]Error:[/] {error.message}\n\n"
                f"[dim]Suggestion:[/] {error.suggestion}",
                title=f"[red]{phase.upper()} Failed[/]",
                border_style="red",
            )
        )

    def show_pipeline_summary(
        self,
        completed_phases: list[str],
        status: str,
        total_duration_ms: int,
        total_tokens: int,
    ) -> None:
        """Show pipeline summary at end of run.

        Args:
            completed_phases: List of completed phase names
            status: Final run status
            total_duration_ms: Total run duration
            total_tokens: Total tokens used
        """
        self.console.print()

        # Build phase status line
        phase_status = []
        for phase in PHASE_SEQUENCE:
            color = self.PHASE_COLORS.get(phase, "white")
            if phase in completed_phases:
                phase_status.append(f"[green]✓[/] [{color}]{phase}[/]")
            else:
                phase_status.append(f"[dim]· {phase}[/]")

        status_line = " → ".join(phase_status)

        # Format duration
        duration = f"{total_duration_ms / 1000:.1f}s"

        # Status color
        status_color = "green" if status == "completed" else "red"

        self.console.print(
            Panel(
                f"{status_line}\n\n"
                f"[bold]Status:[/] [{status_color}]{status}[/]\n"
                f"[bold]Duration:[/] {duration}\n"
                f"[bold]Tokens:[/] {total_tokens:,}",
                title="Pipeline Summary",
                border_style=status_color,
            )
        )
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   └── progress.py           # NEW - ProgressDisplay class
tests/
├── unit/
│   └── cli/
│       └── test_progress.py  # NEW
```

**Files to modify:**
```
src/adw/
├── core/
│   ├── orchestrator.py       # MODIFY - integrate ProgressDisplay
│   └── phase_runner.py       # MODIFY - add progress callbacks
```

**Orchestrator Integration:**
```python
# src/adw/core/orchestrator.py

class Orchestrator:
    def __init__(
        self,
        runs_dir: Path,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
        artifact_manager: ArtifactManager,
        *,
        progress_display: ProgressDisplay | None = None,
        max_retries: int = 3,
    ) -> None:
        # ... existing ...
        self.progress = progress_display

    def _execute_phase_with_transitions(
        self,
        context: RunContext,
        phase: str,
    ) -> RunContext:
        """Execute phase with progress display."""
        # Notify phase start
        if self.progress:
            self.progress.on_phase_start(phase)

        # ... existing execution logic ...

        try:
            result = self._execute_phase_with_retry(context, phase)

            # Notify completion
            if self.progress:
                self.progress.on_phase_complete(phase, result)

        except ADWError as e:
            # Notify error
            if self.progress:
                self.progress.on_phase_error(phase, e)
            raise

        return context
```

### Testing Requirements

**Test Framework:** pytest

**Test phase start display:**
```python
from io import StringIO
from rich.console import Console

def test_phase_start_shows_header():
    """Test that phase start shows formatted header."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    progress = ProgressDisplay(console)

    progress.on_phase_start("plan")

    output_text = output.getvalue()
    assert "PLAN" in output_text
    assert "Starting phase" in output_text
```

**Test phase completion display:**
```python
def test_phase_complete_shows_metrics():
    """Test that phase completion shows duration and artifacts."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    progress = ProgressDisplay(console)

    result = PhaseResult(
        phase="plan",
        status=PhaseStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        artifacts=["plan.md"],
        tokens_used=500,
    )

    progress.on_phase_complete("plan", result)

    output_text = output.getvalue()
    assert "✓" in output_text
    assert "PLAN" in output_text
    assert "500" in output_text  # tokens
```

**Test error display:**
```python
def test_error_shows_suggestion():
    """Test that error display includes suggestion."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    progress = ProgressDisplay(console)

    error = HookError(
        code="HOOK_FAILED",
        message="Pre-hook failed",
        suggestion="Check hook script",
        recoverable=False,
        phase="build",
    )

    progress.on_phase_error("build", error)

    output_text = output.getvalue()
    assert "Failed" in output_text
    assert "Pre-hook failed" in output_text
    assert "Check hook script" in output_text
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Story 5.1 (Orchestrator):**
- Orchestrator iterates through phases
- Good place to inject progress callbacks
- Has access to phase results

**From Story 5.2 (PhaseRunner):**
- PhaseRunner executes LLM
- Can add callback for streaming progress
- Has token counts in result

**Key patterns:**
- Use Rich for all output
- Non-blocking updates with Live
- Structured error display

---

## Git Intelligence

**From architecture.md:**
- Rich 14.1.0 is the terminal output library
- Console, Progress, Live, Panel components
- Color coding conventions established

**Existing patterns:**
- CLI uses Rich for formatted output
- Error messages use Panel with red border
- Success messages use green checkmark

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Rich Output**: Use Rich for all CLI output
2. **Color Coding**: Green=success, Red=error, Yellow=warning
3. **Status Icons**: ✓ complete, ► running, · pending, ✗ failed
4. **Progress**: Use Progress and Live for real-time updates

---

## Dev Notes

### Key Implementation Points

1. **Phase Colors**:
   ```python
   PHASE_COLORS = {
       "plan": "blue",
       "build": "cyan",
       "verify": "yellow",
       "validate": "magenta",
       "document": "green",
   }
   ```

2. **LLM Progress with Live**:
   ```python
   with Live(progress, console=console) as live:
       while streaming:
           progress.update(task, tokens=current_tokens)
   ```

3. **Phase Summary**:
   ```
   ✓ plan → ✓ build → ► verify → · validate → · document
   ```

4. **Error Panel**:
   ```python
   Panel(
       f"[bold red]Error:[/] {error.message}\n\n"
       f"[dim]Suggestion:[/] {error.suggestion}",
       title="BUILD Failed",
       border_style="red",
   )
   ```

### Project Structure Notes

- New ProgressDisplay class in cli/
- Integrated with Orchestrator and PhaseRunner
- Uses dependency injection for testability

### References

- [Source: _bmad-output/architecture.md#Rich-Integration]
- [Source: _bmad-output/prd.md#UX-Requirements]
- [Source: src/adw/cli/] - CLI structure

---

## Dev Agent Record

### Context Reference

Story 5.5 implements progress display for the ADW pipeline, providing real-time feedback during phase execution.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 5.1 (Orchestrator provides phase events), Story 5.2 (PhaseRunner provides LLM progress)
- **Blocks:** None - this is a UX enhancement
- **Can Parallel With:** Story 5.3, Story 5.4 (independent feature)

### Dependency Rationale
- Story 5.1: Orchestrator emits phase events
- Story 5.2: PhaseRunner provides token streaming events
- Progress display consumes these events

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-02 | BMAD Create-Story | Initial story creation with comprehensive context |
