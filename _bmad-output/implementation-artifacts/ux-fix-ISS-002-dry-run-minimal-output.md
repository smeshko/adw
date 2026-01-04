# Story UX-FIX-ISS-002: Implement Complete Dry-Run Execution Preview

Status: in-progress
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-04

---

## Story

As a **developer using ADW**,
I want **the `--dry-run` flag to display a complete preview of what would happen during execution**,
so that **I can verify my configuration and phase selection before committing to an actual run**.

## Acceptance Criteria

- [ ] **AC1:** When `--dry-run` is specified, display ALL phases that would execute (full pipeline or single `--phase`)
- [ ] **AC2:** For each phase, show pre-hook and post-hook commands if configured
- [ ] **AC3:** Display relevant project configuration (language, test_command, build_command, platform)
- [ ] **AC4:** When `--from-run` is specified, show which artifacts would be loaded from the source run
- [ ] **AC5:** Use Rich formatting consistent with existing CLI output patterns (panels, tables, styled text)
- [ ] **AC6:** Return exit code 0 after displaying preview (no error state)
- [ ] **AC7:** No actual phase execution or state modification occurs

## Tasks / Subtasks

### Task 1: Create Dry-Run Display Module
- [x] Create `src/adw/cli/dry_run.py` with `DryRunDisplay` class
- [x] Implement `show_execution_preview()` method
- [x] Use Rich panels and tables for structured output

### Task 2: Implement Phase Preview Display
- [x] Show phases in execution order (PHASE_SEQUENCE or single phase)
- [x] For each phase, display:
  - Phase name (with status: "would execute")
  - Pre-hook command (if configured in project.yaml)
  - Post-hook command (if configured in project.yaml)
- [x] Use Rich Table for clean alignment

### Task 3: Implement Configuration Display
- [ ] Load project config via ConfigLoader
- [ ] Display relevant settings:
  - Project name
  - Language
  - Framework (if set)
  - Platform
  - Test command (if set)
  - Build command (if set)
  - LLM path and timeout
  - Git integration settings (if enabled)
- [ ] Handle case when no .adw/project.yaml exists (show defaults)

### Task 4: Implement Artifact Preview (--from-run)
- [ ] When `--from-run` is specified:
  - Load source run's context
  - List artifacts that would be passed to target phase
  - Show artifact names and sizes
- [ ] Validate source run exists before displaying
- [ ] Show clear message if no artifacts found

### Task 5: Integrate into run Command
- [ ] Modify `src/adw/cli/app.py:run()` command
- [ ] Replace minimal dry-run block (lines 186-188) with `DryRunDisplay` call
- [ ] Pass all relevant parameters: phase, from_run, feature, config

### Task 6: Add Unit Tests
- [ ] Test `DryRunDisplay.show_execution_preview()` output
- [ ] Test phase sequence display (full vs single phase)
- [ ] Test config display with various configurations
- [ ] Test artifact display with --from-run
- [ ] Test edge cases (no config, missing source run)

---

## Relevant Feature Documentation

N/A - No conditional docs matched.

---

## Developer Context

### Technical Requirements

1. **No execution occurs** - dry-run MUST NOT create runs, modify state, or execute hooks
2. **Read-only operations only** - ConfigLoader, ArtifactManager reads are allowed
3. **Rich Console output** - All output through Rich (no print())
4. **Error handling** - Gracefully handle missing config/runs with user-friendly messages

### Architecture Compliance

From `project-context.md`:

```python
# CLI Layer: Parse input, format output, delegate to core
# No business logic in CLI - DryRunDisplay is a presentation layer component

# Rich for ALL CLI output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
console = Console()

# Exception handling pattern
try:
    config = ConfigLoader().load()
except ConfigError as e:
    console.print(f"[red]Error:[/] {e.message}")
    if e.suggestion:
        console.print(f"[dim]Suggestion:[/] {e.suggestion}")
    raise typer.Exit(1) from None
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Typer | 0.21.0 | CLI command handling |
| Rich | 14.1.0 | Console output, Panel, Table |
| Pydantic | 2.12+ | Config model access |

Key Rich components to use:
- `Panel` - For section headers ("Execution Preview", "Configuration")
- `Table` - For phase/hook listing and config display
- `console.print()` - Styled text output
- `[green]✓[/]`, `[yellow]●[/]` - Status indicators

### File Structure Requirements

```
src/adw/cli/
├── app.py              # Modify: integrate DryRunDisplay
├── dry_run.py          # NEW: DryRunDisplay class
└── ...

tests/unit/cli/
├── test_dry_run.py     # NEW: DryRunDisplay tests
└── ...
```

### Testing Requirements

```python
# Test file: tests/unit/cli/test_dry_run.py

# Use StringIO to capture console output
from io import StringIO
from rich.console import Console

def test_show_execution_preview_full_pipeline():
    """Test full pipeline preview shows all 5 phases."""
    output = StringIO()
    console = Console(file=output, force_terminal=True)
    display = DryRunDisplay(console)

    display.show_execution_preview(
        feature="Add user auth",
        phase=None,  # Full pipeline
        from_run=None,
    )

    result = output.getvalue()
    for phase in ["plan", "build", "verify", "validate", "document"]:
        assert phase in result

def test_show_execution_preview_single_phase():
    """Test single phase mode only shows specified phase."""
    # ... similar pattern

def test_artifact_preview_with_from_run(tmp_path):
    """Test artifact display when --from-run specified."""
    # Create mock run with artifacts
    # Verify artifact names appear in output
```

Coverage requirement: >80% for new dry_run.py module

---

## Previous Story Intelligence

### From ISS-001 (LLM Output Too Verbose)

The previous UX fix (ISS-001) established the pattern for UX improvements:
- Added `--show-llm-output` flag to control verbosity
- Integrated with Verbosity enum (TRACE level auto-enables)
- Modified `create_orchestrator()` with new parameter
- Pattern: CLI flags → bootstrap → component configuration

### From Story 6-1 (Start New Run)

The `run` command implementation shows:
- RunDisplay pattern for structured CLI output
- How to get run_id before execution (ULID generation)
- Validation patterns for feature description

---

## Git Intelligence

Recent commit patterns from Epic 9:
```
a881abd docs(story-9-2): mark story ready for review
ce6387b test(story-9-2): add integration tests for git commit functionality
496f2c2 feat(story-9-2): add bundled post-hook for git auto-commit
```

Commit message pattern: `type(scope): description`
- type: feat, fix, test, docs
- scope: story ID or component name

For this story, use:
- `feat(ux-fix-002): implement complete dry-run execution preview`
- `test(ux-fix-002): add dry-run display tests`

---

## Latest Technical Information

### Rich Library (14.1.0)

Key components for this implementation:

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Panel for sections
panel = Panel(
    content,
    title="[bold]Execution Preview[/]",
    border_style="blue",
)

# Table for structured data
table = Table(title="Phases")
table.add_column("Phase", style="cyan")
table.add_column("Pre-Hook", style="dim")
table.add_column("Post-Hook", style="dim")
table.add_row("plan", "—", "—")
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All CLI output through Rich console
- Exception hierarchy for errors (ConfigError for config issues)
- Type annotations required on all functions
- Models in src/adw/models/ only
- PEP 8 naming: snake_case for functions/variables, PascalCase for classes

---

## Dev Notes

### Implementation Approach

1. **Create DryRunDisplay class** - Mirrors `RunDisplay` and `ProgressDisplay` patterns
2. **Load config early** - Use `ConfigLoader` to get project settings
3. **Build preview data** - Collect phases, hooks, config into structured format
4. **Render with Rich** - Use Panel/Table for clean output
5. **Handle edge cases** - Missing config (use defaults), missing source run (error message)

### Output Format Specification

```
╭─ Dry Run Preview ────────────────────────────────────────────╮
│ Feature: Add user authentication                             │
│ Run ID:  01HQXK5P3Z7V8R2M4N6T9W1Y3C (would be generated)    │
╰──────────────────────────────────────────────────────────────╯

Phases to Execute:
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Phase      ┃ Pre-Hook             ┃ Post-Hook            ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ plan       │ —                    │ —                    │
│ build      │ npm install          │ npm run lint         │
│ verify     │ —                    │ —                    │
│ validate   │ —                    │ pytest               │
│ document   │ —                    │ —                    │
└────────────┴──────────────────────┴──────────────────────┘

Project Configuration:
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting           ┃ Value                                  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Name              │ adw-sdk                                │
│ Language          │ python                                 │
│ Platform          │ cli                                    │
│ Test Command      │ pytest                                 │
│ LLM Path          │ claude                                 │
│ LLM Timeout       │ 300s                                   │
│ Git Integration   │ disabled                               │
└───────────────────┴────────────────────────────────────────┘

[yellow]Dry run mode - no execution will occur[/]
```

### Source Tree Components

Files to modify:
- `src/adw/cli/app.py` - Lines 186-188 (replace minimal dry-run)
- `src/adw/cli/dry_run.py` - NEW file

Files to read (no modify):
- `src/adw/config/loader.py` - ConfigLoader
- `src/adw/core/constants.py` - PHASE_SEQUENCE
- `src/adw/core/artifact_manager.py` - For --from-run artifacts

### Project Structure Notes

- Aligns with CLI layer separation (presentation only, no business logic)
- Follows existing display patterns (RunDisplay, ProgressDisplay)
- No new models needed - uses existing ProjectConfig, PhaseConfig

### References

- [Source: src/adw/cli/app.py:186-188] - Current minimal dry-run implementation
- [Source: src/adw/models/config.py] - ProjectConfig, PhaseConfig models
- [Source: src/adw/core/constants.py] - PHASE_SEQUENCE definition
- [Source: _bmad-output/project-context.md] - Implementation rules
- [Source: issues/ISS-002-dry-run-minimal-output.md] - Original issue report

---

## Dev Agent Record

### Context Reference

N/A - Story created from issue ISS-002

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Story created from UX issue ISS-002
- Comprehensive implementation guidance provided
- Output format specification included for developer clarity

### File List

Files to create:
- `src/adw/cli/dry_run.py`
- `tests/unit/cli/test_dry_run.py`

Files to modify:
- `src/adw/cli/app.py` (lines 186-188)
