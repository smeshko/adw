# Story 6.1: Start New Run with Feature Description

Status: dev-complete
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-03

---

## Story

As a user,
I want to start a new run by providing a feature description,
So that I can begin AI-assisted development.

## Acceptance Criteria

**Given** command `adw run "Add user authentication"`
**When** executed
**Then** a new run is created with ULID run_id
**And** the run header panel displays run ID, feature, started timestamp (UX-12)

**Given** a new run starts
**When** project config exists at `.adw/project.yaml`
**Then** configuration is loaded and validated (NFR9)

**Given** no project config exists
**When** run is started
**Then** default configuration is used for common project types (NFR19)

**Given** the feature description
**When** it contains special characters
**Then** they are properly escaped in templates

**Given** CLI startup
**When** I measure time to first output
**Then** it's under 2 seconds (NFR1)

## Tasks / Subtasks

### Task 1: Implement CLI Run Command
- [x] Modify `src/adw/cli/app.py` to accept feature description argument
- [x] Add `FEATURE_DESCRIPTION` positional argument to `run` command
- [x] Add `--verbose/-v` flag for debug output
- [x] Add `--dry-run` flag to show what would happen without executing
- [x] Validate feature description is not empty

### Task 2: Create Run Header Display
- [x] Create `src/adw/cli/run_display.py` with `RunDisplay` class
- [x] Implement `show_run_header()` method using Rich Panel
- [x] Display: run_id, feature description (truncated), started timestamp
- [x] Use UX-12 specification for header format
- [x] Integrate with ProgressDisplay from Story 5.5

### Task 3: Load and Validate Project Configuration
- [x] Create `src/adw/config/loader.py` with `ConfigLoader` class
- [x] Implement three-tier config resolution (project → user → defaults)
- [x] Check for `.adw/project.yaml` in current directory
- [x] If missing, use defaults from package bundled config
- [x] Validate config against Pydantic schema
- [x] Handle invalid config gracefully with `ConfigError`

### Task 4: Detect Project Type for Defaults
- [x] Create `src/adw/config/detector.py` with `ProjectTypeDetector` class
- [x] Detect Python projects via `pyproject.toml`
- [x] Detect Node.js projects via `package.json`
- [x] Detect Go projects via `go.mod`
- [x] Set appropriate defaults (language, test_command) based on detection
- [x] Return "generic" if no known project type detected

### Task 5: Escape Special Characters in Feature Description
- [x] Update template engine in `src/adw/commands/template.py`
- [x] Escape quotes, backslashes, and shell metacharacters
- [x] Ensure feature description is safe for template substitution
- [x] Add tests for various special character scenarios

### Task 6: Integrate Run Command with Orchestrator
- [x] Wire CLI `run` command to `Orchestrator.run()`
- [x] Create all required managers (ContextManager, SnapshotManager, etc.)
- [x] Initialize ProgressDisplay and pass to Orchestrator
- [x] Handle and display errors using Rich formatting
- [x] Ensure startup time is under 2 seconds (NFR1)

### Task 7: Create ProjectConfig Model
- [x] Create `src/adw/models/project_config.py` with `ProjectConfig` class
  - Note: Already exists in `src/adw/models/config.py` from previous story
- [x] Define fields: language, test_command, build_command, phases, llm, hooks
- [x] Add validation rules using Pydantic v2 validators
- [x] Add `from_yaml()` class method for loading from file
- [x] Add sensible defaults for all optional fields

### Task 8: Write Unit Tests
- [x] Create `tests/unit/cli/test_run.py`
- [x] Test feature description argument parsing
- [x] Test verbose and dry-run flags
- [x] Test empty feature description validation
- [x] Create `tests/unit/config/test_loader.py`
- [x] Test config loading from project path
- [x] Test fallback to defaults when no config
- [x] Test config validation errors
- [x] Target: >80% coverage

### Task 9: Write Integration Tests
- [x] Create `tests/integration/cli/test_run_integration.py`
- [x] Test full run command execution with MockExecutor
- [x] Test with project config present
- [x] Test without project config (using defaults)
- [x] Test special character handling in feature description
- [x] Measure startup time to verify NFR1

---

## Developer Context

### Technical Requirements

- **Typer CLI**: Use for command-line argument parsing
- **Rich Console**: Use for all formatted output (UX-12 header)
- **ULID Generation**: Run IDs must be ULIDs for sortability
- **Configuration Loading**: Three-tier hierarchy (project → user → bundled)
- **Performance**: CLI startup under 2 seconds (NFR1)

### Architecture Compliance

**From architecture.md - CLI Structure:**
```
src/adw/
├── cli/                    # Typer CLI commands
│   ├── __init__.py
│   ├── app.py              # Main Typer app, error handling
│   ├── run.py              # `adw run`, `adw resume`, `adw retry`
│   └── progress.py         # Progress display (Story 5.5)
├── core/                   # Orchestration logic
│   └── orchestrator.py     # Main run orchestrator
```

**From architecture.md - CLI Command Patterns:**
```python
# Commands: kebab-case
# adw run, adw list-runs, adw logs show

# Options: double-dash + kebab-case
# --run-id, --from-phase, --verbose

# Short options: single letter
# -v, -q, -f

# Arguments: SCREAMING_CASE in help
# adw run FEATURE_REQUEST
```

**From architecture.md - Config Hierarchy:**
```
Resolution Order (highest priority first):
1. `.adw/config.yaml` (project-specific)
2. `~/.config/adw/config.yaml` (user preferences)
3. Bundled defaults in package
```

### Library & Framework Requirements

**Typer CLI Implementation:**
```python
import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

from adw.core.orchestrator import Orchestrator
from adw.config.loader import ConfigLoader
from adw.cli.progress import ProgressDisplay

console = Console()
app = typer.Typer()

@app.command()
def run(
    feature_description: str = typer.Argument(
        ...,
        help="Description of the feature to implement",
        metavar="FEATURE_DESCRIPTION",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would happen without executing",
    ),
) -> None:
    """Start a new ADW run with the given feature description.

    Example:
        adw run "Add user authentication"
    """
    if not feature_description.strip():
        console.print("[red]Error:[/] Feature description cannot be empty")
        raise typer.Exit(code=1)

    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load()

    # Show run header
    run_display = RunDisplay(console)
    run_display.show_run_header(
        feature=feature_description,
        config=config,
    )

    if dry_run:
        console.print("[yellow]Dry run mode - no execution[/]")
        return

    # Create and run orchestrator
    try:
        orchestrator = create_orchestrator(config, verbose)
        context = orchestrator.run(feature_description)
        console.print(f"[green]Run completed:[/] {context.run_id}")
    except ADWError as e:
        console.print(Panel(
            f"[red]Error:[/] {e.message}\n\n"
            f"[dim]Suggestion:[/] {e.suggestion}",
            title=f"[red]{e.code}[/]",
            border_style="red",
        ))
        raise typer.Exit(code=1)
```

**Run Header Display (UX-12):**
```python
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from ulid import ULID

class RunDisplay:
    """Display run information using Rich."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def show_run_header(
        self,
        run_id: str,
        feature: str,
        started_at: datetime,
    ) -> None:
        """Display the run header panel.

        UX-12: Run header panel displays run ID, feature, started timestamp.

        Args:
            run_id: The ULID run identifier.
            feature: Feature description (will be truncated if long).
            started_at: When the run started.
        """
        # Truncate long feature descriptions
        max_len = 60
        feature_display = (
            f"{feature[:max_len]}..." if len(feature) > max_len else feature
        )

        timestamp = started_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]Run ID:[/] {run_id}\n"
                f"[bold]Feature:[/] {feature_display}\n"
                f"[dim]Started:[/] {timestamp}",
                title="[bold blue]ADW Run[/]",
                border_style="blue",
            )
        )
        self.console.print()
```

**Project Type Detection:**
```python
from pathlib import Path
from typing import Literal

ProjectType = Literal["python", "nodejs", "go", "generic"]

class ProjectTypeDetector:
    """Detect project type from filesystem markers."""

    MARKERS = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt"],
        "nodejs": ["package.json"],
        "go": ["go.mod"],
    }

    DEFAULTS = {
        "python": {"language": "python", "test_command": "pytest"},
        "nodejs": {"language": "javascript", "test_command": "npm test"},
        "go": {"language": "go", "test_command": "go test ./..."},
        "generic": {"language": "unknown", "test_command": None},
    }

    def detect(self, project_root: Path) -> ProjectType:
        """Detect project type from directory.

        Args:
            project_root: Path to project root directory.

        Returns:
            Detected project type.
        """
        for project_type, markers in self.MARKERS.items():
            for marker in markers:
                if (project_root / marker).exists():
                    return project_type
        return "generic"

    def get_defaults(self, project_type: ProjectType) -> dict:
        """Get default config values for project type."""
        return self.DEFAULTS.get(project_type, self.DEFAULTS["generic"])
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   └── run_display.py       # NEW - RunDisplay class
├── config/                   # NEW package
│   ├── __init__.py
│   ├── loader.py            # ConfigLoader class
│   └── detector.py          # ProjectTypeDetector class
├── models/
│   └── project_config.py    # NEW - ProjectConfig model
tests/
├── unit/
│   ├── cli/
│   │   └── test_run.py      # NEW
│   └── config/
│       ├── __init__.py      # NEW
│       ├── test_loader.py   # NEW
│       └── test_detector.py # NEW
└── integration/
    └── cli/
        └── test_run_integration.py  # NEW
```

**Files to modify:**
```
src/adw/
├── cli/
│   ├── __init__.py          # MODIFY - export RunDisplay
│   └── app.py               # MODIFY - implement run command
├── commands/
│   └── template.py          # MODIFY - add special char escaping
├── models/
│   └── __init__.py          # MODIFY - export ProjectConfig
```

### Testing Requirements

**Test Framework:** pytest

**Test run command argument parsing:**
```python
from typer.testing import CliRunner
from adw.cli.app import app

runner = CliRunner()

def test_run_requires_feature_description():
    """Test that run command requires feature description."""
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output

def test_run_accepts_feature_description():
    """Test that run command accepts feature description."""
    result = runner.invoke(app, ["run", "Add user auth", "--dry-run"])
    assert result.exit_code == 0
    assert "Add user auth" in result.output

def test_run_rejects_empty_description():
    """Test that empty feature description is rejected."""
    result = runner.invoke(app, ["run", "   ", "--dry-run"])
    assert result.exit_code == 1
    assert "empty" in result.output.lower()
```

**Test config loading:**
```python
import pytest
from pathlib import Path
from adw.config.loader import ConfigLoader

def test_load_from_project_config(tmp_path):
    """Test loading config from .adw/project.yaml."""
    config_dir = tmp_path / ".adw"
    config_dir.mkdir()
    config_file = config_dir / "project.yaml"
    config_file.write_text("""
language: python
test_command: pytest --cov
    """)

    loader = ConfigLoader(project_root=tmp_path)
    config = loader.load()

    assert config.language == "python"
    assert config.test_command == "pytest --cov"

def test_fallback_to_defaults_when_no_config(tmp_path):
    """Test fallback to defaults when no config exists."""
    # Create pyproject.toml to trigger Python detection
    (tmp_path / "pyproject.toml").touch()

    loader = ConfigLoader(project_root=tmp_path)
    config = loader.load()

    assert config.language == "python"
    assert config.test_command == "pytest"
```

**Test special character escaping:**
```python
from adw.commands.template import escape_feature_description

def test_escapes_quotes():
    """Test that quotes are escaped in feature description."""
    result = escape_feature_description('Add "quoted" text')
    assert '\\"' in result or "'" not in result

def test_escapes_shell_metacharacters():
    """Test that shell metacharacters are escaped."""
    result = escape_feature_description("Add $VAR and `cmd`")
    assert "$" not in result or "\\$" in result
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Epic 5 Stories:**
- Orchestrator is fully implemented with phase sequencing
- ProgressDisplay handles all phase progress output
- ContextManager handles state persistence
- PhaseRunner executes individual phases
- InterruptionHandler manages Ctrl+C gracefully

**Key learnings:**
- Use dependency injection for testability
- Rich Console must be passed to constructors
- Progress callbacks enable real-time updates
- Orchestrator.run() is the main entry point

**Existing components to reuse:**
- `Orchestrator` from `src/adw/core/orchestrator.py`
- `ProgressDisplay` from `src/adw/cli/progress.py`
- `ContextManager` from `src/adw/core/context_manager.py`
- `SnapshotManager` from `src/adw/core/snapshot_manager.py`
- `ArtifactManager` from `src/adw/core/artifact_manager.py`

---

## Git Intelligence

**Recent commits:**
- feat(story-5-3): Pass Artifacts Between Phases
- feat(story-5-5): Display Phase Progress with Rich Console Output
- feat(story-5-2): Implement PhaseRunner for Single Phase Execution
- feat(story-5-1): Implement Phase Sequence and Transitions

**Patterns observed:**
- Commit format: `feat(story-X-Y): Description`
- Tests always included with implementation
- Progress display uses Rich extensively
- Orchestrator accepts optional progress_display parameter

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **CLI Output**: Use Rich for all formatted output
2. **Naming**: PEP 8 strict (snake_case functions, PascalCase classes)
3. **Type Hints**: Full annotations required on all public functions
4. **Exceptions**: Use ADWError hierarchy, never bare Exception
5. **Models**: All Pydantic models in src/adw/models/
6. **Testing**: Pytest, >80% coverage requirement

---

## Dev Notes

### Key Implementation Points

1. **CLI Startup Performance (NFR1)**:
   - Lazy imports to minimize startup time
   - Defer heavy imports until needed
   - Target: first output in <2 seconds

2. **Configuration Resolution**:
   ```python
   # Priority: project > user > bundled
   config = (
       load_project_config() or
       load_user_config() or
       get_bundled_defaults()
   )
   ```

3. **Run Header Format (UX-12)**:
   ```
   ╭───────────────── ADW Run ──────────────────╮
   │ Run ID: 01HQXK5P3Z7V8R2M4N6T9W1Y3C        │
   │ Feature: Add user authentication           │
   │ Started: 2026-01-03 10:30:45 UTC           │
   ╰────────────────────────────────────────────╯
   ```

4. **Special Character Handling**:
   ```python
   def escape_feature_description(desc: str) -> str:
       """Escape special characters for template safety."""
       # Escape backslashes first, then quotes
       result = desc.replace("\\", "\\\\")
       result = result.replace('"', '\\"')
       result = result.replace("$", "\\$")
       result = result.replace("`", "\\`")
       return result
   ```

### Project Structure Notes

- New `config/` package for configuration loading
- CLI command wires together all core components
- Follows existing patterns from Epic 5 stories
- Uses established dependency injection patterns

### References

- [Source: _bmad-output/architecture.md#CLI-Command-Patterns]
- [Source: _bmad-output/architecture.md#Config-Hierarchy]
- [Source: _bmad-output/prd.md#NFR1] - CLI startup <2 seconds
- [Source: _bmad-output/prd.md#NFR9] - Config validation
- [Source: _bmad-output/prd.md#NFR19] - Sensible defaults
- [Source: _bmad-output/prd.md#UX-12] - Run header panel

---

## Dev Agent Record

### Context Reference

Story 6.1 implements the main CLI entry point for starting new ADW runs, connecting the user interface to the orchestration engine.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 5.1 (Orchestrator), Story 5.2 (PhaseRunner), Story 5.5 (ProgressDisplay)
- **Blocks:** Story 6.2 (Resume requires runs to exist), Story 6.3 (Status requires runs), Story 6.4 (List requires runs)
- **Can Parallel With:** Story 6.6 (Initialize Project - independent feature)

### Dependency Rationale
- Story 5.1: Orchestrator is the core engine this command calls
- Story 5.2: PhaseRunner executes individual phases
- Story 5.5: ProgressDisplay shows execution progress
- Story 6.2-6.4: All require runs to exist first

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-03 | BMAD Create-Epic | Initial story creation with comprehensive context |
