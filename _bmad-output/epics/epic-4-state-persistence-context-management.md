# Epic 4: State Persistence & Context Management

**Goal:** Persist run state with atomic writes, state snapshots at phase boundaries, and artifact storage to enable reliable resumability. This epic addresses ASR-5 (highest risk score) and ensures data integrity.

## Story 4.1: Create Run Directory Structure

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

## Story 4.2: Persist Run Context with Atomic Writes

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

## Story 4.3: Create State Snapshots at Phase Boundaries

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

## Story 4.4: Store and Retrieve Phase Artifacts

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

## Story 4.5: Handle Interruption and Recovery

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
