# Story 6.3: Check Run Status

Status: in-progress
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-03

---

## Story

As a user,
I want to check the status of any run,
So that I know its current state and outcome.

## Acceptance Criteria

**Given** command `adw status <run_id>`
**When** the run exists
**Then** it displays: run_id, feature, status, current/last phase, started_at, completed_at

**Given** command `adw status` without run_id
**When** runs exist
**Then** it shows status of the most recent run

**Given** the run is complete
**When** status is shown
**Then** it includes: total duration, phases completed, artifact count

**Given** the run failed
**When** status is shown
**Then** it includes: error message, suggestion, resume command (UX-3)

**Given** an invalid run_id
**When** status is requested
**Then** ConfigError is raised with code "RUN_NOT_FOUND"

## Tasks / Subtasks

### Task 1: Implement CLI Status Command
- [x] Create `src/adw/cli/status.py` with status command
- [x] Add optional `run_id` argument (positional)
- [x] Add `--json` flag for machine-readable output
- [x] Add `--verbose/-v` flag for detailed output
- [x] Register command in main app

### Task 2: Create Status Display
- [x] Create `src/adw/cli/status_display.py` with `StatusDisplay` class
- [x] Implement `show_status()` method using Rich Table
- [x] Display basic info: run_id, feature, status, phase
- [x] Display timestamps: started_at, completed_at
- [x] Use color coding for status (green=completed, red=failed, yellow=running)

### Task 3: Display Completed Run Details
- [x] Calculate total duration from timestamps
- [x] Count phases completed from phase_history
- [x] Count artifacts per phase from artifact directories
- [x] Display token usage summary
- [x] Format duration in human-readable form (e.g., "2m 34s")

### Task 4: Display Failed Run Details (UX-3)
- [x] Load error details from context or snapshot
- [x] Display error message and code
- [x] Display suggestion for resolution
- [x] Show resume command: `adw resume <run_id>`
- [x] Highlight failed phase in red

### Task 5: Implement JSON Output
- [x] Add `--json` flag to command
- [x] Serialize RunContext to JSON with all fields
- [x] Include calculated fields (duration, artifact_count)
- [x] Output clean JSON for scripting/automation

### Task 6: Handle Edge Cases
- [x] Handle run_id not found → ConfigError "RUN_NOT_FOUND"
- [x] Handle no runs exist → message "No runs found"
- [x] Handle corrupted context → show what's available
- [x] Handle very long feature descriptions → truncate

### Task 7: Write Unit Tests
- [ ] Create `tests/unit/cli/test_status.py`
- [ ] Test status with valid run_id
- [ ] Test status without run_id (most recent)
- [ ] Test status non-existent run → error
- [ ] Test JSON output format
- [ ] Test completed run shows duration/artifacts
- [ ] Test failed run shows error/suggestion
- [ ] Target: >80% coverage

### Task 8: Write Integration Tests
- [ ] Create `tests/integration/cli/test_status_integration.py`
- [ ] Test status of running run
- [ ] Test status of completed run
- [ ] Test status of failed run with resume hint
- [ ] Verify output formatting

---

## Developer Context

### Technical Requirements

- **Rich Tables**: Use Rich Table for formatted output
- **Color Coding**: Green=completed, Red=failed, Yellow=running
- **Duration Formatting**: Human-readable format (Xm Ys)
- **JSON Output**: Clean JSON for automation
- **Error Guidance**: Show resume command for failed runs (UX-3)

### Architecture Compliance

**From architecture.md - CLI Output Format:**
```python
# Use Rich for all formatted output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Tables - use Rich tables
table = Table(title="Run Status")
```

**From PRD - UX-3:**
```
UX-3: Failed status includes error message, suggestion, resume command
```

### Library & Framework Requirements

**Status Command Implementation:**
```python
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from adw.core.run_lookup import RunLookup
from adw.exceptions import ConfigError

console = Console()

@app.command()
def status(
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to check (defaults to most recent)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in JSON format",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed information",
    ),
) -> None:
    """Show status of a run.

    If no run_id is provided, shows status of the most recent run.

    Examples:
        adw status                    # Most recent run
        adw status 01HQXK5P3Z...      # Specific run
        adw status --json             # JSON output
    """
    lookup = RunLookup(runs_dir=get_runs_dir())

    # Find the run
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
        context = lookup.find_most_recent()
        if not context:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit()

    # Output format
    if json_output:
        output_json(context)
    else:
        display = StatusDisplay(console)
        display.show_status(context, verbose=verbose)
```

**Status Display Implementation:**
```python
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from adw.models import RunContext
from adw.core.constants import PHASE_SEQUENCE

class StatusDisplay:
    """Display run status using Rich."""

    STATUS_COLORS = {
        "running": "yellow",
        "completed": "green",
        "failed": "red",
        "interrupted": "orange1",
    }

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def show_status(
        self,
        context: RunContext,
        *,
        verbose: bool = False,
    ) -> None:
        """Display run status.

        Args:
            context: The run context to display.
            verbose: Show detailed information.
        """
        status_color = self.STATUS_COLORS.get(context.status, "white")

        # Truncate long feature descriptions
        feature = context.feature_description
        if len(feature) > 60:
            feature = f"{feature[:57]}..."

        # Calculate duration
        duration = self._format_duration(context)

        # Build status table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Run ID", context.run_id)
        table.add_row("Feature", feature)
        table.add_row("Status", f"[{status_color}]{context.status}[/]")
        table.add_row("Phase", context.current_phase or "—")
        table.add_row("Started", self._format_timestamp(context.started_at))

        if context.completed_at:
            table.add_row("Completed", self._format_timestamp(context.completed_at))

        table.add_row("Duration", duration)

        if verbose:
            table.add_row("Phases", self._format_phases(context))
            table.add_row("Tokens", f"{sum(context.phase_tokens.values()):,}")
            table.add_row("Artifacts", str(self._count_artifacts(context)))

        # Wrap in panel
        self.console.print()
        self.console.print(Panel(table, title="Run Status", border_style=status_color))

        # Show failure details (UX-3)
        if context.status == "failed":
            self._show_failure_details(context)

    def _show_failure_details(self, context: RunContext) -> None:
        """Show failure details with resume hint.

        UX-3: Failed status includes error message, suggestion, resume command.
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[red]Phase Failed:[/] {context.current_phase}\n\n"
                f"[dim]To resume this run:[/]\n"
                f"  adw resume {context.run_id}",
                title="[red]Recovery[/]",
                border_style="red",
            )
        )

    def _format_duration(self, context: RunContext) -> str:
        """Format run duration in human-readable form."""
        if context.completed_at and context.started_at:
            delta = context.completed_at - context.started_at
            total_seconds = int(delta.total_seconds())
        elif context.started_at:
            delta = datetime.now(timezone.utc) - context.started_at
            total_seconds = int(delta.total_seconds())
        else:
            return "—"

        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"

    def _format_timestamp(self, dt: datetime | None) -> str:
        """Format timestamp for display."""
        if not dt:
            return "—"
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _format_phases(self, context: RunContext) -> str:
        """Format phase progress line."""
        parts = []
        for phase in PHASE_SEQUENCE:
            if phase in context.phase_history:
                parts.append(f"[green]✓ {phase}[/]")
            elif phase == context.current_phase:
                parts.append(f"[yellow]► {phase}[/]")
            else:
                parts.append(f"[dim]· {phase}[/]")
        return " → ".join(parts)

    def _count_artifacts(self, context: RunContext) -> int:
        """Count total artifacts across all phases."""
        # This would use ArtifactManager in actual implementation
        return len(context.phase_history) * 2  # Placeholder
```

**JSON Output:**
```python
import json
from datetime import datetime

def output_json(context: RunContext) -> None:
    """Output run status as JSON."""
    # Calculate additional fields
    duration_ms = 0
    if context.completed_at and context.started_at:
        duration_ms = int(
            (context.completed_at - context.started_at).total_seconds() * 1000
        )

    data = {
        "run_id": context.run_id,
        "feature_description": context.feature_description,
        "status": context.status,
        "current_phase": context.current_phase,
        "completed_phases": context.phase_history,
        "started_at": context.started_at.isoformat() if context.started_at else None,
        "completed_at": context.completed_at.isoformat() if context.completed_at else None,
        "duration_ms": duration_ms,
        "tokens_used": sum(context.phase_tokens.values()),
        "phase_tokens": context.phase_tokens,
    }

    console.print_json(data=data)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   ├── status.py            # NEW - status command
│   └── status_display.py    # NEW - StatusDisplay class
tests/
├── unit/
│   └── cli/
│       ├── test_status.py   # NEW
│       └── test_status_display.py  # NEW
└── integration/
    └── cli/
        └── test_status_integration.py  # NEW
```

**Files to modify:**
```
src/adw/
├── cli/
│   ├── __init__.py          # MODIFY - export status command
│   └── app.py               # MODIFY - register status command
```

### Testing Requirements

**Test Framework:** pytest

**Test status with valid run_id:**
```python
def test_status_shows_run_details(tmp_path):
    """Test that status displays all run details."""
    context = create_test_run(
        tmp_path,
        status="completed",
        phase_history=["plan", "build", "verify"],
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    display = StatusDisplay(console)
    display.show_status(context)

    output_text = output.getvalue()
    assert context.run_id in output_text
    assert "completed" in output_text.lower()
```

**Test failed run shows resume hint:**
```python
def test_status_failed_shows_resume(tmp_path):
    """Test that failed status shows resume command (UX-3)."""
    context = create_test_run(
        tmp_path,
        status="failed",
        current_phase="build",
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True)
    display = StatusDisplay(console)
    display.show_status(context)

    output_text = output.getvalue()
    assert "adw resume" in output_text
    assert context.run_id in output_text
```

**Test JSON output:**
```python
def test_status_json_output(tmp_path):
    """Test JSON output format."""
    context = create_test_run(tmp_path, status="completed")

    runner = CliRunner()
    result = runner.invoke(app, ["status", context.run_id, "--json"])

    data = json.loads(result.output)
    assert data["run_id"] == context.run_id
    assert data["status"] == "completed"
    assert "duration_ms" in data
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Story 6.1 and 6.2:**
- RunLookup class for finding runs
- ContextManager loads RunContext
- CLI command patterns established
- Error handling with Rich Panel

**Key patterns:**
- Optional run_id defaults to most recent
- Use Rich Table for structured display
- Color coding for status
- JSON output for automation

---

## Git Intelligence

**Existing patterns:**
- Status command pattern from other CLI tools
- Rich Table used in ProgressDisplay for summary
- Console.print_json() for JSON output

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **CLI Output**: Use Rich Table for structured data
2. **Color Coding**: Green=success, Red=error, Yellow=warning
3. **JSON Output**: Use console.print_json() for machine-readable
4. **Error Messages**: Include actionable suggestions

---

## Dev Notes

### Key Implementation Points

1. **Status Table Format**:
   ```
   ╭───────────────── Run Status ─────────────────╮
   │ Run ID     01HQXK5P3Z7V8R2M4N6T9W1Y3C       │
   │ Feature    Add user authentication          │
   │ Status     completed                        │
   │ Phase      document                         │
   │ Started    2026-01-03 10:30:45 UTC          │
   │ Completed  2026-01-03 10:35:12 UTC          │
   │ Duration   4m 27s                           │
   ╰──────────────────────────────────────────────╯
   ```

2. **Failed Run Display (UX-3)**:
   ```
   ╭───────────────── Recovery ───────────────────╮
   │ Phase Failed: build                          │
   │                                              │
   │ To resume this run:                          │
   │   adw resume 01HQXK5P3Z7V8R2M4N6T9W1Y3C     │
   ╰──────────────────────────────────────────────╯
   ```

3. **Verbose Output**:
   - Phase progress line: ✓ plan → ✓ build → ► verify → · validate → · document
   - Token usage summary
   - Artifact counts per phase

### Project Structure Notes

- StatusDisplay is separate from command logic
- Reuses RunLookup from Story 6.2
- JSON output for scripting/automation

### References

- [Source: _bmad-output/prd.md#UX-3] - Failed status details
- [Source: _bmad-output/architecture.md#CLI-Output-Format]

---

## Dev Agent Record

### Context Reference

Story 6.3 implements the status command for inspecting run state and outcome.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 6.1 (runs must exist), Story 6.2 (RunLookup class)
- **Blocks:** None
- **Can Parallel With:** Story 6.4 (list), Story 6.5 (abort), Story 6.6 (init)

### Dependency Rationale
- Story 6.1: Status needs runs to display
- Story 6.2: Reuses RunLookup for finding runs

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-03 | BMAD Create-Epic | Initial story creation with comprehensive context |
