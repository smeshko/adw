---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/prd.md
  - _bmad-output/architecture.md
  - _bmad-output/ux-design-specification.md
status: complete
totalStories: 47
totalEpics: 9
validated: 2025-12-31
---

# adw-sdk - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for adw-sdk, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Run Management (FR1-FR6):**
- FR1: User can start a new run with a feature description via CLI
- FR2: User can resume a previously failed run from the last successful phase
- FR3: User can check the status of any run by ID
- FR4: User can list recent runs with their statuses
- FR5: User can abort a running execution
- FR6: System generates unique run IDs for tracking

**Phase Execution (FR7-FR12):**
- FR7: System executes phases in fixed order (Plan → Build → Verify → Validate → Document)
- FR8: System runs pre-hooks before LLM execution in each phase
- FR9: System runs post-hooks after LLM execution in each phase
- FR10: System captures artifacts at the end of each phase
- FR11: System makes previous phase artifacts available to subsequent phases
- FR12: User can execute a single phase in isolation

**Verify Phase / Evidence Gathering (FR13-FR18):**
- FR13: System gathers platform-appropriate evidence based on project type
- FR14: For CLI projects: System captures terminal output for key commands
- FR15: For web projects: System captures screenshots of key routes
- FR16: For backend projects: System captures API request/response pairs
- FR17: System generates evidence manifest linking evidence to plan steps
- FR18: System compresses and optimizes captured evidence

**Command System (FR19-FR25):**
- FR19: System resolves commands using three-tier hierarchy (project → user → default)
- FR20: User can override any command file at project level
- FR21: User can override any command file at user level
- FR22: System renders prompt templates with variable substitution
- FR23: System validates LLM output against schema when provided
- FR24: System executes pre-hooks and captures stdout for prompt context
- FR25: System executes post-hooks for validation and cleanup

**LLM Execution (FR26-FR31):**
- FR26: System invokes Claude Code CLI for LLM execution
- FR27: System streams LLM output in real-time to console
- FR28: System captures tool calls made by the LLM
- FR29: System retries on transient failures with exponential backoff
- FR30: System respects timeout configuration
- FR31: System tracks token usage for each execution

**Project Configuration (FR32-FR36):**
- FR32: User can initialize a new project with `adw init`
- FR33: System creates `.adw/` directory with default configuration
- FR34: User can configure project metadata (name, language, framework, platform)
- FR35: User can configure test and build commands
- FR36: System loads configuration from `.adw/project.yaml`

**Context & State (FR37-FR41):**
- FR37: System persists run context to `.adw/runs/<id>/`
- FR38: System creates state snapshots at phase boundaries
- FR39: System stores artifacts in `.adw/runs/<id>/artifacts/<phase>/`
- FR40: User can inspect any artifact from a run
- FR41: System maintains run context across interruptions

**Observability & Logging (FR42-FR53):**
- FR42: System displays phase progress in console output
- FR43: System writes raw logs to `.adw/runs/<id>/logs/raw.log`
- FR44: System writes structured logs in JSONL format
- FR45: System captures full LLM request/response for debugging
- FR46: User can view logs with configurable verbosity levels (--quiet, --verbose, --trace)
- FR47: User can follow live logs with `adw logs follow`
- FR48: User can search logs with `adw logs search`
- FR49: User can view LLM interactions with `adw logs llm`
- FR50: User can inspect state at any point with `adw logs state`
- FR51: User can diff state between phases with `adw logs diff`
- FR52: User can export logs for sharing with `adw logs export`
- FR53: User can list and view state snapshots

**Git Integration (FR54-FR57):**
- FR54: Pre-hooks can create feature branches
- FR55: Post-hooks can stage and commit changes
- FR56: System captures git diff as build artifact
- FR57: Document phase generates PR-ready description

### NonFunctional Requirements

**Performance (NFR1-NFR4):**
- NFR1: CLI startup time shall be under 2 seconds
- NFR2: Phase transitions shall complete within 1 second (excluding LLM time)
- NFR3: Artifact writes shall not block LLM streaming
- NFR4: State snapshots shall complete within 500ms

**Reliability (NFR5-NFR9):**
- NFR5: System shall gracefully handle LLM API failures with retry
- NFR6: System shall persist state before each phase transition
- NFR7: System shall recover from interruption (Ctrl+C) without data loss
- NFR8: Resume shall succeed if the previous run reached a phase boundary
- NFR9: System shall validate all configuration before starting a run

**Observability (NFR10-NFR13):**
- NFR10: All errors shall include actionable error messages
- NFR11: Debug logs shall include sufficient context to diagnose issues
- NFR12: LLM interactions shall be fully reproducible from logs
- NFR13: State snapshots shall enable "time travel" debugging

**Security (NFR14-NFR17):**
- NFR14: System shall not log API keys or secrets
- NFR15: System shall support environment variables for sensitive configuration
- NFR16: Hooks shall execute with repository-scoped permissions only
- NFR17: System shall redact sensitive patterns from logs (configurable)

**Usability (NFR18-NFR21):**
- NFR18: CLI shall provide helpful error messages for common mistakes
- NFR19: Default configuration shall work for common project types
- NFR20: Documentation shall include quickstart and common use cases
- NFR21: CLI help shall be discoverable via `--help` on all commands

**Maintainability (NFR22-NFR25):**
- NFR22: Codebase shall have >80% test coverage for core logic
- NFR23: All public APIs shall have type hints
- NFR24: Architecture shall support adding new phases without core changes
- NFR25: Executor interface shall support adding new LLM backends

### Additional Requirements

**From Architecture:**
- ARCH-1: Starter template uses Typer 0.21.0 + Rich 14.1.0 + Pydantic 2.12+
- ARCH-2: Project uses Python 3.13+ with uv package manager
- ARCH-3: Async model is "Sync with Async Islands" (sync orchestrator, async LLM streaming)
- ARCH-4: Custom exception hierarchy (ADWError base with typed subclasses)
- ARCH-5: State persistence uses Pydantic JSON serialization
- ARCH-6: Run IDs use ULID format via python-ulid
- ARCH-7: Concurrency control via filelock per-run
- ARCH-8: Template engine uses simple regex for {{var}} and {{file:path}}
- ARCH-9: Claude Code CLI invoked as `claude`, configurable path
- ARCH-10: Three-tier config hierarchy: project → user → bundled defaults
- ARCH-11: All Pydantic models centralized in src/adw/models/
- ARCH-12: PEP 8 strict naming conventions throughout

**From UX Design:**
- UX-1: All output through Rich Console - never use print()
- UX-2: Phase progress uses Rich Progress bars with spinner, text, bar, percentage
- UX-3: Errors displayed in Rich Panels with title, error, suggestion, resume command
- UX-4: Completion shown in Rich Panel with PR URL, artifacts path, duration
- UX-5: Verbosity levels: quiet (-q), normal (default), verbose (-v), trace (--trace)
- UX-6: Text-only phase labels [PLAN] [BUILD] etc. for terminal compatibility
- UX-7: Non-TTY mode disables colors, animations; outputs machine-readable
- UX-8: Ctrl+C prompts "Abort run?" with confirmation
- UX-9: LLM progress shows spinner + token count + elapsed time
- UX-10: Terminal width adaptation (compact <60, standard 60-120, wide >120)
- UX-11: All emoji have text fallbacks for accessibility
- UX-12: Run header panel shows run ID, feature, started timestamp

### FR Coverage Map

| Epic | Requirements Covered |
|------|---------------------|
| **Epic 1: Project Scaffolding & Test Infrastructure** | ARCH-1 through ARCH-12, NFR22-25 |
| **Epic 2: Command Resolution & Templates** | FR19-FR25, ARCH-8, ARCH-10 |
| **Epic 3: Hook & Phase Execution** | FR8-FR9, FR26-FR31, ARCH-9, NFR3-5 |
| **Epic 4: State Persistence & Context Management** | FR37-FR41, ARCH-5-7, NFR6-9 |
| **Epic 5: Pipeline Orchestration** | FR7, FR10-FR12, NFR1-2 |
| **Epic 6: Run Management & Recovery** | FR1-FR6, NFR7-8, NFR10, NFR18-21 |
| **Epic 7: Observability & Logging** | FR42-FR53, NFR10-13, NFR14-17 |
| **Epic 8: Evidence Gathering** | FR13-FR18 |
| **Epic 9: Git Integration & Documentation** | FR54-FR57 |

## Epic List

| Epic | Title | Goal | Priority | Test Priority |
|------|-------|------|----------|---------------|
| 1 | Project Scaffolding & Test Infrastructure | Establish project foundation with Pydantic models, exception hierarchy, and MockExecutor for test enablement | P0 | P0 (models, exceptions) |
| 2 | Command Resolution & Templates | Enable command/prompt resolution with three-tier hierarchy and template variable substitution | P1 | P1 (template.py) |
| 3 | Hook & Phase Execution | Execute shell hooks and LLM calls within phases with streaming, retry, and timeout support | P1 | P1/P2 (executor, hooks) |
| 4 | State Persistence & Context Management | Persist run state with atomic writes, snapshots, and artifact storage for resumability | P1 | P1 (context_manager, ASR-5) |
| 5 | Pipeline Orchestration | Coordinate phase execution in order, manage transitions, and handle artifacts | P2 | P2 (orchestrator) |
| 6 | Run Management & Recovery | Enable users to start, resume, abort, and monitor runs through CLI commands | P2 | E2E (cli/) |
| 7 | Observability & Logging | Provide multi-tier logging, state inspection, and debugging capabilities | P3 | Integration |
| 8 | Evidence Gathering | Capture platform-appropriate evidence during Verify phase | P3 | Integration |
| 9 | Git Integration & Documentation | Support git workflows and generate PR-ready documentation | P4 | Integration |

---

## Epic 1: Project Scaffolding & Test Infrastructure

**Goal:** Establish the project foundation with proper Python packaging, Pydantic data models, exception hierarchy, and MockExecutor for deterministic testing. This epic creates the P0-priority modules that all subsequent epics depend upon.

### Story 1.1: Initialize Project Structure with uv and Typer

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

### Story 1.2: Create Core Pydantic Models

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

### Story 1.3: Implement Custom Exception Hierarchy

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

### Story 1.4: Create LLM Executor Protocol and MockExecutor

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

### Story 1.5: Set Up pytest Infrastructure and Fixtures

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

### Epic 1: Dependency Flowchart

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

## Epic 2: Command Resolution & Templates

**Goal:** Enable command and prompt resolution using the three-tier hierarchy (project → user → bundled) with template variable substitution. This epic provides the foundation for loading and rendering phase prompts.

### Story 2.1: Implement Three-Tier Command Resolution

As a developer,
I want commands resolved from project, then user, then bundled defaults,
So that users can override any command at the appropriate level.

**Acceptance Criteria:**

**Given** a command name "plan"
**When** the resolver searches for it
**Then** it checks in order:
  1. `.adw/commands/plan/` (project level)
  2. `~/.adw/commands/plan/` (user level)
  3. Bundled defaults in package

**Given** a command exists at project level
**When** the same command exists at user and bundled level
**Then** the project-level command is used

**Given** a command exists only at bundled level
**When** project and user levels are empty
**Then** the bundled command is used

**Given** a command name that doesn't exist anywhere
**When** resolution is attempted
**Then** ConfigError is raised with code "COMMAND_NOT_FOUND" and helpful suggestion

**Given** a resolved command directory
**When** I inspect its contents
**Then** it contains: prompt.md, optionally schema.json, optionally pre-hook.sh, post-hook.sh

---

### Story 2.2: Create Template Engine with Variable Substitution

As a developer,
I want templates rendered with {{variable}} substitution,
So that prompts can include dynamic content from the run context.

**Acceptance Criteria:**

**Given** a template string with `{{feature_description}}`
**When** rendered with context containing feature_description="Add login"
**Then** the output contains "Add login"

**Given** a template with `{{file:path/to/file.txt}}`
**When** the file exists and contains "file content"
**Then** the output contains "file content"

**Given** a template with `{{file:nonexistent.txt}}`
**When** rendering is attempted
**Then** ConfigError is raised with code "TEMPLATE_FILE_NOT_FOUND"

**Given** a template with nested variables `{{phase_{{index}}}}`
**When** rendering is attempted
**Then** only single-level substitution occurs (no recursive expansion)

**Given** a template with `{{unknown_var}}`
**When** rendering is attempted with strict mode
**Then** ConfigError is raised with code "UNKNOWN_VARIABLE"

**Given** a template with `{{unknown_var}}`
**When** rendering is attempted with lenient mode
**Then** the variable is left as-is in output

---

### Story 2.3: Load and Render Phase Prompts

As a developer,
I want to load a phase prompt from the resolved command directory and render it,
So that each phase has its complete, rendered prompt ready for LLM execution.

**Acceptance Criteria:**

**Given** a phase "plan" with resolved command directory
**When** I call `load_prompt("plan", context)`
**Then** it reads `prompt.md` from the command directory
**And** renders all template variables using the context

**Given** a prompt that references artifacts from previous phases
**When** the template contains `{{artifacts.build.diff}}`
**Then** the artifact content is included in the rendered prompt

**Given** a command directory with pre-hook output
**When** pre-hook stdout is available as `{{pre_hook_output}}`
**Then** it's included in the template context for rendering

**Given** the rendered prompt
**When** I inspect it
**Then** no unresolved `{{...}}` patterns remain (in strict mode)

---

### Story 2.4: Validate LLM Output Against Schema

As a developer,
I want LLM output validated against an optional JSON schema,
So that I can ensure structured output meets expectations.

**Acceptance Criteria:**

**Given** a command directory with `schema.json`
**When** LLM output matches the schema
**Then** validation passes and returns parsed data

**Given** a command directory with `schema.json`
**When** LLM output doesn't match the schema
**Then** ValidationError is raised with specific field errors

**Given** a command directory without `schema.json`
**When** LLM output is received
**Then** no validation is performed and raw content is returned

**Given** LLM output as markdown with JSON code block
**When** schema validation is enabled
**Then** JSON is extracted from the code block before validation

**Given** multiple JSON code blocks in output
**When** extraction is attempted
**Then** the first valid JSON block matching the schema is used

---

## Epic 3: Hook & Phase Execution

**Goal:** Execute shell hooks (pre/post) and LLM calls within phases with streaming output, retry logic, and timeout support. This epic enables the core execution capability.

### Story 3.1: Execute Shell Hooks with Capture

As a developer,
I want to execute shell scripts as pre-hooks and post-hooks,
So that I can run custom logic before and after LLM execution.

**Acceptance Criteria:**

**Given** a pre-hook script at `commands/plan/pre-hook.sh`
**When** the hook is executed
**Then** stdout is captured and returned for use in templates
**And** stderr is logged

**Given** a hook script that exits with code 0
**When** execution completes
**Then** the hook is considered successful

**Given** a hook script that exits with non-zero code
**When** execution completes
**Then** HookError is raised with exit code, stdout, and stderr

**Given** a hook script that takes longer than the configured timeout
**When** timeout is reached
**Then** the process is killed and HookError is raised with code "HOOK_TIMEOUT"

**Given** environment variables in the run context
**When** the hook executes
**Then** they are available to the script (ADW_RUN_ID, ADW_PHASE, ADW_FEATURE, etc.)

**Given** a command directory without hooks
**When** hook execution is requested
**Then** it's silently skipped (not an error)

---

### Story 3.2: Implement Claude Code Executor with Streaming

As a developer,
I want to invoke Claude Code CLI and stream its output in real-time,
So that users see LLM responses as they're generated.

**Acceptance Criteria:**

**Given** a rendered prompt
**When** I call the Claude Code executor
**Then** it spawns `claude` (or configured path) as subprocess

**Given** Claude Code is producing output
**When** streaming is enabled
**Then** output appears in the console in real-time via Rich
**And** artifact writes don't block the stream (NFR3)

**Given** the configured Claude Code path doesn't exist
**When** execution is attempted
**Then** LLMError is raised with code "CLAUDE_NOT_FOUND" and suggestion to configure path

**Given** Claude Code execution completes
**When** I inspect the result
**Then** it includes: full content, tool_calls list, tokens_used, duration_ms

**Given** Claude Code respects the `--print` flag
**When** streaming output
**Then** tool calls are captured separately from text content

---

### Story 3.3: Implement Retry Logic with Exponential Backoff

As a developer,
I want transient LLM failures to be retried automatically,
So that temporary issues don't fail the entire run.

**Acceptance Criteria:**

**Given** LLMTimeoutError occurs during execution
**When** retries are configured (default: 3)
**Then** the request is retried with exponential backoff (1s, 2s, 4s)

**Given** LLMRateLimitError occurs during execution
**When** retries are configured
**Then** the request is retried with backoff respecting rate limit headers if available

**Given** all retry attempts fail
**When** the final attempt fails
**Then** the original error is raised with attempt count in the message

**Given** a non-retryable error (e.g., invalid prompt)
**When** error occurs
**Then** no retries are attempted and error is raised immediately

**Given** MockExecutor with configured failures
**When** first two attempts fail and third succeeds
**Then** execution succeeds with attempt_count=3

---

### Story 3.4: Implement Timeout Configuration and Enforcement

As a developer,
I want timeouts enforced on LLM execution,
So that hung processes don't block the pipeline indefinitely.

**Acceptance Criteria:**

**Given** a timeout of 300 seconds in project config
**When** Claude Code execution exceeds 300 seconds
**Then** the process is killed and LLMTimeoutError is raised

**Given** no timeout configured
**When** execution proceeds
**Then** a default timeout of 600 seconds is used

**Given** timeout occurs
**When** error is raised
**Then** it includes elapsed time and configured timeout in the message

**Given** execution completes before timeout
**When** result is returned
**Then** duration_ms is included in the result

---

### Story 3.5: Track Token Usage and Tool Calls

As a developer,
I want token usage and tool calls captured from each LLM execution,
So that I can monitor costs and understand what actions the LLM took.

**Acceptance Criteria:**

**Given** Claude Code execution completes
**When** I inspect LLMResult
**Then** tokens_used contains the token count from the execution

**Given** Claude Code makes tool calls during execution
**When** I inspect LLMResult.tool_calls
**Then** each tool call includes: tool_name, arguments, result_summary

**Given** the LLM execution for a phase
**When** phase completes
**Then** token usage is logged in structured format for aggregation

**Given** an entire run completes
**When** I query total tokens
**Then** it's the sum of all phase executions

---

## Epic 4: State Persistence & Context Management

**Goal:** Persist run state with atomic writes, state snapshots at phase boundaries, and artifact storage to enable reliable resumability. This epic addresses ASR-5 (highest risk score) and ensures data integrity.

### Story 4.1: Create Run Directory Structure

As a developer,
I want a consistent directory structure for each run,
So that all run data is organized and discoverable.

**Acceptance Criteria:**

**Given** a new run is started
**When** the run ID is generated (ULID format)
**Then** directory `.adw/runs/<run_id>/` is created with subdirectories:
  - `artifacts/` (for phase outputs)
  - `logs/` (for logging)
  - `llm/` (for LLM capture)
  - `snapshots/` (for state snapshots)

**Given** the run directory
**When** `context.json` is created
**Then** it contains the serialized RunContext model

**Given** file operations on the run directory
**When** concurrent access is attempted
**Then** filelock prevents corruption (ARCH-7)

**Given** I list `.adw/runs/`
**When** runs exist
**Then** they are sorted by ULID (chronological order)

---

### Story 4.2: Persist Run Context with Atomic Writes

As a developer,
I want run context persisted atomically,
So that power loss or crashes don't corrupt state (ASR-5).

**Acceptance Criteria:**

**Given** a RunContext to be saved
**When** `context_manager.save(context)` is called
**Then** it writes to a temp file first, then atomically renames to `context.json`

**Given** atomic write in progress
**When** the process is killed mid-write
**Then** either the old context.json exists or the new one, never a partial file

**Given** context.json on disk
**When** I call `context_manager.load(run_id)`
**Then** it returns a validated RunContext instance

**Given** corrupted context.json (invalid JSON)
**When** load is attempted
**Then** StateError is raised with code "CONTEXT_CORRUPTED" and suggestion to check snapshots

**Given** context save
**When** fsync is called
**Then** data is guaranteed to be on disk (NFR6)

---

### Story 4.3: Create State Snapshots at Phase Boundaries

As a developer,
I want state snapshots taken before and after each phase,
So that I can debug failures and resume from known-good states.

**Acceptance Criteria:**

**Given** a phase is about to start
**When** the orchestrator enters the phase
**Then** a snapshot is saved to `snapshots/<seq>_pre_<phase>.json`

**Given** a phase completes successfully
**When** the orchestrator exits the phase
**Then** a snapshot is saved to `snapshots/<seq>_post_<phase>.json`

**Given** snapshot creation
**When** I measure duration
**Then** it completes within 500ms (NFR4)

**Given** the snapshots directory
**When** I list snapshots
**Then** they are numbered sequentially (001, 002, etc.)

**Given** a snapshot file
**When** I load it
**Then** it's a complete StateSnapshot model with: context, phase_result, timestamp

---

### Story 4.4: Store and Retrieve Phase Artifacts

As a developer,
I want phase artifacts stored in a predictable location,
So that subsequent phases can access outputs from previous phases.

**Acceptance Criteria:**

**Given** the build phase produces a git diff
**When** the phase completes
**Then** the diff is stored in `artifacts/build/diff.txt`

**Given** a phase produces multiple artifacts
**When** storage completes
**Then** all artifacts are in `artifacts/<phase>/` directory

**Given** artifact storage
**When** I call `context_manager.get_artifact(phase, name)`
**Then** the artifact content is returned

**Given** a non-existent artifact requested
**When** get_artifact is called
**Then** None is returned (not an error)

**Given** artifacts from all phases
**When** the run context is serialized
**Then** it includes artifact paths (not content) for reference

---

### Story 4.5: Handle Interruption and Recovery

As a developer,
I want interruptions (Ctrl+C) to save state cleanly,
So that the run can be resumed without data loss (NFR7).

**Acceptance Criteria:**

**Given** a run is in progress
**When** SIGINT (Ctrl+C) is received
**Then** the current context is saved before exit
**And** the run status is set to "interrupted"

**Given** a run was interrupted mid-phase
**When** resume is attempted
**Then** it starts from the last completed phase boundary (NFR8)

**Given** a run was interrupted during LLM execution
**When** resume is attempted
**Then** the phase is re-executed from the beginning

**Given** an interrupted run
**When** I check status
**Then** it shows "interrupted" with the phase where it stopped

---

## Epic 5: Pipeline Orchestration

**Goal:** Coordinate phase execution in the fixed order (Plan → Build → Verify → Validate → Document), manage phase transitions, and handle artifact flow between phases. This epic brings together hooks, execution, and state management into a complete pipeline.

### Story 5.1: Implement Phase Sequence and Transitions

As a developer,
I want phases executed in the fixed order with clean transitions,
So that the pipeline follows the defined workflow.

**Acceptance Criteria:**

**Given** a full run is requested
**When** the orchestrator executes
**Then** phases run in order: Plan → Build → Verify → Validate → Document

**Given** the orchestrator transitions between phases
**When** I measure transition time (excluding LLM)
**Then** it completes within 1 second (NFR2)

**Given** a phase completes successfully
**When** transitioning to the next phase
**Then** state is persisted before starting the next phase

**Given** a phase fails
**When** the error is not recoverable
**Then** the pipeline stops and run status is set to "failed"

**Given** a phase fails
**When** the error is recoverable
**Then** retry is attempted based on configuration

---

### Story 5.2: Implement PhaseRunner for Single Phase Execution

As a developer,
I want a PhaseRunner that handles all aspects of executing a single phase,
So that phase logic is encapsulated and testable.

**Acceptance Criteria:**

**Given** a phase to execute
**When** `phase_runner.run(phase, context)` is called
**Then** it executes in order: pre-hook → load prompt → LLM execution → post-hook

**Given** a pre-hook produces output
**When** the prompt is loaded
**Then** pre-hook stdout is available as template variable

**Given** LLM execution completes
**When** post-hook runs
**Then** LLM output is available as environment variable

**Given** any step fails
**When** error is raised
**Then** partial state is captured for debugging

**Given** PhaseRunner
**When** I test with MockExecutor
**Then** the full flow can be exercised without Claude Code

---

### Story 5.3: Pass Artifacts Between Phases

As a developer,
I want artifacts from earlier phases available to later phases,
So that the pipeline builds on previous outputs.

**Acceptance Criteria:**

**Given** the Plan phase produces `plan.md` artifact
**When** the Build phase template references `{{artifacts.plan.plan}}`
**Then** the content of plan.md is included

**Given** the Build phase produces `diff.txt` artifact
**When** the Verify phase executes
**Then** the diff is available for evidence gathering

**Given** multiple artifacts from a phase
**When** template references `{{artifacts.build.*}}`
**Then** all artifacts are available by name

**Given** an artifact referenced that doesn't exist
**When** strict mode is enabled
**Then** ConfigError is raised with clear message

---

### Story 5.4: Execute Single Phase in Isolation

As a developer,
I want to execute a single phase without running the full pipeline,
So that I can test or re-run specific phases.

**Acceptance Criteria:**

**Given** command `adw run --phase plan --feature "Add login"`
**When** executed
**Then** only the Plan phase runs

**Given** a single-phase run
**When** previous phase artifacts are needed
**Then** they're loaded from a specified run ID or error is raised

**Given** command `adw run --phase build --from-run <id>`
**When** executed
**Then** artifacts from run <id> are used as input

**Given** single-phase execution
**When** it completes
**Then** artifacts are stored in the current run, not the source run

---

### Story 5.5: Display Phase Progress

As a developer,
I want phase progress displayed in the console,
So that users understand what's happening.

**Acceptance Criteria:**

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

---

## Epic 6: Run Management & Recovery

**Goal:** Enable users to start, resume, abort, and monitor runs through CLI commands. This epic provides the user-facing interface to the orchestration capabilities.

### Story 6.1: Start New Run with Feature Description

As a user,
I want to start a new run by providing a feature description,
So that I can begin AI-assisted development.

**Acceptance Criteria:**

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

---

### Story 6.2: Resume Failed or Interrupted Run

As a user,
I want to resume a run from where it failed or was interrupted,
So that I don't lose progress.

**Acceptance Criteria:**

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

---

### Story 6.3: Check Run Status

As a user,
I want to check the status of any run,
So that I know its current state and outcome.

**Acceptance Criteria:**

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

---

### Story 6.4: List Recent Runs

As a user,
I want to list my recent runs,
So that I can find runs to resume or inspect.

**Acceptance Criteria:**

**Given** command `adw list`
**When** runs exist
**Then** it displays recent runs (default: 10) sorted by creation time

**Given** the run list
**When** displayed
**Then** each entry shows: run_id, feature (truncated), status, started_at

**Given** command `adw list --limit 20`
**When** executed
**Then** up to 20 runs are displayed

**Given** command `adw list --status failed`
**When** executed
**Then** only failed runs are displayed

**Given** no runs exist
**When** list is requested
**Then** message "No runs found" is displayed

---

### Story 6.5: Abort Running Execution

As a user,
I want to abort a running execution,
So that I can stop a stuck or unwanted run.

**Acceptance Criteria:**

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

---

### Story 6.6: Initialize New Project

As a user,
I want to initialize a project with default configuration,
So that I can start using adw in my repository.

**Acceptance Criteria:**

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

---

## Epic 7: Observability & Logging

**Goal:** Provide multi-tier logging (console, raw file, structured JSONL), LLM interaction capture, and debugging commands for state inspection, log search, and export.

### Story 7.1: Implement Multi-Tier Logging System

As a developer,
I want logs written to console, raw file, and structured JSONL,
So that I have appropriate output for different use cases.

**Acceptance Criteria:**

**Given** any log message
**When** logged
**Then** it appears in console (via Rich), raw.log, and logs.jsonl

**Given** console output
**When** TTY is detected
**Then** Rich formatting with colors is used

**Given** console output
**When** non-TTY (piped/redirected)
**Then** plain text without colors/animations (UX-7)

**Given** structured log entry
**When** written to JSONL
**Then** it includes: timestamp, level, category, message, context fields

**Given** the LogCategory enum
**When** logging
**Then** categories include: PHASE, LLM, HOOK, STATE, ERROR, PERFORMANCE

---

### Story 7.2: Configure Verbosity Levels

As a user,
I want to control log verbosity,
So that I see the right amount of detail for my needs.

**Acceptance Criteria:**

**Given** command with `-q` or `--quiet`
**When** executing
**Then** only errors and final results are shown

**Given** command with no flags (default)
**When** executing
**Then** phase progress and key events are shown

**Given** command with `-v` or `--verbose`
**When** executing
**Then** detailed execution info including hook output is shown

**Given** command with `--trace`
**When** executing
**Then** all debug information including template rendering is shown

**Given** verbosity setting
**When** applied
**Then** it affects console output only, not file logs

---

### Story 7.3: Capture LLM Interactions

As a developer,
I want full LLM request/response captured,
So that I can debug and reproduce issues.

**Acceptance Criteria:**

**Given** LLM execution
**When** capturing
**Then** full request (prompt, params) is saved to `llm/<seq>_request.json`

**Given** LLM execution
**When** capturing
**Then** full response (content, tool_calls, tokens) is saved to `llm/<seq>_response.json`

**Given** streaming output
**When** capturing
**Then** raw stream is captured to `llm/<seq>_stream.txt`

**Given** captured LLM interactions
**When** replayed with same prompt
**Then** equivalent behavior can be reproduced (NFR12)

**Given** captured interactions
**When** reviewing
**Then** no API keys or secrets are included (NFR14)

---

### Story 7.4: Implement Log Viewing Commands

As a user,
I want to view and search logs from CLI,
So that I can debug issues without navigating files manually.

**Acceptance Criteria:**

**Given** command `adw logs show <run_id>`
**When** executed
**Then** displays recent log entries from the run

**Given** command `adw logs follow <run_id>`
**When** run is active
**Then** streams new log entries in real-time (FR47)

**Given** command `adw logs search <pattern>`
**When** executed
**Then** searches logs across runs for matching entries (FR48)

**Given** command `adw logs llm <run_id>`
**When** executed
**Then** shows LLM prompts and responses for the run (FR49)

**Given** command `adw logs export <run_id>`
**When** executed
**Then** creates a shareable bundle of logs and state (FR52)

---

### Story 7.5: Implement State Inspection Commands

As a user,
I want to inspect and diff state snapshots,
So that I can debug state-related issues.

**Acceptance Criteria:**

**Given** command `adw logs state <run_id>`
**When** executed
**Then** displays current or final state of the run (FR50)

**Given** command `adw logs state <run_id> --snapshot <seq>`
**When** executed
**Then** displays state at that specific snapshot

**Given** command `adw logs diff <run_id> <phase1> <phase2>`
**When** executed
**Then** shows differences between states at those phases (FR51)

**Given** command `adw logs snapshots <run_id>`
**When** executed
**Then** lists all available snapshots with labels (FR53)

**Given** snapshot inspection
**When** debugging
**Then** enables "time travel" to understand state evolution (NFR13)

---

### Story 7.6: Implement Secret Redaction

As a developer,
I want sensitive data redacted from logs,
So that secrets are never exposed.

**Acceptance Criteria:**

**Given** log message containing API key pattern
**When** logged
**Then** the key is replaced with [REDACTED] (NFR14)

**Given** environment variables with sensitive names
**When** logged
**Then** values are redacted (API_KEY, SECRET, TOKEN, PASSWORD)

**Given** configurable redaction patterns in project.yaml
**When** logging
**Then** custom patterns are also redacted (NFR17)

**Given** a log export
**When** generated
**Then** all redaction rules are applied

---

## Epic 8: Evidence Gathering

**Goal:** Capture platform-appropriate evidence during the Verify phase based on project type (CLI, web, backend), generate evidence manifests, and optimize captured artifacts.

### Story 8.1: Detect Project Platform Type

As a developer,
I want the system to detect the project platform type,
So that appropriate evidence gathering strategies are used.

**Acceptance Criteria:**

**Given** project config with `platform: cli`
**When** evidence gathering starts
**Then** CLI evidence strategy is used

**Given** project config with `platform: web`
**When** evidence gathering starts
**Then** web screenshot strategy is used

**Given** project config with `platform: backend`
**When** evidence gathering starts
**Then** API capture strategy is used

**Given** no platform specified
**When** detection is attempted
**Then** it's inferred from project markers (e.g., package.json with react → web)

**Given** platform cannot be determined
**When** Verify phase runs
**Then** default CLI strategy is used with warning

---

### Story 8.2: Capture CLI Terminal Output

As a developer,
I want terminal output captured for CLI projects,
So that command execution can be verified.

**Acceptance Criteria:**

**Given** CLI platform type
**When** evidence gathering runs
**Then** configured commands are executed and output captured

**Given** commands from project.yaml `evidence.commands`
**When** each command executes
**Then** stdout and stderr are captured to `evidence/<cmd_name>.txt`

**Given** command output
**When** captured
**Then** it includes: command executed, exit code, duration, full output

**Given** command fails (non-zero exit)
**When** capturing
**Then** failure is recorded but doesn't fail the phase

**Given** evidence capture
**When** complete
**Then** exit codes are summarized (X passed, Y failed)

---

### Story 8.3: Capture Web Screenshots

As a developer,
I want screenshots captured for web projects,
So that UI changes can be visually verified.

**Acceptance Criteria:**

**Given** web platform type
**When** evidence gathering runs
**Then** configured routes are loaded and screenshotted

**Given** routes from project.yaml `evidence.routes`
**When** each route is captured
**Then** screenshot is saved to `evidence/screenshots/<route_name>.png`

**Given** screenshot capture
**When** browser automation runs
**Then** it uses headless Playwright or configured tool

**Given** route fails to load
**When** capturing
**Then** error screenshot is captured with error message

**Given** multiple viewport sizes configured
**When** capturing
**Then** screenshots at each viewport are generated

---

### Story 8.4: Capture API Request/Response Pairs

As a developer,
I want API interactions captured for backend projects,
So that endpoint behavior can be verified.

**Acceptance Criteria:**

**Given** backend platform type
**When** evidence gathering runs
**Then** configured API endpoints are called and responses captured

**Given** endpoints from project.yaml `evidence.endpoints`
**When** each endpoint is called
**Then** request and response are saved to `evidence/api/<endpoint_name>.json`

**Given** API call
**When** captured
**Then** it includes: method, url, headers, body, status_code, response_body, duration

**Given** endpoint returns error
**When** capturing
**Then** error response is captured for verification

**Given** authentication required
**When** capturing
**Then** auth headers from config or env vars are used

---

### Story 8.5: Generate Evidence Manifest

As a developer,
I want an evidence manifest linking evidence to plan steps,
So that verification is traceable.

**Acceptance Criteria:**

**Given** evidence gathering completes
**When** manifest is generated
**Then** it's saved to `evidence/manifest.json`

**Given** the manifest
**When** inspected
**Then** it includes: timestamp, platform, evidence_items list

**Given** each evidence item
**When** included in manifest
**Then** it references: plan_step (if linkable), path, type, status (pass/fail/error)

**Given** plan step references
**When** linking
**Then** step IDs from plan.md are matched to evidence items

**Given** manifest
**When** processed by Validate phase
**Then** it's used to assess verification coverage

---

### Story 8.6: Compress and Optimize Evidence

As a developer,
I want captured evidence compressed,
So that storage and transfer are efficient.

**Acceptance Criteria:**

**Given** evidence directory with screenshots
**When** optimization runs
**Then** images are compressed (lossy acceptable for screenshots)

**Given** large terminal outputs
**When** optimization runs
**Then** they're truncated or summarized if over threshold

**Given** all evidence
**When** run completes
**Then** total size is logged for monitoring

**Given** evidence optimization
**When** configured
**Then** max sizes are respected per file type

---

## Epic 9: Git Integration & Documentation

**Goal:** Support git workflows through hooks (feature branches, commits) and generate PR-ready documentation in the Document phase.

### Story 9.1: Create Feature Branch via Pre-Hook

As a user,
I want a feature branch created automatically when a run starts,
So that my work is isolated from the main branch.

**Acceptance Criteria:**

**Given** git integration enabled in project.yaml
**When** run starts
**Then** the bundled pre-hook creates branch `feature/<sanitized-feature-name>`

**Given** feature name "Add user authentication"
**When** branch name is generated
**Then** it becomes `feature/add-user-authentication`

**Given** the branch already exists
**When** pre-hook runs
**Then** it switches to the existing branch instead of failing

**Given** uncommitted changes exist
**When** branch creation is attempted
**Then** HookError is raised with suggestion to commit or stash

**Given** git integration disabled
**When** run starts
**Then** no branch operations occur

---

### Story 9.2: Stage and Commit Changes via Post-Hook

As a user,
I want changes automatically staged and committed after each phase,
So that my work is preserved incrementally.

**Acceptance Criteria:**

**Given** Build phase completes successfully
**When** post-hook runs
**Then** changed files are staged and committed with message "[adw] Build: <feature>"

**Given** commit message template
**When** generating
**Then** it includes: phase name, feature description, run_id reference

**Given** no changes to commit
**When** post-hook runs
**Then** commit is skipped silently (not an error)

**Given** commit fails (e.g., pre-commit hook rejects)
**When** post-hook runs
**Then** HookError is raised with the failure details

**Given** auto-commit disabled in project.yaml
**When** phase completes
**Then** no commit is made

---

### Story 9.3: Capture Git Diff as Artifact

As a developer,
I want the git diff captured as a Build phase artifact,
So that changes can be reviewed and included in PR description.

**Acceptance Criteria:**

**Given** Build phase completes
**When** artifacts are captured
**Then** `git diff HEAD~1` output is saved to `artifacts/build/diff.txt`

**Given** the diff artifact
**When** accessed by Document phase
**Then** it's available as `{{artifacts.build.diff}}`

**Given** diff is very large (>100KB)
**When** capturing
**Then** it's truncated with summary of total lines changed

**Given** no commits made during Build
**When** diff is captured
**Then** staged changes diff is captured instead

---

### Story 9.4: Generate PR Description

As a user,
I want a PR-ready description generated,
So that I can quickly create a pull request.

**Acceptance Criteria:**

**Given** Document phase executes
**When** LLM generates output
**Then** it produces structured PR description with: Summary, Changes, Testing, Screenshots (if applicable)

**Given** the PR description
**When** saved as artifact
**Then** it's at `artifacts/document/pr_description.md`

**Given** evidence manifest from Verify phase
**When** generating PR description
**Then** relevant evidence items are referenced

**Given** run completion panel
**When** displayed
**Then** it includes link to generated PR description artifact

---

### Story 9.5: Support PR Creation Command

As a user,
I want to create a PR directly from the completed run,
So that I can quickly share my work for review.

**Acceptance Criteria:**

**Given** command `adw pr <run_id>`
**When** run is complete
**Then** it opens PR creation with pre-filled title and description

**Given** GitHub CLI (gh) is available
**When** pr command runs
**Then** it uses `gh pr create` with generated description

**Given** gh is not available
**When** pr command runs
**Then** it outputs the description and instructions for manual PR

**Given** run is not complete
**When** pr command is attempted
**Then** ConfigError is raised with "Run must be complete to create PR"

**Given** pr creation succeeds
**When** complete
**Then** PR URL is displayed and stored in run artifacts
