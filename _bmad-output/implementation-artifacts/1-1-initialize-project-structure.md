# Story 1.1: Initialize Project Structure with uv and Typer

Status: ready-for-dev
Linear Issue: not-configured
Epic: 1 - Project Scaffolding & Test Infrastructure
Created: 2025-12-31

---

## Story

As a developer,
I want the project scaffolded with uv package manager, proper Python 3.13+ configuration, and Typer CLI entry point,
so that I have a working development environment with the correct tooling from day one.

## Acceptance Criteria

**Given** a fresh clone of the repository
**When** I run `uv sync`
**Then** all dependencies are installed successfully
**And** the package is installed in editable mode

**Given** the project is installed
**When** I run `adw --help`
**Then** the CLI displays help output using Rich formatting
**And** startup time is under 2 seconds (NFR1)

**Given** the project structure
**When** I inspect the layout
**Then** it follows the architecture specification:
  - `src/adw/` contains cli/, core/, models/, exceptions.py, utils/
  - `tests/` contains unit/, integration/ subdirectories
  - `pyproject.toml` specifies Python 3.13+, Typer 0.21.0, Rich 14.1.0, Pydantic 2.12+

## Tasks / Subtasks

### Task 1: Initialize uv Project
- [x] Run `uv init adw --app --python 3.13` to create project skeleton
- [x] Verify `pyproject.toml` is created with correct Python version constraint

### Task 2: Add Core Dependencies
- [x] Run `uv add typer[all] rich pydantic pyyaml filelock python-ulid`
- [x] Verify all dependencies are added to pyproject.toml
- [x] Run `uv add --dev pytest pytest-asyncio pytest-cov ruff mypy`
- [x] Verify dev dependencies are in dev dependency group

### Task 3: Create Directory Structure
- [ ] Create `src/adw/` package directory with `__init__.py`
- [ ] Create `src/adw/__main__.py` for `python -m adw` support
- [ ] Create subdirectories: cli/, core/, models/, commands/, executors/, hooks/, logging/, utils/
- [ ] Create `src/adw/exceptions.py` placeholder
- [ ] Create `tests/` directory with `__init__.py` and `conftest.py`
- [ ] Create `tests/unit/` and `tests/integration/` subdirectories
- [ ] Create `tests/fixtures/` directory for test data
- [ ] Create `defaults/commands/` directory for bundled command templates

### Task 4: Configure pyproject.toml Entry Point
- [ ] Add `[project.scripts]` section with `adw = "adw.cli:app"`
- [ ] Verify entry point configuration is correct

### Task 5: Create Minimal CLI App
- [ ] Create `src/adw/cli/__init__.py` with Typer app export
- [ ] Create `src/adw/cli/app.py` with main Typer app
- [ ] Add a simple `--version` command using Rich console
- [ ] Add placeholder `run` command that prints "Not implemented yet"

### Task 6: Verify Installation
- [ ] Run `uv sync` to install the package
- [ ] Run `adw --help` and verify output
- [ ] Run `adw --version` and verify output
- [ ] Measure startup time (should be <2 seconds)

### Task 7: Add Configuration Files
- [ ] Create `.gitignore` with Python/uv patterns
- [ ] Create basic `README.md` with installation instructions
- [ ] Create `.github/workflows/ci.yml` placeholder for CI

---

## Developer Context

### Technical Requirements

**From Architecture Document (ARCH-1, ARCH-2):**
- Use Typer 0.21.0 with Rich integration for CLI
- Use Rich 14.1.0 for all terminal output
- Use Pydantic 2.12+ for data validation
- Python 3.13+ required for modern type hints and features
- Use uv for package management (NOT pip or poetry)

**Performance Requirement (NFR1):**
- CLI startup time must be under 2 seconds
- Use lazy imports where possible to minimize startup overhead

### Architecture Compliance

**Project Structure (from architecture.md):**
```
adw/
├── pyproject.toml
├── src/
│   └── adw/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli/
│       ├── core/
│       ├── commands/
│       ├── executors/
│       ├── hooks/
│       ├── logging/
│       ├── models/
│       ├── exceptions.py
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── defaults/
│   └── commands/
└── uv.lock
```

**Entry Point Configuration:**
```toml
[project.scripts]
adw = "adw.cli:app"
```

**Package Version:**
```python
# src/adw/__init__.py
__version__ = "0.1.0"
```

### Library & Framework Requirements

| Library | Version | Import Pattern |
|---------|---------|----------------|
| Typer | 0.21.0 | `import typer` |
| Rich | 14.1.0 | `from rich.console import Console` |
| Pydantic | 2.12+ | `from pydantic import BaseModel` |
| PyYAML | 6.0+ | `import yaml` |
| filelock | latest | `import filelock` |
| python-ulid | latest | `from ulid import ULID` |

**Typer App Pattern:**
```python
# src/adw/cli/app.py
import typer
from rich.console import Console

console = Console()
app = typer.Typer(
    name="adw",
    help="Agentic Development Workflow SDK",
    add_completion=True,
)

@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
):
    if version:
        from adw import __version__
        console.print(f"adw version {__version__}")
        raise typer.Exit()
```

### File Structure Requirements

**Required Files to Create:**

1. `pyproject.toml` - Project configuration
2. `src/adw/__init__.py` - Package init with version
3. `src/adw/__main__.py` - python -m support
4. `src/adw/cli/__init__.py` - CLI package init
5. `src/adw/cli/app.py` - Main Typer app
6. `src/adw/exceptions.py` - Exception placeholder
7. `tests/__init__.py` - Test package init
8. `tests/conftest.py` - Shared fixtures
9. `.gitignore` - Git ignore patterns

**Directory Creation Order:**
1. Root directories: src/, tests/, defaults/
2. Package directories: src/adw/
3. Module directories: cli/, core/, models/, etc.
4. Test directories: tests/unit/, tests/integration/, tests/fixtures/
5. Default commands: defaults/commands/

### Testing Requirements

**For This Story:**
- No unit tests required yet (this is infrastructure setup)
- Verify installation works via manual testing
- Verify `adw --help` produces expected output
- Measure startup time

**Test Infrastructure Created:**
```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures (placeholder)
├── unit/
│   └── __init__.py
├── integration/
│   └── __init__.py
└── fixtures/
    └── (empty for now)
```

---

## Previous Story Intelligence

This is the first story in Epic 1. No previous story learnings available.

**Epic Context:**
- Epic 1 establishes project foundation
- All subsequent stories depend on this infrastructure
- Stories 1.2-1.5 will build on this structure

---

## Git Intelligence

No prior commits yet - this is the initial project setup.

**Recommended Commit Pattern:**
```
feat(init): scaffold project with uv and Typer

- Initialize uv project with Python 3.13+
- Add core dependencies (Typer, Rich, Pydantic)
- Create src/adw/ package structure
- Add minimal CLI with --version and --help
- Set up tests/ directory structure
```

---

## Latest Technical Information

**Typer 0.21.0 (current stable):**
- Full Rich integration for help formatting
- Decorator-based command definition
- Automatic shell completion
- Type hint-based argument parsing

**Rich 14.1.0 (current stable):**
- Console class for styled output
- Progress bars for phase display
- Panel and Table for structured output
- Automatic terminal width detection

**Python 3.13+ Features to Use:**
- `X | None` union syntax (not `Optional[X]`)
- `list[str]` generic syntax (not `List[str]`)
- `dict[str, Any]` generic syntax
- Match statements where appropriate

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- All CLI output must use Rich Console
- Exception hierarchy must be used (will be implemented in Story 1.3)
- Type annotations are required on all functions
- Models must be in src/adw/models/ (will be implemented in Story 1.2)

---

## Dev Notes

### Critical Success Factors

1. **uv Must Work:** Verify `uv sync` installs all dependencies correctly
2. **CLI Must Start Fast:** <2 second startup time (NFR1)
3. **Structure Must Match Architecture:** Exactly follow the directory layout
4. **Entry Point Must Work:** `adw --help` must display Rich-formatted help

### Common Pitfalls to Avoid

- Don't use pip or poetry - use uv exclusively
- Don't forget `__init__.py` files in all packages
- Don't use print() - use Rich Console
- Don't create models outside of models/ directory (not yet, but be aware)

### References

- [Source: _bmad-output/architecture.md#Starter-Template-Evaluation]
- [Source: _bmad-output/architecture.md#Project-Structure-&-Boundaries]
- [Source: _bmad-output/prd.md#Technical-Decisions]
- [Source: _bmad-output/project-context.md#Technology-Stack-&-Versions]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Completion Notes List

(To be filled by dev agent after implementation)

### File List

(To be filled by dev agent after implementation)

---

## Dependencies

- **Depends On:** None
- **Blocks:** Story 1.2, Story 1.3, Story 1.4, Story 1.5
- **Can Parallel With:** None

### Dependency Rationale
- Story 1.2: Requires project structure with src/adw/models/ directory
- Story 1.3: Requires project structure with src/adw/exceptions.py location
- Story 1.4: Requires project structure with src/adw/executors/ directory
- Story 1.5: Requires project structure with tests/ directory and pyproject.toml
