---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
inputDocuments:
  - _bmad-output/analysis/product-brief-adw-sdk-2025-12-30.md
  - docs/arch-high-level.md
  - docs/arch-entry-point.md
  - docs/arch-orchestrator.md
  - docs/arch-command-system.md
  - docs/arch-llm-executor.md
  - docs/arch-logging.md
  - docs/arch-phase-pipeline.md
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 7
workflowType: 'prd'
lastStep: 11
project_name: 'adw-sdk'
user_name: 'Ivo'
date: '2025-12-30'
status: 'complete'
---

# Product Requirements Document - adw-sdk

**Author:** Ivo
**Date:** 2025-12-30

---

## Executive Summary

ADW-SDK (Agentic Development Workflow SDK) is a deterministic, observable pipeline system that transforms AI-assisted software development from ad-hoc prompting into a reliable, auditable workflow.

**Vision:** Developers provide a small prompt describing a feature and receive a fully implemented, validated feature with a detailed PR, evidence, and documentation.

**Core Problem:** Current AI coding approaches lack determinism and robustness. Whether using ad-hoc prompting or prompt-chain systems, developers face inconsistent results, no audit trail, and no way to recover from failures.

**Solution:** A phased pipeline (Plan → Build → Verify → Validate → Document) where:
- **Scripts handle deterministic operations** (git, tests, file I/O, deploys)
- **LLMs handle autonomous reasoning** (planning, code generation, decisions)

This separation creates a robust system with checkpoints, artifacts, and full observability.

### What Makes This Special

1. **Determinism by design** — Predictable operations are scripted, not prompted
2. **Resumability** — Failed runs can be resumed from any phase
3. **Full observability** — State snapshots, LLM stream capture, structured logs enable "time travel" debugging
4. **Pluggable architecture** — Override prompts, hooks, and configuration at project or user level
5. **Artifact continuity** — Each phase produces artifacts that feed the next, creating an audit trail

---

## Project Classification

| Attribute | Value |
|-----------|-------|
| **Technical Type** | CLI Tool / SDK |
| **Domain** | Developer Tools |
| **Complexity** | Medium |
| **Project Context** | Greenfield with pre-designed architecture |
| **Language** | Python 3.13+ |
| **Package Manager** | uv |
| **Target Market** | Solo developers (initial), Teams/Enterprise (future) |
| **Business Model** | Freemium |

---

## Success Criteria

### User Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Feature completion rate | >80% | Runs completing all phases / total runs |
| Time to feature | 50% reduction | Time from prompt to merged PR vs. manual baseline |
| Resume success rate | >90% | Successful resumes / failed runs |
| First-run success | >60% | Runs completing without manual intervention |

### Business Success Metrics

**3-Month Goals:**
- Functional MVP with CLI and core phases (Plan/Build/Verify/Validate/Document)
- 10+ early adopter developers actively using the system
- Validated core value proposition through user feedback

**12-Month Goals:**
- Full integration suite (Linear, GitHub webhooks, GitHub Actions)
- Enterprise-ready with audit logging
- Community contributing custom commands and configurations

### MVP Success Criteria (Go/No-Go)

The MVP is successful when:
1. Users can go from prompt to validated, documented code in a single run
2. Failed runs can be resumed from any phase
3. Issues can be diagnosed from logs and artifacts
4. Users can customize prompts and hooks for their projects

**Decision Point:** 10+ developers, 50+ successful runs, >70% first-run success rate

---

## User Journeys

### Primary Persona: Solo Developer ("Alex")

**Profile:** Mid-to-senior developer working on personal projects or as a solo founder. Uses AI coding tools daily but frustrated by inconsistent results.

**Journey:**

1. **Discovery:** Alex hears about ADW from a dev community or sees a demo of "prompt to PR"
2. **Setup:** Installs via `uv tool install adw`, runs `adw init` in project directory
3. **First Run:** Types `adw run "Add user authentication with OAuth"`, watches phases execute
4. **Success Moment:** Sees validated code with passing tests and auto-generated PR description
5. **Adoption:** Customizes prompts for project conventions, uses for all new features
6. **Advocacy:** Shares experience with other developers

**Key Touchpoints:**
- CLI output showing phase progress
- Artifact inspection for debugging (`adw logs show`)
- Configuration override for customization

### Secondary Persona: Tech Lead ("Jordan")

**Profile:** Engineering lead exploring how to scale AI-assisted development across team.

**Journey:**

1. **Discovery:** Learns about ADW from team member (Alex)
2. **Evaluation:** Reviews observability features and audit capabilities
3. **Pilot:** Deploys for one team with shared configuration
4. **Rollout:** Creates team-wide prompt templates and hooks
5. **Optimization:** Analyzes run metrics to improve prompts

**Key Touchpoints:**
- Shared `.adw/commands/` configuration
- Run logs and artifacts for review (`adw logs llm`, `adw logs state`)
- Success rate metrics across team

### Tertiary Persona: Enterprise Architect ("Morgan")

**Profile:** Platform engineer evaluating tools for governance and compliance.

**Journey:**

1. **Discovery:** Evaluates ADW for enterprise adoption
2. **Compliance Review:** Examines audit logging and state snapshots
3. **Integration:** Connects to enterprise CI/CD and issue tracking
4. **Governance:** Establishes approved prompt templates and validation rules
5. **Scaling:** Rolls out across engineering organization

**Key Touchpoints:**
- Structured logs for compliance (`adw logs export`)
- Webhook integrations (future)
- Configuration inheritance hierarchy

---

## Domain Requirements

### Developer Tools Domain

**Domain Characteristics:**
- Users are technical and CLI-comfortable
- Reliability and predictability are paramount
- Integration with existing developer workflows (git, CI/CD) is essential
- Error messages must be actionable and debugging must be possible

**Domain-Specific Requirements:**

1. **Git Integration:** All code changes must be tracked via git with proper branching
2. **Test Integration:** Must support standard test runners (pytest, jest, etc.)
3. **CI/CD Compatibility:** Artifacts must be usable in standard CI/CD pipelines
4. **IDE Agnostic:** Must work regardless of user's editor choice

**Compliance:** No heavy regulatory compliance (HIPAA, PCI-DSS) required for MVP. Standard security practices apply.

---

## Innovation Patterns

### Core Innovation: Deterministic Wrapper for Non-Deterministic AI

**Pattern:** Separate concerns between what must be deterministic (scripts) and what benefits from AI reasoning (prompts).

**Implementation:**
- Pre-hooks gather context deterministically
- LLM performs reasoning and generation
- Post-hooks validate and capture artifacts deterministically
- Phase transitions are checkpoint-based

### Key Innovations:

1. **Phase-Based Execution:** Fixed pipeline with clear contracts between phases
2. **Artifact Continuity:** Each phase's output feeds the next phase's context
3. **State Snapshots:** Capture full state at key moments for debugging
4. **Command Resolution:** Three-tier override system (project → user → default)
5. **LLM Stream Capture:** Full token-by-token logging for debugging and replay

---

## Project Type Requirements

### CLI Tool / SDK Requirements

**CLI Characteristics:**
- Must be installable via uv (`uv tool install adw`)
- Must provide clear, actionable output
- Must support both interactive and non-interactive (CI) modes
- Must handle interruption gracefully (Ctrl+C)

**SDK Characteristics:**
- Must provide programmatic API for embedding
- Must support custom executors for different LLM backends
- Must allow extension through hooks and plugins

**Specific Requirements:**

1. **Installation:** `uv tool install adw` or `uv add adw` for library usage
2. **Configuration:** YAML-based configuration with sensible defaults
3. **Output:** Streaming console output with phase progress indicators
4. **Exit Codes:** Standard exit codes for CI/CD integration (0=success, non-zero=failure)
5. **Environment:** Support for environment variables for secrets and configuration

---

## MVP Scope

### In Scope (Must Have)

1. **CLI Entry Point**
   - `adw run "<feature>"` — Execute full pipeline
   - `adw run --phase <phase>` — Execute single phase
   - `adw resume <run_id>` — Resume from last successful phase
   - `adw status <run_id>` — Check run status
   - `adw init` — Initialize project configuration

2. **Core Phases**
   - **Plan:** Generate implementation plan from feature request
   - **Build:** Execute plan with LLM-driven code generation
   - **Verify:** Gather evidence that implementation works (screenshots, terminal output, API responses)
   - **Validate:** Run automated checks (tests, linters, type checkers)
   - **Document:** Generate PR description and documentation updates

3. **Command System**
   - Default commands for all MVP phases
   - Project-level overrides via `.adw/commands/`
   - User-level overrides via `~/.config/adw/commands/`
   - Prompt templates with variable substitution
   - Pre/post hooks (shell scripts) for deterministic operations
   - Schema validation for structured LLM output

4. **Claude Code Executor**
   - Primary LLM executor wrapping Claude Code CLI
   - Streaming output with tool call capture
   - Retry logic for transient failures
   - Token usage tracking

5. **Context & Artifact Management**
   - Run context persistence (`.adw/runs/<id>/`)
   - Artifact storage per phase
   - State snapshots at phase boundaries
   - Variable namespace for prompt templates

6. **Observability & Logging**
   - Console output with phase progress (verbosity: quiet/normal/verbose/trace)
   - Raw logs (`.adw/runs/<id>/logs/raw.log`)
   - Structured JSON logs (`.adw/runs/<id>/logs/structured.jsonl`)
   - LLM request/response capture (`.adw/runs/<id>/llm/`)
   - State snapshots (`.adw/runs/<id>/snapshots/`)
   - **Logging Commands:**
     - `adw logs follow <run_id>` — Live log streaming
     - `adw logs show <run_id>` — View historical logs
     - `adw logs search <run_id> <query>` — Search logs
     - `adw logs llm <run_id>` — View LLM interactions
     - `adw logs state <run_id>` — Inspect run state
     - `adw logs diff <run_id>` — Diff between phases
     - `adw logs export <run_id>` — Export for sharing
     - `adw logs snapshots <run_id>` — List state snapshots
     - `adw logs snapshot <run_id> --id <n>` — View specific snapshot

### Out of Scope (Post-MVP)

- Webhook entry points (Linear, GitHub)
- GitHub Action adapter
- Ship phase (deployment automation)
- Custom LLM executors (Aider, Ollama, raw API)
- Enterprise features (SSO, advanced audit logging)
- Team collaboration features
- Command marketplace
- Web dashboard
- Python hooks (shell only for MVP)

---

## Functional Requirements

### Run Management

- FR1: User can start a new run with a feature description via CLI
- FR2: User can resume a previously failed run from the last successful phase
- FR3: User can check the status of any run by ID
- FR4: User can list recent runs with their statuses
- FR5: User can abort a running execution
- FR6: System generates unique run IDs for tracking

### Phase Execution

- FR7: System executes phases in fixed order (Plan → Build → Verify → Validate → Document)
- FR8: System runs pre-hooks before LLM execution in each phase
- FR9: System runs post-hooks after LLM execution in each phase
- FR10: System captures artifacts at the end of each phase
- FR11: System makes previous phase artifacts available to subsequent phases
- FR12: User can execute a single phase in isolation

### Verify Phase (Evidence Gathering)

- FR13: System gathers platform-appropriate evidence based on project type
- FR14: For CLI projects: System captures terminal output for key commands
- FR15: For web projects: System captures screenshots of key routes
- FR16: For backend projects: System captures API request/response pairs
- FR17: System generates evidence manifest linking evidence to plan steps
- FR18: System compresses and optimizes captured evidence

### Command System

- FR19: System resolves commands using three-tier hierarchy (project → user → default)
- FR20: User can override any command file at project level
- FR21: User can override any command file at user level
- FR22: System renders prompt templates with variable substitution
- FR23: System validates LLM output against schema when provided
- FR24: System executes pre-hooks and captures stdout for prompt context
- FR25: System executes post-hooks for validation and cleanup

### LLM Execution

- FR26: System invokes Claude Code CLI for LLM execution
- FR27: System streams LLM output in real-time to console
- FR28: System captures tool calls made by the LLM
- FR29: System retries on transient failures with exponential backoff
- FR30: System respects timeout configuration
- FR31: System tracks token usage for each execution

### Project Configuration

- FR32: User can initialize a new project with `adw init`
- FR33: System creates `.adw/` directory with default configuration
- FR34: User can configure project metadata (name, language, framework, platform)
- FR35: User can configure test and build commands
- FR36: System loads configuration from `.adw/project.yaml`

### Context & State

- FR37: System persists run context to `.adw/runs/<id>/`
- FR38: System creates state snapshots at phase boundaries
- FR39: System stores artifacts in `.adw/runs/<id>/artifacts/<phase>/`
- FR40: User can inspect any artifact from a run
- FR41: System maintains run context across interruptions

### Observability & Logging

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

### Git Integration

- FR54: Pre-hooks can create feature branches
- FR55: Post-hooks can stage and commit changes
- FR56: System captures git diff as build artifact
- FR57: Document phase generates PR-ready description

---

## Non-Functional Requirements

### Performance

- NFR1: CLI startup time shall be under 2 seconds
- NFR2: Phase transitions shall complete within 1 second (excluding LLM time)
- NFR3: Artifact writes shall not block LLM streaming
- NFR4: State snapshots shall complete within 500ms

### Reliability

- NFR5: System shall gracefully handle LLM API failures with retry
- NFR6: System shall persist state before each phase transition
- NFR7: System shall recover from interruption (Ctrl+C) without data loss
- NFR8: Resume shall succeed if the previous run reached a phase boundary
- NFR9: System shall validate all configuration before starting a run

### Observability

- NFR10: All errors shall include actionable error messages
- NFR11: Debug logs shall include sufficient context to diagnose issues
- NFR12: LLM interactions shall be fully reproducible from logs
- NFR13: State snapshots shall enable "time travel" debugging

### Security

- NFR14: System shall not log API keys or secrets
- NFR15: System shall support environment variables for sensitive configuration
- NFR16: Hooks shall execute with repository-scoped permissions only
- NFR17: System shall redact sensitive patterns from logs (configurable)

### Usability

- NFR18: CLI shall provide helpful error messages for common mistakes
- NFR19: Default configuration shall work for common project types
- NFR20: Documentation shall include quickstart and common use cases
- NFR21: CLI help shall be discoverable via `--help` on all commands

### Maintainability

- NFR22: Codebase shall have >80% test coverage for core logic
- NFR23: All public APIs shall have type hints
- NFR24: Architecture shall support adding new phases without core changes
- NFR25: Executor interface shall support adding new LLM backends

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package Manager | uv | Fast, modern Python packaging |
| Python Version | 3.13+ | Latest stable, modern features |
| Hook Language | Shell scripts | Simple, universal, no Python dependency in hooks |
| Resume Granularity | Phase-level only | Simpler implementation, phase boundaries are natural checkpoints |
| Async Model | TBD | To be decided during architecture |

---

*PRD completed on 2025-12-30. Updated with Verify phase, uv packaging, adw naming, and full logging commands.*
