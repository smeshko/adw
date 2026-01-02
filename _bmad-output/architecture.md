---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: complete
completedAt: '2025-12-31'
inputDocuments:
  - _bmad-output/prd.md
  - docs/arch-high-level.md
  - docs/arch-entry-point.md
  - docs/arch-orchestrator.md
  - docs/arch-command-system.md
  - docs/arch-llm-executor.md
  - docs/arch-logging.md
  - docs/arch-phase-pipeline.md
workflowType: 'architecture'
lastStep: 0
project_name: 'adw-sdk'
user_name: 'Ivo'
date: '2025-12-30'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The PRD defines 57 functional requirements across 9 categories:

| Category | Count | Architectural Implication |
|----------|-------|--------------------------|
| Run Management | FR1-FR6 | Core orchestration, state machine |
| Phase Execution | FR7-FR12 | Pipeline engine, hook system |
| Verify Phase | FR13-FR18 | Platform-aware evidence gathering |
| Command System | FR19-FR25 | Three-tier resolution, templating |
| LLM Execution | FR26-FR31 | Executor abstraction, retry logic |
| Project Configuration | FR32-FR36 | YAML config, initialization |
| Context & State | FR37-FR41 | Persistence, artifacts, snapshots |
| Observability | FR42-FR53 | Multi-layer logging, CLI commands |
| Git Integration | FR54-FR57 | Branch management, diff capture |

**Non-Functional Requirements:**

| Category | Requirements | Key Constraints |
|----------|--------------|-----------------|
| Performance | NFR1-NFR4 | CLI <2s startup, phase transitions <1s, non-blocking artifact writes |
| Reliability | NFR5-NFR9 | Graceful failure handling, state persistence, resumable runs |
| Observability | NFR10-NFR13 | Actionable errors, reproducible LLM interactions, time-travel debugging |
| Security | NFR14-NFR17 | No secrets in logs, env-based config, redaction patterns |
| Usability | NFR18-NFR21 | Helpful errors, sensible defaults, discoverable help |
| Maintainability | NFR22-NFR25 | >80% test coverage, type hints, extensible architecture |

**Scale & Complexity:**

- Primary domain: **CLI Tool / SDK**
- Complexity level: **Medium**
- Language: **Python 3.13+**
- Package manager: **uv**
- Estimated architectural components: ~12 major modules

### Technical Constraints & Dependencies

**Language & Runtime:**
- Python 3.13+ required (modern features, type hints)
- uv for package management and installation
- Shell scripts for hooks (POSIX-compatible)

**External Dependencies:**
- Claude Code CLI as primary LLM executor
- Git for version control operations
- YAML for configuration files
- JSON Schema (draft-07) for validation

**Pre-existing Architecture:**
- 7 architecture documents already define detailed component designs
- Examples written in TypeScript need translation to Python idioms
- Core patterns (Context Manager, Command Resolver, Phase Runner) are well-specified

### Cross-Cutting Concerns Identified

1. **State Management** - Run context, session context, project context, artifact storage
2. **Logging/Observability** - Console, raw files, structured JSONL, LLM stream capture
3. **Configuration Resolution** - Three-tier override (project → user → default)
4. **Error Handling** - Retry logic, graceful degradation, resumption
5. **Security** - Secret redaction, scoped permissions for hooks
6. **Testing** - >80% coverage requirement, mock executors needed

## Starter Template Evaluation

### Primary Technology Domain

**CLI Tool / SDK** - Python-based command-line interface with real-time streaming, progress display, and comprehensive observability.

### Starter Approach

No pre-built starter template exists for this specialized use case. Recommend custom stack initialization using uv with carefully selected dependencies.

### Selected Stack: Typer + Rich + Pydantic

**Rationale:**
- Typer provides modern, type-hint-based CLI with minimal boilerplate
- Rich delivers the formatted output, progress bars, and logging required by NFR10-NFR13
- Pydantic v2 handles schema validation with native JSON Schema support
- asyncio subprocess enables real-time streaming from Claude Code CLI

**Initialization Command:**

```bash
# Create project with uv
uv init adw --app --python 3.13

# Add core dependencies
uv add typer[all] rich pydantic pyyaml

# Add development dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy
```

### Architectural Decisions Provided by Stack

**CLI Framework (Typer 0.21.0):**
- Decorator-based command definition using `@app.command()`
- Automatic `--help` generation from docstrings and type hints
- Built-in shell completion installation
- Subcommand groups via `typer.Typer()` instances
- Rich integration for error display and help formatting

**Terminal Output (Rich 14.1.0):**
- `Console` for styled output and logging
- `Progress` for multi-phase progress display
- `Live` for real-time updating displays
- `Panel`, `Table` for structured output
- Handles concurrent output without flickering

**Data Validation (Pydantic 2.12+):**
- `BaseModel` for all structured data (RunContext, PhaseResult, etc.)
- JSON Schema generation via `model_json_schema()`
- YAML config loading with validation
- Settings management for configuration hierarchy

**Async Subprocess (Python 3.13 asyncio):**
- `asyncio.create_subprocess_exec()` for Claude Code CLI
- `StreamReader` for real-time stdout/stderr capture
- Non-blocking I/O for responsive phase execution
- Timeout handling via `asyncio.wait_for()`

**Project Structure:**
```
adw/
├── pyproject.toml           # uv/PEP 621 project config
├── src/
│   └── adw/
│       ├── __init__.py
│       ├── cli/             # Typer CLI commands
│       ├── core/            # Orchestrator, Phase Runner
│       ├── commands/        # Command resolution
│       ├── executors/       # LLM executor abstraction
│       ├── logging/         # Multi-tier logging
│       └── models/          # Pydantic models
├── tests/
├── defaults/                # Default command templates
│   └── commands/
└── uv.lock
```

**Note:** Project initialization using these commands should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Async Model: Sync with Async Islands
- Error Handling: Custom Exception Hierarchy
- State Persistence: Pydantic JSON serialization
- Run Identification: ULID

**Important Decisions (Shape Architecture):**
- Concurrency Control: filelock per-run
- Template Engine: Simple regex parser
- Config Hierarchy: project → user → bundled
- Hook Environment: Minimal env vars + context file path

**Deferred Decisions (Post-MVP):**
- Alternative LLM Executors (MVP: Claude Code only)
- Webhook Entry Points (MVP: CLI only)
- Web/Mobile Evidence Gathering (MVP: API only)
- Plugin System

### Async Model

**Decision:** Sync with Async Islands

The orchestrator and phase runner use synchronous Python. Async is used only within the LLM executor for streaming subprocess output via `asyncio.run()`.

**Rationale:**
- Phases execute sequentially, no benefit from full async
- Streaming output requires non-blocking I/O
- Simpler mental model, easier debugging
- NFR3 satisfied: artifact writes don't block streaming

**Pattern:**
```python
# Orchestrator (sync)
def run_phase(self, phase: str) -> PhaseResult:
    result = self.executor.execute(prompt)  # internally uses asyncio
    return result

# LLM Executor (async internally)
def execute(self, prompt: str) -> LLMResult:
    return asyncio.run(self._stream_subprocess(prompt))
```

### Error Handling

**Decision:** Custom Exception Hierarchy

**Base Class:**
```python
class ADWError(Exception):
    code: str           # e.g., "HOOK_FAILED", "LLM_TIMEOUT"
    recoverable: bool   # Can this be retried?
    phase: str | None   # Which phase failed
    suggestion: str     # Actionable next step for user
```

**Exception Hierarchy:**
- `ADWError` (base)
  - `ConfigError` - Invalid configuration
  - `CommandError` - Command resolution failures
  - `HookError` - Pre/post hook failures
  - `LLMError` - Claude Code execution failures
    - `LLMTimeoutError`
    - `LLMRateLimitError`
  - `PhaseError` - Phase execution failures
  - `ValidationError` - Schema/artifact validation failures
  - `StateError` - State persistence/loading failures

**Rationale:** NFR5 (graceful failure), NFR10 (actionable errors), enables smart retry logic.

### State Persistence

**Decision:** Pydantic JSON

All state objects (`RunContext`, `PhaseResult`, `Artifact`) are Pydantic models serialized via `model_dump_json()` and loaded via `model_validate_json()`.

**File Locations:**
```
.adw/runs/<run_id>/
├── context.json          # RunContext - live updated
├── snapshots/
│   └── <seq>_<label>.json  # StateSnapshot at key moments
└── artifacts/
    └── <phase>/
        └── <artifact>.json
```

**Rationale:** Type-safe, validates on load, catches corruption, already using Pydantic.

### Run Identification

**Decision:** ULID via `python-ulid`

Run IDs are ULIDs (Universally Unique Lexicographically Sortable Identifiers).

**Example:** `01HQXK5P3Z7V8R2M4N6T9W1Y3C`

**Rationale:**
- Sortable by creation time (unlike UUIDs)
- Timestamp embedded (debuggable)
- URL-safe, filesystem-safe
- No collisions in practice

### Concurrency Control

**Decision:** `filelock` per-run

Each run acquires `.adw/runs/<run_id>/.lock` before modification.

**Rationale:** Prevents corruption if user accidentally runs `adw resume` twice on same run.

### Template Engine

**Decision:** Simple regex-based parser

Handles two patterns:
- `{{variable.path}}` - Variable substitution from context
- `{{file:relative/path}}` - File content inclusion

**Implementation:**
```python
VARIABLE_PATTERN = r'\{\{([a-z_][a-z0-9_.]*)\}\}'
FILE_PATTERN = r'\{\{file:([^}]+)\}\}'
```

**Rationale:** Jinja2 is overkill. Simple patterns cover all use cases in architecture docs.

### Claude Code CLI Invocation

**Decision:** Run `claude` command, configurable path

**Default:** Invoke `claude` assuming it's in PATH.

**Configuration:** Users can override in config.yaml:
```yaml
llm:
  claude_code:
    path: /custom/path/to/claude
```

**Error Handling:** If `claude` not found, raise `ConfigError` with suggestion to install Claude Code or configure path.

### Evidence Gathering (MVP)

**Decision:** API evidence only for MVP

**MVP Scope:**
- API responses via subprocess calls to `curl`
- Terminal output capture for CLI commands
- JSON response storage in `artifacts/verify/api/`

**Deferred:** Web screenshots (Playwright), mobile screenshots, video recording.

**Rationale:** Reduces dependencies, API evidence sufficient for backend-focused MVP.

### Hook Execution Environment

**Decision:** Minimal env vars + context file path

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `ADW_RUN_ID` | Current run ULID |
| `ADW_PHASE` | Current phase name |
| `ADW_ARTIFACTS_DIR` | Path to artifacts directory |
| `ADW_CONTEXT_FILE` | Path to full context.json |

**Working Directory:** Project root (where `.adw/` lives)

**Rationale:** Hooks can read full context from JSON if needed, env vars cover common cases.

### Config Hierarchy

**Decision:** Three-tier resolution

**Resolution Order (highest priority first):**
1. `.adw/config.yaml` (project-specific)
2. `~/.config/adw/config.yaml` (user preferences)
3. Bundled defaults in package

**Merge Strategy:** Deep merge, arrays replace (don't append).

### Package Distribution

**Decision:** PyPI via uv

**Entry Point:**
```toml
[project.scripts]
adw = "adw.cli:app"
```

**Installation:**
```bash
uv tool install adw
# or
uv pip install adw
```

**Default Commands:** Bundled at `adw/defaults/commands/` within the package.

### Decision Impact Analysis

**Implementation Sequence:**
1. Project scaffolding (Typer CLI skeleton)
2. Pydantic models (RunContext, PhaseResult, etc.)
3. Exception hierarchy
4. Config loading with three-tier resolution
5. State persistence layer
6. Template engine
7. Hook executor
8. LLM executor (Claude Code wrapper)
9. Phase runner
10. Orchestrator
11. CLI commands

**Cross-Component Dependencies:**
- All components depend on Pydantic models
- Phase runner depends on hook executor + LLM executor
- Orchestrator depends on phase runner + state persistence
- CLI depends on orchestrator + logging

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 7 areas where AI agents could make different choices, all addressed below.

### Naming Patterns

**Python Naming (PEP 8 Strict):**

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `phase_runner.py` |
| Packages | snake_case | `adw/executors/` |
| Classes | PascalCase | `PhaseRunner`, `RunContext` |
| Functions | snake_case | `run_phase()`, `load_config()` |
| Methods | snake_case | `def execute_hook(self):` |
| Constants | SCREAMING_SNAKE_CASE | `DEFAULT_TIMEOUT = 300` |
| Private | _underscore prefix | `_internal_state` |
| Type Vars | PascalCase | `T`, `ResultT` |

**Pydantic Model Fields:**

```python
# CORRECT
class RunContext(BaseModel):
    run_id: str
    feature_request: str
    current_phase: str
    completed_phases: list[str]

# WRONG - don't use camelCase in Python
class RunContext(BaseModel):
    runId: str  # NO
    featureRequest: str  # NO
```

**JSON Serialization:** snake_case preserved (no alias conversion)

```python
# Output: {"run_id": "01HQ...", "current_phase": "plan"}
context.model_dump_json()
```

**CLI Command Naming:**

| Element | Convention | Example |
|---------|------------|---------|
| Commands | kebab-case | `adw run`, `adw list-runs` |
| Subcommands | kebab-case | `adw logs show`, `adw logs clean` |
| Options | double-dash + kebab-case | `--run-id`, `--from-phase` |
| Short options | single letter | `-v`, `-q`, `-f` |
| Arguments | SCREAMING_CASE in help | `adw run FEATURE_REQUEST` |

**Config Keys (YAML):**

```yaml
# CORRECT - snake_case
llm:
  claude_code:
    path: /usr/local/bin/claude
    timeout_seconds: 300

# WRONG
llm:
  claudeCode:  # NO - don't use camelCase
    timeoutSeconds: 300  # NO
```

### Structure Patterns

**Project Organization:**

```
src/adw/
├── __init__.py
├── cli/                    # Typer CLI commands
│   ├── __init__.py
│   ├── main.py            # App entry point, root commands
│   ├── run.py             # Run-related commands
│   └── logs.py            # Log-related commands
├── core/                   # Core orchestration logic
│   ├── __init__.py
│   ├── orchestrator.py    # Main orchestrator
│   ├── phase_runner.py    # Phase execution
│   └── context_manager.py # Context handling
├── commands/              # Command resolution
│   ├── __init__.py
│   ├── resolver.py        # Three-tier resolution
│   └── template.py        # Template engine
├── executors/             # LLM executor abstraction
│   ├── __init__.py
│   ├── base.py            # Protocol/ABC
│   ├── claude_code.py     # Claude Code implementation
│   └── mock.py            # Mock for testing
├── logging/               # Logging system
│   ├── __init__.py
│   ├── manager.py         # Log manager
│   ├── console.py         # Rich console transport
│   ├── file.py            # File transports
│   └── stream.py          # LLM stream capture
├── models/                # ALL Pydantic models here
│   ├── __init__.py
│   ├── context.py         # RunContext, SessionContext, etc.
│   ├── config.py          # Configuration models
│   ├── phase.py           # PhaseResult, Artifact
│   └── errors.py          # Error models
├── exceptions.py          # Exception hierarchy
└── utils/                 # Shared utilities
    ├── __init__.py
    ├── files.py           # File operations
    └── ulid.py            # ULID generation
```

**Test Organization:**

```
tests/
├── __init__.py
├── conftest.py            # Shared fixtures
├── fixtures/              # Test data
│   ├── runs/              # Sample run directories
│   └── configs/           # Sample config files
├── unit/                  # Unit tests (mirror src structure)
│   ├── core/
│   │   ├── test_orchestrator.py
│   │   └── test_phase_runner.py
│   ├── executors/
│   │   └── test_claude_code.py
│   └── models/
│       └── test_context.py
└── integration/           # Integration tests
    ├── test_full_run.py
    └── test_resume.py
```

**File Naming Rules:**
- One class per file for major classes: `phase_runner.py` contains `PhaseRunner`
- Related small classes can share: `models/context.py` has `RunContext`, `SessionContext`, `ProjectContext`
- Test files: `test_<module_name>.py`

### Format Patterns

**Log Message Format:**

```python
# CORRECT - structured context, concise message
logger.info("Phase completed", phase="plan", duration_ms=1234)
logger.error("Hook failed", phase="build", hook="pre", exit_code=1)

# WRONG - unstructured, verbose
logger.info(f"The plan phase has completed successfully in 1234ms")  # NO
```

**Log Levels:**

| Level | Usage |
|-------|-------|
| `TRACE` | Internal state changes, full prompts/responses |
| `DEBUG` | Detailed debugging, variable values |
| `INFO` | Normal operations, phase transitions |
| `WARN` | Recoverable issues, deprecations |
| `ERROR` | Failures that stop current operation |
| `FATAL` | Unrecoverable errors, exits |

**Error Message Format:**

```python
# User-facing error (shown in CLI)
raise ConfigError(
    code="CONFIG_NOT_FOUND",
    message="Configuration file not found",
    suggestion="Run 'adw init' to create .adw/config.yaml",
    recoverable=False
)

# Displayed as:
# Error [CONFIG_NOT_FOUND]: Configuration file not found
# Suggestion: Run 'adw init' to create .adw/config.yaml
```

**CLI Output Format:**

```python
# Use Rich for all formatted output
from rich.console import Console
console = Console()

# Progress/status - use Rich components
console.print("[bold green]✓[/] Phase completed: plan")

# Errors - use Rich panels
console.print(Panel(error_message, title="Error", border_style="red"))

# Tables - use Rich tables
table = Table(title="Recent Runs")
```

### Communication Patterns

**Internal Events (Logging Categories):**

```python
# Event naming: component.action
LogCategory.PHASE_START      # "phase.start"
LogCategory.PHASE_END        # "phase.end"
LogCategory.LLM_REQUEST      # "llm.request"
LogCategory.LLM_STREAM       # "llm.stream"
LogCategory.HOOK_EXECUTE     # "hook.execute"
LogCategory.ARTIFACT_SAVE    # "artifact.save"
```

**State Updates:**

```python
# CORRECT - immutable updates via Pydantic
new_context = context.model_copy(update={"current_phase": "build"})

# WRONG - direct mutation
context.current_phase = "build"  # NO - loses audit trail
```

### Process Patterns

**Error Handling Flow:**

```python
# CORRECT - catch specific, re-raise with context
try:
    result = subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    raise HookError(
        code="HOOK_FAILED",
        phase=phase,
        message=f"Hook exited with code {e.returncode}",
        suggestion="Check hook script for errors",
        recoverable=False
    ) from e

# WRONG - bare except, lost context
try:
    result = subprocess.run(cmd, check=True)
except:  # NO
    raise Exception("Hook failed")  # NO - loses context
```

**Resource Cleanup:**

```python
# CORRECT - context managers
with filelock.FileLock(lock_path):
    with open(context_path, "w") as f:
        f.write(context.model_dump_json())

# WRONG - manual cleanup
lock = filelock.FileLock(lock_path)
lock.acquire()  # NO - might not release on error
```

**Type Annotations:**

```python
# CORRECT - full annotations, modern syntax
def run_phase(
    self,
    phase: str,
    context: RunContext,
    *,
    timeout: int | None = None,
) -> PhaseResult:
    ...

# WRONG - missing annotations, old syntax
def run_phase(self, phase, context, timeout=None):  # NO
    ...

# Use TYPE_CHECKING for import cycles
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from adw.core.orchestrator import Orchestrator
```

### Enforcement Guidelines

**All AI Agents MUST:**

1. Follow PEP 8 naming exactly - no exceptions
2. Place ALL Pydantic models in `src/adw/models/`
3. Use the exception hierarchy - never raise bare `Exception`
4. Include type annotations on all public functions
5. Use structured logging with context fields
6. Write tests in `tests/unit/` mirroring source structure
7. Use Rich for all CLI output formatting

**Pattern Verification:**

```bash
# Lint checks (enforced in CI)
ruff check src/               # Style + import sorting
mypy src/                     # Type checking
pytest --cov=adw tests/       # Coverage >80%
```

**Anti-Patterns to Avoid:**

```python
# ❌ Mixing naming conventions
class phase_runner:  # NO - classes are PascalCase
def RunPhase():      # NO - functions are snake_case

# ❌ Models scattered across modules
# models in core/orchestrator.py  # NO - centralize in models/

# ❌ Print statements for output
print("Phase completed")  # NO - use Rich console

# ❌ Untyped functions
def load_config(path):  # NO - add type hints
    ...

# ❌ Generic exceptions
raise Exception("Something failed")  # NO - use ADWError hierarchy

# ❌ Mutable default arguments
def run(phases: list = []):  # NO - use None default
    ...
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
adw/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint, type check, test on PR
│       └── release.yml            # Build and publish to PyPI
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml                 # uv/PEP 621 project config
├── uv.lock                        # Locked dependencies
│
├── src/
│   └── adw/
│       ├── __init__.py            # Package version, exports
│       ├── __main__.py            # `python -m adw` support
│       │
│       ├── cli/                   # Typer CLI layer
│       │   ├── __init__.py
│       │   ├── app.py             # Main Typer app, error handling
│       │   ├── run.py             # `adw run`, `adw resume`, `adw retry`
│       │   ├── logs.py            # `adw logs show/follow/clean`
│       │   ├── config.py          # `adw init`, `adw config`
│       │   └── completions.py     # Shell completion commands
│       │
│       ├── core/                  # Orchestration logic
│       │   ├── __init__.py
│       │   ├── orchestrator.py    # Main run orchestrator
│       │   ├── phase_runner.py    # Single phase execution
│       │   ├── context_manager.py # Context loading/saving
│       │   └── state.py           # State machine, transitions
│       │
│       ├── commands/              # Command resolution
│       │   ├── __init__.py
│       │   ├── resolver.py        # Three-tier resolution logic
│       │   ├── loader.py          # Load command from directory
│       │   └── template.py        # Template variable substitution
│       │
│       ├── executors/             # LLM execution abstraction
│       │   ├── __init__.py
│       │   ├── base.py            # LLMExecutor Protocol
│       │   ├── claude_code.py     # Claude Code CLI wrapper
│       │   ├── result.py          # LLMResult, ToolCall models
│       │   └── mock.py            # MockExecutor for testing
│       │
│       ├── hooks/                 # Hook execution
│       │   ├── __init__.py
│       │   ├── runner.py          # Shell script executor
│       │   └── environment.py     # Env var setup for hooks
│       │
│       ├── logging/               # Multi-tier logging
│       │   ├── __init__.py
│       │   ├── manager.py         # LogManager, global setup
│       │   ├── console.py         # Rich console transport
│       │   ├── file.py            # Raw + structured file transports
│       │   ├── stream.py          # LLM stream capture
│       │   └── snapshots.py       # State snapshot capture
│       │
│       ├── models/                # ALL Pydantic models
│       │   ├── __init__.py        # Re-exports all models
│       │   ├── context.py         # RunContext, SessionContext, ProjectContext
│       │   ├── config.py          # ADWConfig, PhaseConfig, LLMConfig
│       │   ├── phase.py           # PhaseResult, Artifact, PhaseStatus
│       │   ├── command.py         # ResolvedCommand, CommandConfig
│       │   ├── log.py             # LogEvent, LogCategory, StateSnapshot
│       │   └── evidence.py        # EvidenceManifest, EvidenceItem
│       │
│       ├── exceptions.py          # Complete exception hierarchy
│       │
│       └── utils/                 # Shared utilities
│           ├── __init__.py
│           ├── files.py           # File operations, path resolution
│           ├── ulid.py            # ULID generation
│           ├── git.py             # Git operations wrapper
│           └── yaml.py            # YAML loading with validation
│
├── defaults/                      # Bundled default commands
│   └── commands/
│       ├── plan/
│       │   ├── prompt.md
│       │   ├── config.yaml
│       │   └── schema.json
│       ├── build/
│       │   ├── prompt.md
│       │   ├── config.yaml
│       │   ├── pre.sh
│       │   └── post.sh
│       ├── verify/
│       │   ├── prompt.md
│       │   └── config.yaml
│       ├── validate/
│       │   ├── prompt.md
│       │   ├── config.yaml
│       │   └── post.sh
│       ├── document/
│       │   ├── prompt.md
│       │   └── config.yaml
│       └── ship/
│           ├── prompt.md
│           ├── config.yaml
│           └── post.sh
│
└── tests/
    ├── __init__.py
    ├── conftest.py                # Shared fixtures, temp dirs
    │
    ├── fixtures/                  # Test data
    │   ├── configs/               # Sample config files
    │   │   ├── minimal.yaml
    │   │   └── full.yaml
    │   ├── commands/              # Sample command directories
    │   │   └── test_phase/
    │   ├── runs/                  # Sample run directories
    │   │   └── completed_run/
    │   └── prompts/               # Sample prompt templates
    │
    ├── unit/                      # Unit tests (mirror src/)
    │   ├── cli/
    │   │   └── test_run.py
    │   ├── core/
    │   │   ├── test_orchestrator.py
    │   │   ├── test_phase_runner.py
    │   │   └── test_context_manager.py
    │   ├── commands/
    │   │   ├── test_resolver.py
    │   │   └── test_template.py
    │   ├── executors/
    │   │   └── test_claude_code.py
    │   ├── hooks/
    │   │   └── test_runner.py
    │   ├── logging/
    │   │   └── test_manager.py
    │   └── models/
    │       ├── test_context.py
    │       └── test_config.py
    │
    └── integration/               # Integration tests
        ├── test_full_run.py       # Complete run with mock executor
        ├── test_resume.py         # Resume from checkpoint
        └── test_config_hierarchy.py
```

### Architectural Boundaries

**CLI Boundary (src/adw/cli/):**
- Handles user input parsing and validation
- Formats output using Rich
- Catches exceptions and displays user-friendly errors
- Delegates to core orchestrator - NO business logic here

**Core Boundary (src/adw/core/):**
- Contains all orchestration logic
- Manages state transitions and persistence
- Coordinates phase execution
- Pure Python - no CLI dependencies (Rich OK for logging)

**Executor Boundary (src/adw/executors/):**
- Isolated LLM interaction
- Protocol-based for testability
- Handles streaming, retries, timeouts
- Returns structured results, raises typed exceptions

**Command Boundary (src/adw/commands/):**
- Resolution logic only
- Loads from filesystem
- Applies template substitution
- Returns fully resolved command ready for execution

**Logging Boundary (src/adw/logging/):**
- Self-contained logging system
- Multiple transports (console, file, structured)
- Stream capture for LLM output
- State snapshots for debugging

### Requirements to Structure Mapping

**FR1-FR6 (Run Management):**
- `cli/run.py` - CLI commands
- `core/orchestrator.py` - Run lifecycle
- `core/state.py` - State machine
- `models/context.py` - RunContext model

**FR7-FR12 (Phase Execution):**
- `core/phase_runner.py` - Phase execution
- `hooks/runner.py` - Pre/post hook execution
- `models/phase.py` - PhaseResult, PhaseStatus

**FR13-FR18 (Verify Phase):**
- `defaults/commands/verify/` - Default verify command
- `models/evidence.py` - Evidence models
- `utils/` - Evidence capture utilities

**FR19-FR25 (Command System):**
- `commands/resolver.py` - Three-tier resolution
- `commands/loader.py` - Command directory loading
- `commands/template.py` - Variable substitution
- `models/command.py` - Command models

**FR26-FR31 (LLM Execution):**
- `executors/base.py` - Protocol definition
- `executors/claude_code.py` - Claude Code wrapper
- `executors/result.py` - Result models

**FR32-FR36 (Project Configuration):**
- `cli/config.py` - Config CLI commands
- `models/config.py` - Config models
- `utils/yaml.py` - YAML loading

**FR37-FR41 (Context & State):**
- `core/context_manager.py` - Context persistence
- `logging/snapshots.py` - State snapshots
- `models/context.py` - Context models

**FR42-FR53 (Observability):**
- `logging/manager.py` - Log manager
- `logging/console.py` - Console output
- `logging/file.py` - File logging
- `logging/stream.py` - LLM stream capture
- `cli/logs.py` - Log CLI commands

**FR54-FR57 (Git Integration):**
- `utils/git.py` - Git operations
- `defaults/commands/build/pre.sh` - Branch creation
- `defaults/commands/ship/post.sh` - PR creation

### Integration Points

**Internal Communication:**

```
CLI Layer
    │
    ▼ (calls)
Orchestrator
    │
    ├──▶ ContextManager (load/save state)
    │
    ├──▶ CommandResolver (resolve phase commands)
    │
    └──▶ PhaseRunner
            │
            ├──▶ HookRunner (pre/post scripts)
            │
            ├──▶ LLMExecutor (Claude Code)
            │
            └──▶ LogManager (events, streaming)
```

**External Integrations:**

| Integration | Location | Purpose |
|-------------|----------|---------|
| Claude Code CLI | `executors/claude_code.py` | LLM execution |
| Git | `utils/git.py` | Version control |
| Filesystem | `core/context_manager.py` | State persistence |
| Shell | `hooks/runner.py` | Hook execution |

**Data Flow:**

```
User Input (feature request)
    │
    ▼
RunContext created
    │
    ▼
For each phase:
    │
    ├──▶ Load command (resolver)
    │
    ├──▶ Render prompt (template)
    │
    ├──▶ Run pre-hook (hooks)
    │
    ├──▶ Execute LLM (executor) ──▶ Stream to console + files
    │
    ├──▶ Run post-hook (hooks)
    │
    ├──▶ Capture artifact
    │
    └──▶ Update context, save snapshot
    │
    ▼
Run complete, final state persisted
```

### File Organization Patterns

**Configuration Files:**

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, tool config |
| `uv.lock` | Locked dependency versions |
| `.github/workflows/*.yml` | CI/CD pipelines |
| `.gitignore` | Git ignore patterns |
| `defaults/commands/*/config.yaml` | Default phase configurations |

**Runtime Files (.adw/ in user's project):**

```
.adw/
├── config.yaml              # Project-specific config
├── commands/                # Project command overrides
│   └── <phase>/
└── runs/
    └── <run_id>/
        ├── context.json     # Run state
        ├── .lock            # Concurrency lock
        ├── logs/
        │   ├── raw.log
        │   └── structured.jsonl
        ├── snapshots/
        │   └── <seq>_<label>.json
        ├── llm/
        │   └── <phase>_stream.jsonl
        └── artifacts/
            └── <phase>/
```

### Development Workflow Integration

**Local Development:**
```bash
# Clone and setup
git clone <repo>
cd adw
uv sync                      # Install dependencies

# Development
uv run adw --help            # Run CLI
uv run pytest                # Run tests
uv run ruff check src/       # Lint
uv run mypy src/             # Type check

# Build
uv build                     # Create wheel
```

**CI Pipeline (.github/workflows/ci.yml):**
```yaml
- Checkout
- Setup Python 3.13
- Install uv
- uv sync
- ruff check src/
- mypy src/
- pytest --cov=adw --cov-fail-under=80
```

**Release Pipeline (.github/workflows/release.yml):**
```yaml
- Triggered on tag push (v*)
- Build wheel
- Publish to PyPI via uv publish
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are compatible and work together seamlessly:
- Typer 0.21.0 has native Rich integration ✓
- Pydantic 2.12+ works with Python 3.13+ type hints ✓
- asyncio subprocess is stdlib, no conflicts ✓
- uv manages all dependencies cleanly ✓
- filelock, python-ulid are lightweight with no conflicts ✓

**Pattern Consistency:**
- PEP 8 naming applied uniformly across all code patterns
- CLI uses kebab-case, Python uses snake_case, classes use PascalCase - consistent
- JSON serialization preserves snake_case (Pydantic default) - aligned with Python patterns
- Logging patterns use structured fields - consistent with Pydantic models
- Exception hierarchy follows Python conventions with custom attributes

**Structure Alignment:**
- src layout supports Pydantic, Typer, and uv packaging
- models/ centralization aligns with Pydantic's validation-at-boundary pattern
- executors/ abstraction supports mock testing (NFR22)
- logging/ isolation enables multi-transport architecture
- CLI/core separation enables testing without CLI dependencies

### Requirements Coverage Validation ✅

**Functional Requirements Coverage (57 FRs):**

| Category | FRs | Coverage | Location |
|----------|-----|----------|----------|
| Run Management | FR1-FR6 | ✅ Complete | `core/orchestrator.py`, `cli/run.py` |
| Phase Execution | FR7-FR12 | ✅ Complete | `core/phase_runner.py`, `hooks/` |
| Verify Phase | FR13-FR18 | ✅ Complete | `defaults/commands/verify/`, `models/evidence.py` |
| Command System | FR19-FR25 | ✅ Complete | `commands/resolver.py`, `commands/template.py` |
| LLM Execution | FR26-FR31 | ✅ Complete | `executors/claude_code.py`, `executors/base.py` |
| Project Configuration | FR32-FR36 | ✅ Complete | `utils/yaml.py`, `models/config.py` |
| Context & State | FR37-FR41 | ✅ Complete | `core/context_manager.py`, `logging/snapshots.py` |
| Observability | FR42-FR53 | ✅ Complete | `logging/*`, `cli/logs.py` |
| Git Integration | FR54-FR57 | ✅ Complete | `utils/git.py`, `defaults/commands/*/pre.sh` |

**Non-Functional Requirements Coverage (25 NFRs):**

| NFR | Requirement | Architectural Support |
|-----|-------------|----------------------|
| NFR1 | CLI startup <2s | Lazy imports, minimal dependencies |
| NFR2 | Phase transitions <1s | Direct function calls, no remote services |
| NFR3 | Non-blocking artifact writes | asyncio in executor, background file writes |
| NFR5 | Graceful failure handling | Custom exception hierarchy with recovery hints |
| NFR6 | State persistence | Pydantic JSON at each phase boundary |
| NFR8 | Resume from any phase | `context.json` with completed_phases tracking |
| NFR10 | Actionable error messages | `suggestion` field in all exceptions |
| NFR14 | No secrets in logs | Redaction patterns in logging config |
| NFR22 | >80% test coverage | MockExecutor, fixtures, pytest-cov |

### Implementation Readiness Validation ✅

**Decision Completeness:**
- ✅ All critical decisions documented with specific library versions
- ✅ Async model explicitly chosen (Sync with Async Islands)
- ✅ Error handling pattern fully specified with exception hierarchy
- ✅ State persistence format decided (Pydantic JSON)
- ✅ Template engine approach specified (simple regex)

**Structure Completeness:**
- ✅ Every file and directory defined in project tree
- ✅ All modules have explicit purposes documented
- ✅ Test structure mirrors source structure
- ✅ Default commands structure fully specified
- ✅ Runtime file locations (.adw/) documented

**Pattern Completeness:**
- ✅ Naming conventions cover all code elements
- ✅ Logging patterns include levels and structured fields
- ✅ Error handling shows correct/incorrect examples
- ✅ Type annotation patterns specified
- ✅ Anti-patterns explicitly documented

### Gap Analysis Results

**Critical Gaps: None**

All blocking decisions have been made. Implementation can proceed.

**Important Gaps (Non-Blocking):**

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| Exact Pydantic model field definitions | Low | Define during first story implementation |
| Default prompt.md content | Low | Write as part of Phase 6 command scaffolding |
| JSON Schema for artifacts | Low | Generate from Pydantic models |

**Nice-to-Have (Future Enhancement):**

| Enhancement | Benefit |
|-------------|---------|
| OpenTelemetry integration | Distributed tracing support |
| Plugin system architecture | Extensibility for custom phases |
| Alternative executor support | OpenAI, local models |
| Cross-project dashboard | Aggregate runs across all projects, token/cost tracking, analytics |

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (57 FRs, 25 NFRs)
- [x] Scale and complexity assessed (Medium - CLI tool)
- [x] Technical constraints identified (Python 3.13+, uv)
- [x] Cross-cutting concerns mapped (logging, error handling, state)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified (Typer, Rich, Pydantic)
- [x] Integration patterns defined (subprocess, filesystem)
- [x] Performance considerations addressed (async streaming)

**✅ Implementation Patterns**
- [x] Naming conventions established (PEP 8 + CLI conventions)
- [x] Structure patterns defined (src layout, model centralization)
- [x] Communication patterns specified (internal flow, logging events)
- [x] Process patterns documented (error handling, resource cleanup)

**✅ Project Structure**
- [x] Complete directory structure defined (40+ files)
- [x] Component boundaries established (CLI, Core, Executors, etc.)
- [x] Integration points mapped (CLI→Orchestrator→PhaseRunner→Executor)
- [x] Requirements to structure mapping complete (all 57 FRs)

### Architecture Readiness Assessment

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
1. Clear separation of concerns (CLI vs Core vs Executors)
2. Testable architecture (Protocol-based executors, MockExecutor)
3. Comprehensive observability (multi-tier logging, snapshots)
4. Extensible design (executor abstraction, command resolution)
5. Consistent patterns prevent AI agent conflicts

**Areas for Future Enhancement:**
1. Alternative LLM executor support (post-MVP)
2. Webhook entry points for Linear/GitHub (post-MVP)
3. Web/mobile evidence gathering (post-MVP)
4. Plugin system for custom phases (post-MVP)
5. Cross-project run visibility and dashboard (post-MVP) - See Epic 10

### Implementation Handoff

**AI Agent Guidelines:**

1. Follow all architectural decisions exactly as documented
2. Use implementation patterns consistently across all components
3. Place ALL Pydantic models in `src/adw/models/`
4. Use the exception hierarchy - never raise bare `Exception`
5. Respect project structure and component boundaries
6. Use Rich for all CLI output, structured logging for files
7. Refer to this document for all architectural questions

**First Implementation Priority:**

```bash
# Step 1: Initialize project
uv init adw --app --python 3.13
cd adw

# Step 2: Add dependencies
uv add typer[all] rich pydantic pyyaml filelock python-ulid
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy

# Step 3: Create directory structure
# (per Project Structure section)

# Step 4: Implement in dependency order
# 1. models/ (no dependencies)
# 2. exceptions.py (no dependencies)
# 3. utils/ (depends on models)
# 4. logging/ (depends on models)
# 5. commands/ (depends on models, utils)
# 6. hooks/ (depends on models, logging)
# 7. executors/ (depends on models, logging)
# 8. core/ (depends on all above)
# 9. cli/ (depends on core)
```

## Future Enhancement: Cross-Project Run Visibility & Dashboard

### Overview

Post-MVP enhancement to provide visibility into all ADW runs across multiple projects from a single view. Enables dashboards, analytics, and cross-project run management.

### Current Architecture Support

The existing architecture already captures rich data per run:

| Data | Location | Dashboard Use |
|------|----------|---------------|
| Run metadata | `context.json` | Run list, status, duration |
| Phase results | `artifacts/<phase>/` | Phase performance, failure analysis |
| Token usage | `llm/*_response.json` | Cost tracking, usage trends |
| Structured logs | `logs/logs.jsonl` | Error patterns, debugging |
| Timestamps | ULID run_id | Timeline views, sorting |

### Architectural Additions Required

**1. Project Registry** (`~/.config/adw/projects.yaml`)
```yaml
projects:
  - path: /Users/dev/my-api
    name: my-api
    registered_at: 2025-01-15T10:00:00Z
  - path: /Users/dev/frontend
    name: frontend-app
    registered_at: 2025-01-16T14:30:00Z
```

**2. Optional Central Index** (`~/.config/adw/run-index.sqlite` or `.jsonl`)
- Mirrors run metadata for fast cross-project queries
- Updated on run state changes (dual-write pattern)
- Enables filtering, aggregation without filesystem scanning

**3. Model Enhancements**

```python
# Add to RunContext
class RunContext(BaseModel):
    # ... existing fields ...
    project_name: str | None = None    # Human-readable project name
    tags: list[str] = []               # User-defined labels
    initiated_by: str | None = None    # Username/identifier
```

### Dashboard Capabilities

| View | Description | Data Source |
|------|-------------|-------------|
| Run Overview | All runs across projects with status, duration | `context.json` aggregation |
| Project Summary | Per-project metrics, success rates | Grouped by project_name |
| Timeline | Runs over time, patterns, trends | ULID timestamps |
| Token/Cost Analytics | Usage tracking, cost estimates | `llm/*_response.json` |
| Failure Analysis | Common errors, failure phases | PhaseResult + logs |
| Active Runs | Currently running executions | `status == "running"` |

### CLI Commands (Proposed)

```bash
adw register                    # Register current project
adw global list                 # List runs across all projects
adw global stats                # Show aggregate statistics
adw global dashboard            # TUI dashboard (Rich-based)
```

### Implementation Notes

- **File-based aggregation** works for <1000 runs, simple to implement
- **SQLite index** recommended for larger scale, enables rich queries
- **Web dashboard** could consume the index via simple HTTP server
- No changes to core run execution - purely additive

See **Epic 10** for detailed implementation stories.

## Future Enhancement: Task Manager Integration

### Overview

Post-MVP enhancement enabling runs to be initiated from external task managers (Linear, Jira, GitHub Issues). The SDK fetches task content automatically and synchronizes status at phase transitions.

### Architectural Pattern

**Protocol-Based Abstraction:**

```python
from typing import Protocol

class TaskManager(Protocol):
    """Protocol for external task manager integration."""

    def fetch_task(self, task_id: str) -> TaskInfo:
        """Fetch task details from external system."""
        ...

    def update_status(self, task_id: str, status: str, metadata: dict) -> None:
        """Update task status in external system."""
        ...

    def resolve_task_id(self, input_str: str) -> str | None:
        """Extract task ID from input string if it matches this manager's pattern."""
        ...
```

**Configuration:**

```yaml
# .adw/project.yaml
task_manager: linear  # or: jira, github_issues, none
task_manager_config:
  # Linear-specific
  api_key_env: LINEAR_API_KEY  # Environment variable name
  team_key: RULE  # For pattern matching RULE-123

  # State mapping (ADW state → Task Manager state)
  state_mapping:
    pending: "Todo"
    running: "In Progress"
    completed: "Done"
    failed: "In Progress"  # Keep open for retry
```

### Integration Points

| Component | Integration |
|-----------|-------------|
| CLI (`cli/run.py`) | Detect task ID pattern, call `task_manager.fetch_task()` |
| Orchestrator | Call `task_manager.update_status()` at phase transitions |
| Config | Load task_manager settings, instantiate correct implementation |
| Models | `TaskInfo` model for fetched task data |

### File Locations

```
src/adw/
├── task_managers/           # New package
│   ├── __init__.py
│   ├── base.py              # TaskManager Protocol
│   ├── linear.py            # Linear implementation
│   ├── jira.py              # Jira implementation (future)
│   └── github_issues.py     # GitHub Issues (future)
└── models/
    └── task.py              # TaskInfo model
```

### Data Flow

```
User: adw run RULE-123
         │
         ▼
    CLI detects task ID pattern
         │
         ▼
    TaskManager.fetch_task("RULE-123")
         │
         ▼
    Returns TaskInfo(title, description, labels, ...)
         │
         ▼
    RunContext created with task content as feature_request
         │
         ▼
    Orchestrator runs phases
         │ (at each transition)
         ▼
    TaskManager.update_status("RULE-123", "running", {phase: "build"})
         │
         ▼
    Run completes
         │
         ▼
    TaskManager.update_status("RULE-123", "completed", {run_id: "..."})
```

See **Epic 11** for implementation stories.

---

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2025-12-31
**Document Location:** `_bmad-output/architecture.md`

### Final Architecture Deliverables

**Complete Architecture Document**
- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation**
- 15+ architectural decisions made
- 7 implementation pattern categories defined
- 9 architectural components specified
- 57 functional requirements fully supported
- 25 non-functional requirements addressed

**AI Agent Implementation Guide**
- Technology stack with verified versions (Typer 0.21.0, Rich 14.1.0, Pydantic 2.12+)
- Consistency rules that prevent implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards

### Quality Assurance Checklist

**✅ Architecture Coherence**
- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**✅ Requirements Coverage**
- [x] All functional requirements are supported
- [x] All non-functional requirements are addressed
- [x] Cross-cutting concerns are handled
- [x] Integration points are defined

**✅ Implementation Readiness**
- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples are provided for clarity

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

