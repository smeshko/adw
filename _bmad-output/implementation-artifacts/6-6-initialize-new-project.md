# Story 6.6: Initialize New Project

Status: ready-for-dev
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-03

---

## Story

As a user,
I want to initialize a project with default configuration,
So that I can start using adw in my repository.

## Acceptance Criteria

**Given** command `adw init` in a directory
**When** `.adw/` doesn't exist
**Then** it creates `.adw/` with `project.yaml` containing defaults

**Given** the project appears to be Python
**When** init detects `pyproject.toml`
**Then** defaults are set appropriately (language: python, test_command: pytest)

**Given** the project appears to be Node.js
**When** init detects `package.json`
**Then** defaults are set appropriately (language: javascript, test_command: npm test)

**Given** `.adw/` already exists
**When** init is run
**Then** ConfigError is raised with "Project already initialized"

**Given** command `adw init --force`
**When** `.adw/` exists
**Then** configuration is regenerated with fresh defaults

## Tasks / Subtasks

### Task 1: Implement CLI Init Command
- [x] Create `src/adw/cli/init.py` with init command
- [x] Add `--force/-f` flag to overwrite existing config
- [x] Add `--language` option to override detection
- [x] Add `--template` option for future template support
- [x] Register command in main app

### Task 2: Create Project Initialization Logic
- [x] Create `src/adw/config/initializer.py` with `ProjectInitializer` class
- [x] Implement `initialize()` method
- [x] Create `.adw/` directory structure
- [x] Generate `project.yaml` with detected/default settings
- [x] Create `.gitignore` for `.adw/runs/` directory

### Task 3: Implement Project Type Detection
- [x] Use `ProjectTypeDetector` from Story 6.1
- [x] Detect Python via `pyproject.toml`, `setup.py`, `requirements.txt`
- [x] Detect Node.js via `package.json`
- [x] Detect Go via `go.mod`
- [x] Detect Rust via `Cargo.toml`
- [x] Set appropriate defaults for each type

### Task 4: Generate Project Configuration
- [x] Create `project.yaml` with detected settings
- [x] Include: language, test_command, build_command
- [x] Include: default phases configuration
- [x] Include: LLM configuration (claude_code path)
- [x] Add helpful comments explaining each setting

### Task 5: Create Directory Structure
- [ ] Create `.adw/` directory
- [ ] Create `.adw/runs/` for run storage
- [ ] Create `.adw/commands/` for custom phase commands (empty)
- [ ] Create `.gitignore` to exclude run data

### Task 6: Handle Existing Configuration
- [ ] Check if `.adw/` exists before init
- [ ] Raise ConfigError if exists and no --force
- [ ] With --force: backup existing config, regenerate
- [ ] Display warning when overwriting

### Task 7: Display Initialization Summary
- [ ] Show detected project type
- [ ] Show generated configuration summary
- [ ] Show next steps (how to run first workflow)
- [ ] Use Rich Panel for formatted output

### Task 8: Write Unit Tests
- [ ] Create `tests/unit/cli/test_init.py`
- [ ] Test init in empty directory
- [ ] Test init with Python project
- [ ] Test init with Node.js project
- [ ] Test init with existing .adw/ fails
- [ ] Test init --force overwrites
- [ ] Test generated config is valid YAML
- [ ] Target: >80% coverage

### Task 9: Write Integration Tests
- [ ] Create `tests/integration/cli/test_init_integration.py`
- [ ] Test full init flow
- [ ] Test run command works after init
- [ ] Verify directory structure created

---

## Developer Context

### Technical Requirements

- **Directory Creation**: Create `.adw/` with subdirectories
- **Project Detection**: Auto-detect project type from markers
- **Config Generation**: Generate valid YAML configuration
- **Gitignore**: Exclude run data from version control
- **Force Mode**: Allow reinitializing with --force

### Architecture Compliance

**From architecture.md - Project Structure:**
```
.adw/
├── project.yaml              # Project-specific config
├── commands/                 # Project command overrides
│   └── <phase>/
└── runs/
    └── <run_id>/
        ├── context.json
        └── ...
```

**From architecture.md - Config Hierarchy:**
```
Resolution Order (highest priority first):
1. `.adw/project.yaml` (project-specific)
2. `~/.config/adw/config.yaml` (user preferences)
3. Bundled defaults in package
```

### Library & Framework Requirements

**Init Command Implementation:**
```python
import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

from adw.config.initializer import ProjectInitializer
from adw.config.detector import ProjectTypeDetector
from adw.exceptions import ConfigError

console = Console()

@app.command()
def init(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing configuration",
    ),
    language: str | None = typer.Option(
        None,
        "--language", "-l",
        help="Override detected language (python, javascript, go, etc.)",
    ),
) -> None:
    """Initialize ADW in the current directory.

    Creates .adw/ directory with project configuration.
    Auto-detects project type and sets appropriate defaults.

    Examples:
        adw init                    # Auto-detect and initialize
        adw init --force            # Reinitialize existing project
        adw init --language python  # Override detection
    """
    project_root = Path.cwd()
    adw_dir = project_root / ".adw"

    # Check if already initialized
    if adw_dir.exists() and not force:
        raise ConfigError(
            code="PROJECT_ALREADY_INITIALIZED",
            message="Project already initialized",
            suggestion="Use 'adw init --force' to reinitialize",
            recoverable=False,
        )

    # Detect project type
    detector = ProjectTypeDetector()
    detected_type = detector.detect(project_root)

    # Override if specified
    project_type = language or detected_type

    # Initialize
    initializer = ProjectInitializer(project_root)
    config = initializer.initialize(
        project_type=project_type,
        force=force,
    )

    # Show summary
    show_init_summary(project_type, config, adw_dir)


def show_init_summary(
    project_type: str,
    config: dict,
    adw_dir: Path,
) -> None:
    """Display initialization summary."""
    console.print()
    console.print(
        Panel(
            f"[bold green]Project initialized![/]\n\n"
            f"[bold]Detected:[/] {project_type}\n"
            f"[bold]Language:[/] {config.get('language', 'unknown')}\n"
            f"[bold]Test Command:[/] {config.get('test_command', 'not set')}\n\n"
            f"[dim]Config:[/] {adw_dir / 'project.yaml'}\n\n"
            f"[bold]Next steps:[/]\n"
            f"  1. Review configuration: {adw_dir / 'project.yaml'}\n"
            f"  2. Start your first run: adw run \"Add feature description\"",
            title="[blue]ADW Init[/]",
            border_style="green",
        )
    )
```

**Project Initializer:**
```python
from pathlib import Path
import yaml

class ProjectInitializer:
    """Initialize ADW project structure."""

    DEFAULT_CONFIG_TEMPLATE = """# ADW Project Configuration
# Generated by: adw init
# Documentation: https://adw.dev/docs/config

# Project language (auto-detected)
language: {language}

# Test command for verify phase
test_command: {test_command}

# Build command (optional)
# build_command: make build

# LLM Configuration
llm:
  claude_code:
    # Path to Claude Code CLI (default: claude in PATH)
    # path: /usr/local/bin/claude
    timeout_seconds: 300

# Phase configuration (uses defaults if not specified)
# phases:
#   plan:
#     timeout: 120
#   build:
#     timeout: 300
#   verify:
#     timeout: 180

# Hook configuration (optional)
# hooks:
#   build:
#     pre: ./scripts/pre-build.sh
#     post: ./scripts/post-build.sh
"""

    GITIGNORE_CONTENT = """# ADW run data (can be large)
runs/

# ADW logs
*.log
"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.adw_dir = project_root / ".adw"

    def initialize(
        self,
        project_type: str,
        force: bool = False,
    ) -> dict:
        """Initialize ADW project.

        Args:
            project_type: Detected or specified project type.
            force: Overwrite existing config.

        Returns:
            Generated configuration dict.
        """
        # Backup existing if force
        if self.adw_dir.exists() and force:
            self._backup_existing()

        # Create directory structure
        self._create_directories()

        # Generate config
        config = self._generate_config(project_type)

        # Write files
        self._write_config(config)
        self._write_gitignore()

        return config

    def _create_directories(self) -> None:
        """Create .adw/ directory structure."""
        self.adw_dir.mkdir(exist_ok=True)
        (self.adw_dir / "runs").mkdir(exist_ok=True)
        (self.adw_dir / "commands").mkdir(exist_ok=True)

    def _generate_config(self, project_type: str) -> dict:
        """Generate configuration based on project type."""
        from adw.config.detector import ProjectTypeDetector

        detector = ProjectTypeDetector()
        defaults = detector.get_defaults(project_type)

        return {
            "language": defaults.get("language", "unknown"),
            "test_command": defaults.get("test_command"),
            "build_command": defaults.get("build_command"),
        }

    def _write_config(self, config: dict) -> None:
        """Write project.yaml configuration file."""
        config_content = self.DEFAULT_CONFIG_TEMPLATE.format(
            language=config.get("language", "unknown"),
            test_command=config.get("test_command") or "# not configured",
        )

        config_path = self.adw_dir / "project.yaml"
        config_path.write_text(config_content)

    def _write_gitignore(self) -> None:
        """Write .gitignore for .adw/ directory."""
        gitignore_path = self.adw_dir / ".gitignore"
        gitignore_path.write_text(self.GITIGNORE_CONTENT)

    def _backup_existing(self) -> None:
        """Backup existing configuration."""
        import shutil
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / f".adw.backup.{timestamp}"
        shutil.move(str(self.adw_dir), str(backup_dir))
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── cli/
│   └── init.py              # NEW - init command
├── config/
│   └── initializer.py       # NEW - ProjectInitializer class
tests/
├── unit/
│   ├── cli/
│   │   └── test_init.py     # NEW
│   └── config/
│       └── test_initializer.py  # NEW
└── integration/
    └── cli/
        └── test_init_integration.py  # NEW
```

**Files to modify:**
```
src/adw/
├── cli/
│   ├── __init__.py          # MODIFY - export init command
│   └── app.py               # MODIFY - register init command
├── config/
│   └── __init__.py          # MODIFY - export ProjectInitializer
```

### Testing Requirements

**Test Framework:** pytest

**Test init in empty directory:**
```python
def test_init_creates_adw_directory(tmp_path):
    """Test that init creates .adw/ directory."""
    initializer = ProjectInitializer(tmp_path)
    initializer.initialize(project_type="generic")

    assert (tmp_path / ".adw").exists()
    assert (tmp_path / ".adw" / "project.yaml").exists()
    assert (tmp_path / ".adw" / "runs").exists()
    assert (tmp_path / ".adw" / "commands").exists()
```

**Test Python project detection:**
```python
def test_init_detects_python_project(tmp_path):
    """Test that init detects Python project."""
    # Create pyproject.toml marker
    (tmp_path / "pyproject.toml").touch()

    initializer = ProjectInitializer(tmp_path)
    detector = ProjectTypeDetector()
    project_type = detector.detect(tmp_path)

    assert project_type == "python"

    config = initializer.initialize(project_type=project_type)
    assert config["language"] == "python"
    assert config["test_command"] == "pytest"
```

**Test existing config fails:**
```python
def test_init_fails_if_exists(tmp_path):
    """Test that init fails if .adw/ exists."""
    # Create existing .adw/
    (tmp_path / ".adw").mkdir()

    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code != 0
    assert "already initialized" in result.output.lower()
```

**Test force overwrites:**
```python
def test_init_force_overwrites(tmp_path):
    """Test that --force overwrites existing config."""
    # Create existing .adw/
    (tmp_path / ".adw").mkdir()
    (tmp_path / ".adw" / "project.yaml").write_text("old: config")

    initializer = ProjectInitializer(tmp_path)
    initializer.initialize(project_type="python", force=True)

    # Verify new config
    config_content = (tmp_path / ".adw" / "project.yaml").read_text()
    assert "language: python" in config_content
```

**Coverage Target:** >80% overall

---

## Previous Story Intelligence

**From Story 6.1:**
- ProjectTypeDetector already created
- Config loading patterns established
- CLI command patterns

**Key patterns:**
- Use Rich Panel for summary output
- Helpful next steps in output
- Force flag for overwrite operations

---

## Git Intelligence

**Existing patterns:**
- Directory creation with mkdir()
- YAML file generation
- Path manipulation with pathlib

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Directory Creation**: Use pathlib for all path operations
2. **YAML Output**: Format with helpful comments
3. **Gitignore**: Exclude large/temporary data
4. **Force Flag**: Allow overwriting with explicit flag

---

## Dev Notes

### Key Implementation Points

1. **Generated project.yaml**:
   ```yaml
   # ADW Project Configuration
   # Generated by: adw init

   language: python
   test_command: pytest

   llm:
     claude_code:
       timeout_seconds: 300
   ```

2. **Directory Structure Created**:
   ```
   .adw/
   ├── project.yaml     # Configuration
   ├── .gitignore       # Exclude runs/
   ├── commands/        # Custom commands (empty)
   └── runs/            # Run storage (empty)
   ```

3. **Project Type Detection**:
   | Marker | Project Type | Defaults |
   |--------|--------------|----------|
   | pyproject.toml | python | pytest |
   | package.json | nodejs | npm test |
   | go.mod | go | go test ./... |
   | Cargo.toml | rust | cargo test |

4. **Init Summary Display**:
   ```
   ╭────────────────── ADW Init ──────────────────╮
   │ Project initialized!                          │
   │                                               │
   │ Detected: python                              │
   │ Language: python                              │
   │ Test Command: pytest                          │
   │                                               │
   │ Config: .adw/project.yaml                     │
   │                                               │
   │ Next steps:                                   │
   │   1. Review configuration: .adw/project.yaml  │
   │   2. Start your first run: adw run "..."      │
   ╰───────────────────────────────────────────────╯
   ```

### Project Structure Notes

- Init is independent of run commands
- Can run in parallel with Story 6.1
- Uses shared ProjectTypeDetector

### References

- [Source: _bmad-output/architecture.md#Project-Structure]
- [Source: _bmad-output/architecture.md#Config-Hierarchy]
- [Source: _bmad-output/prd.md#FR32-FR36] - Project configuration

---

## Dev Agent Record

### Context Reference

Story 6.6 implements project initialization for new ADW users.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** None (independent initialization feature)
- **Blocks:** None
- **Can Parallel With:** Story 6.1 (both are entry points), Story 6.2-6.5

### Dependency Rationale
- Init is independent - users can run it before or after run command
- Story 6.1 uses ConfigLoader which handles missing .adw/

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-03 | BMAD Create-Epic | Initial story creation with comprehensive context |
