# Epic 5: Pipeline Orchestration

**Goal:** Coordinate phase execution in the fixed order (Plan → Build → Verify → Validate → Document), manage phase transitions, and handle artifact flow between phases. This epic brings together hooks, execution, and state management into a complete pipeline.

## Story 5.1: Implement Phase Sequence and Transitions

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

## Story 5.2: Implement PhaseRunner for Single Phase Execution

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

## Story 5.3: Pass Artifacts Between Phases

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

## Story 5.4: Execute Single Phase in Isolation

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

## Story 5.5: Display Phase Progress

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

## Dependency Analysis

### Story Dependencies

| Story | Depends On | Blocks | Can Parallel With |
|-------|------------|--------|-------------------|
| 5.1 | Epic 4 (all stories) | 5.2, 5.4, 5.5 | None |
| 5.2 | 5.1, Epic 2, Epic 3 | 5.3, 5.4 | None |
| 5.3 | 5.2 | 5.4 | 5.5 |
| 5.4 | 5.1, 5.2, 5.3 | None | None |
| 5.5 | 5.1 | None | 5.3 |

### Execution Waves

```
Wave 1: [5.1] Foundation - Phase Sequence and Transitions
           │
           ├──────────────────┐
           │                  │
           ▼                  ▼
Wave 2: [5.2]              [5.5]
        PhaseRunner        Progress Display
           │                  │
           │                  │ (parallel)
           ▼                  │
Wave 3: [5.3] ─────────────┘
        Artifact Passing
           │
           ▼
Wave 4: [5.4]
        Single Phase Execution
```

### Parallelization Flowchart

```
                    ┌─────────────────────────────────────┐
                    │              [5.1]                  │
                    │   Implement Phase Sequence and     │
                    │          Transitions               │
                    │     (Foundation - Orchestrator)    │
                    └─────────────────┬───────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
        ┌────────────────────────┐    ┌────────────────────────┐
        │         [5.2]          │    │         [5.5]          │
        │   PhaseRunner for      │    │    Display Phase       │
        │  Single Phase Exec     │    │       Progress         │
        │ (Core Phase Logic)     │    │   (UX Enhancement)     │
        └───────────┬────────────┘    └────────────────────────┘
                    │                              ▲
                    │                              │ (can start
                    ▼                              │  in parallel)
        ┌────────────────────────┐                 │
        │         [5.3]          │─────────────────┘
        │   Pass Artifacts       │
        │   Between Phases       │
        │ (Template Variables)   │
        └───────────┬────────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │         [5.4]          │
        │   Execute Single       │
        │  Phase in Isolation    │
        │ (--phase, --from-run)  │
        └────────────────────────┘
```

### Critical Path

**Minimum Sequential Path:** 5.1 → 5.2 → 5.3 → 5.4

**Parallelizable:** Story 5.5 can be developed in parallel with 5.2 and 5.3

### Estimated Story Points

| Story | Complexity | Notes |
|-------|------------|-------|
| 5.1 | Medium | Core orchestration, retry logic |
| 5.2 | Medium | Hook/LLM coordination |
| 5.3 | Small | Template variable extension |
| 5.4 | Medium | CLI flags, artifact loading |
| 5.5 | Small | Rich display components |

---

## Story Files

- [5.1 - Phase Sequence and Transitions](../implementation-artifacts/5-1-implement-phase-sequence-and-transitions.md)
- [5.2 - PhaseRunner for Single Phase Execution](../implementation-artifacts/5-2-implement-phase-runner-for-single-phase-execution.md)
- [5.3 - Pass Artifacts Between Phases](../implementation-artifacts/5-3-pass-artifacts-between-phases.md)
- [5.4 - Execute Single Phase in Isolation](../implementation-artifacts/5-4-execute-single-phase-in-isolation.md)
- [5.5 - Display Phase Progress](../implementation-artifacts/5-5-display-phase-progress.md)

---
