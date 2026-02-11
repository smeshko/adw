# Requirements Inventory

## Functional Requirements

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

## NonFunctional Requirements

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

## Additional Requirements

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

## FR Coverage Map

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
