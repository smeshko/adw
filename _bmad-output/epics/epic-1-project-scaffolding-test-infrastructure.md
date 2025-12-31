# Epic 1: Project Scaffolding & Test Infrastructure

**Goal:** Establish the project foundation with proper Python packaging, Pydantic data models, exception hierarchy, and MockExecutor for deterministic testing. This epic creates the P0-priority modules that all subsequent epics depend upon.

## Story 1.1: Initialize Project Structure with uv and Typer

As a developer,
I want the project scaffolded with uv package manager, proper Python 3.13+ configuration, and Typer CLI entry point,
So that I have a working development environment with the correct tooling from day one.

**Acceptance Criteria:**

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

---

## Story 1.2: Create Core Pydantic Models

As a developer,
I want centralized Pydantic models for RunContext, PhaseResult, and ProjectConfig,
So that all state management uses validated, type-safe data structures.

**Acceptance Criteria:**

**Given** the models module at `src/adw/models/`
**When** I import RunContext
**Then** it includes: run_id (ULID), feature_description (str), current_phase (str), phase_history (list), started_at (datetime), artifacts (dict)
**And** it serializes to JSON with snake_case keys

**Given** a RunContext instance
**When** I call `model_copy(update={"current_phase": "build"})`
**Then** a new instance is returned with the updated phase
**And** the original instance is unchanged (immutability)

**Given** a PhaseResult model
**When** I create an instance
**Then** it includes: phase (str), status (enum: pending|running|completed|failed), started_at, completed_at, artifacts (list[str]), error (optional)

**Given** a ProjectConfig model
**When** I load from valid YAML
**Then** it includes: name, language, framework, platform, test_command, build_command, llm config section

**Given** invalid data for any model
**When** I attempt to create an instance
**Then** Pydantic raises ValidationError with clear field-level messages

---

## Story 1.3: Implement Custom Exception Hierarchy

As a developer,
I want a structured exception hierarchy with typed errors,
So that error handling is consistent and errors are actionable.

**Acceptance Criteria:**

**Given** the exceptions module at `src/adw/exceptions.py`
**When** I import ADWError
**Then** it is the base class with: code (str), message (str), suggestion (str|None), recoverable (bool)

**Given** the exception hierarchy
**When** I inspect available exceptions
**Then** these typed subclasses exist:
  - ConfigError (for configuration issues)
  - HookError (for shell hook failures, includes phase field)
  - LLMError (for Claude Code issues, includes subclasses: LLMTimeoutError, LLMRateLimitError)
  - StateError (for state persistence issues)
  - ValidationError (for schema validation failures)

**Given** any ADWError subclass
**When** I raise it with required fields
**Then** it formats to a user-friendly message suitable for Rich Panel display

**Given** a HookError instance
**When** I access its attributes
**Then** it includes the phase field indicating which phase failed

---

## Story 1.4: Create LLM Executor Protocol and MockExecutor

As a developer,
I want a Protocol-based LLM executor interface with a MockExecutor implementation,
So that I can write deterministic tests without calling Claude Code.

**Acceptance Criteria:**

**Given** the executors module at `src/adw/executors/`
**When** I import LLMExecutor
**Then** it is a Protocol with method: `execute(prompt: str, *, timeout: int | None = None) -> LLMResult`

**Given** an LLMResult model
**When** I inspect its fields
**Then** it includes: success (bool), content (str), tool_calls (list), tokens_used (int), duration_ms (int), error (LLMError | None)

**Given** a MockExecutor instance
**When** I call `configure_responses([{"content": "response1"}, {"content": "response2"}])`
**Then** subsequent execute() calls return those responses in order

**Given** a MockExecutor with configured failures
**When** I call `configure_failures([LLMTimeoutError("timeout"), None])`
**Then** the first execute() raises LLMTimeoutError
**And** the second execute() succeeds

**Given** a MockExecutor instance
**When** I inspect after multiple calls
**Then** I can access: call_count, last_prompt, all_prompts list for assertions

---

## Story 1.5: Set Up pytest Infrastructure and Fixtures

As a developer,
I want pytest configured with coverage, async support, and shared fixtures,
So that I can write and run tests following the 60/30/10 pyramid.

**Acceptance Criteria:**

**Given** pyproject.toml
**When** I inspect pytest configuration
**Then** it specifies:
  - testpaths = ["tests"]
  - asyncio_mode = "auto"
  - addopts includes --cov=adw --cov-fail-under=80

**Given** tests/conftest.py
**When** I import fixtures
**Then** these fixtures are available:
  - `tmp_adw_dir`: Creates isolated `.adw/` in tmp_path
  - `mock_executor`: Returns a fresh MockExecutor
  - `sample_run_context`: Returns a valid RunContext with test data
  - `sample_project_config`: Returns a valid ProjectConfig

**Given** I run `uv run pytest tests/unit/`
**When** tests execute
**Then** they run in isolation with no shared state
**And** coverage report is generated

**Given** tests/fixtures/ directory
**When** I inspect its contents
**Then** it contains subdirectories: runs/, configs/, llm/ for JSON/YAML test data

---

## Epic 1: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [1.1] Initialize Project Structure with uv and Typer                         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                       │
                                       ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 1.1 (PARALLEL)                                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [1.2] Create Core Pydantic Models     ║  [1.3] Implement Exception Hierarchy ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                       │
                                       ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 1.2 AND 1.3                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [1.4] Create LLM Executor Protocol and MockExecutor                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                       │
                                       ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 4: After 1.4 (Final)                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [1.5] Set Up pytest Infrastructure and Fixtures                              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

**Wave Summary:**
- **Wave 1:** 1 story (start immediately)
- **Wave 2:** 2 stories (can run in parallel)
- **Wave 3:** 1 story
- **Wave 4:** 1 story (completes the epic)

**Parallelization Opportunity:** Stories 1.2 and 1.3 can be developed concurrently after Story 1.1 is complete.

---
