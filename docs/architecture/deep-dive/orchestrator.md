# Orchestrator

The `Orchestrator` (`src/adw/core/orchestrator.py`) is the central coordinator for the ADW pipeline. It manages execution of phases in a fixed sequence: **Plan → Build → Validate → Document → Ship**.

## Core Responsibilities

| Responsibility | How |
|----------------|-----|
| Phase sequencing | Executes phases in order via `PHASE_SEQUENCE` |
| State persistence | Saves `RunContext` after every state change (enables resume) |
| Snapshots | Creates pre/post snapshots for debugging |
| Retry logic | Exponential backoff for recoverable errors |
| Graceful shutdown | Handles Ctrl+C/SIGTERM via `InterruptionHandler` |
| Worktree isolation | Optional git worktree per run (Story 10.1) |

## Key Components

```
Orchestrator
├── context_manager      → Persists RunContext to disk
├── snapshot_manager     → Creates debugging snapshots
├── artifact_manager     → Stores phase outputs
├── run_directory_manager → Creates directory structure
├── index_manager        → Global execution tracking
├── interruption_handler → Graceful shutdown
└── _phase_runner        → Delegates actual phase execution
```

## Main Methods

| Method | Purpose |
|--------|---------|
| `run(feature)` | Full pipeline execution (plan → build → validate → document → ship) |
| `run_single_phase(phase, feature)` | Execute one phase only |
| `resume(run_id)` | Continue a failed/interrupted run |

## Phase Execution Flow

```
run()
 ├── Generate run ID (ULID)
 ├── Create worktree (if enabled)
 ├── Create initial RunContext
 └── For each phase in PHASE_SEQUENCE:
      ├── Check shutdown signal
      ├── Update context.current_phase → persist
      ├── Create pre-phase snapshot
      ├── Execute phase with retry (up to 3x)
      ├── Create post-phase snapshot
      └── Update phase_history → persist
```

## Error Handling

| Error Type | Behavior |
|------------|----------|
| `ADWError` (recoverable) | Retry up to 3x with exponential backoff |
| `ADWError` (non-recoverable) | Fail immediately, persist state |
| `ShutdownRequested` | Graceful exit, state preserved |

## Design Notes

**PhaseRunnerProtocol**: The orchestrator depends on a `Protocol` rather than the concrete `PhaseRunner` class. This provides module decoupling and testability (mock injection).

**Setter Injection**: `set_phase_runner()` is used instead of constructor injection. This is historical — there's no actual circular dependency, so constructor injection would be cleaner.
