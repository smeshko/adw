# Epic 12: Worktree Isolation

**Goal:** Enable concurrent workflow execution via git worktrees with deterministic port allocation, allowing up to 15 simultaneous ADW runs.

**Priority:** P2 (MVP)
**Dependencies:** Epic 4 (State Persistence), Epic 5 (Pipeline Orchestration)

---

## Story 12.1: Worktree Creation and Lifecycle

As a developer,
I want each ADW run to execute in an isolated git worktree,
So that concurrent runs don't interfere with each other or my working directory.

**Acceptance Criteria:**

**Given** a new run starts
**When** orchestrator initializes
**Then** a worktree is created at `trees/<run_id>/` from current branch

**Given** worktree creation
**When** `git worktree add` executes
**Then** a new branch `adw/<run_id>` is created for the worktree

**Given** run completes successfully
**When** cleanup runs
**Then** worktree is removed via `git worktree remove`

**Given** run fails
**When** cleanup runs
**Then** worktree is preserved for debugging (configurable)

**Given** `--no-worktree` flag
**When** run starts
**Then** execution happens in current directory (legacy mode)

---

## Story 12.2: Worktree Directory Structure

As a developer,
I want worktrees organized predictably,
So that I can find and inspect them easily.

**Acceptance Criteria:**

**Given** worktree creation
**When** path is determined
**Then** it's created at `<project-root>/trees/<run_id>/`

**Given** the trees directory
**When** it doesn't exist
**Then** it's created with `.gitignore` entry added to project

**Given** worktree structure
**When** created
**Then** it includes full project copy with `.adw/` directory

**Given** `.adw/runs/<run_id>/` in worktree
**When** run executes
**Then** all artifacts are stored in the worktree's `.adw/` directory

**Given** run completion
**When** artifacts need preservation
**Then** key artifacts are copied to main `.adw/runs/<run_id>/` before worktree removal

---

## Story 12.3: Port Allocation System

As a developer,
I want deterministic port allocation per run,
So that concurrent runs don't have port conflicts.

**Acceptance Criteria:**

**Given** a run with slot number N (0-14)
**When** ports are allocated
**Then** backend port = 9100 + N, frontend port = 9200 + N

**Given** run starts
**When** slot is assigned
**Then** slot is determined by hashing run_id modulo 15

**Given** port allocation
**When** `.ports.env` is generated
**Then** it contains: `BACKEND_PORT=91XX`, `FRONTEND_PORT=92XX`

**Given** a phase needs ports
**When** environment is set up
**Then** `.ports.env` is sourced or variables are injected

**Given** port is already in use
**When** allocation occurs
**Then** next available slot is tried (up to 3 attempts)

---

## Story 12.4: Concurrent Run Management

As a developer,
I want to run multiple ADW workflows simultaneously,
So that I can process multiple features in parallel.

**Acceptance Criteria:**

**Given** multiple `adw run` commands
**When** executed in parallel
**Then** each gets its own worktree and port allocation

**Given** maximum concurrent runs (15)
**When** a 16th run is attempted
**Then** error is raised: "Maximum concurrent runs reached. Use `adw list --running` to see active runs."

**Given** command `adw list --running`
**When** executed
**Then** shows all currently executing runs with their worktree paths and ports

**Given** orphaned worktrees (from crashed runs)
**When** `adw cleanup` is executed
**Then** stale worktrees are removed after confirmation

---

## Story 12.5: Worktree Context in Phases

As a developer,
I want phases to execute in the worktree context,
So that file operations happen in the isolated environment.

**Acceptance Criteria:**

**Given** a phase executes
**When** LLM is invoked
**Then** working directory is set to worktree path

**Given** hooks execute
**When** environment is set up
**Then** `ADW_WORKTREE_PATH` is available

**Given** template variables
**When** rendered
**Then** `{{worktree_path}}` resolves to absolute worktree path

**Given** artifact paths
**When** stored in context
**Then** they're relative to worktree root

---

## Story 12.6: Worktree Branch Management

As a developer,
I want worktree branches managed automatically,
So that my git history stays clean.

**Acceptance Criteria:**

**Given** worktree creation
**When** branch is created
**Then** it's named `adw/<run_id>` (e.g., `adw/01HQXK5P3Z7V8R2M4N6T9W1Y3C`)

**Given** run completes with PR created
**When** cleanup runs
**Then** branch is preserved (needed for PR)

**Given** run fails or is aborted
**When** cleanup runs with `--delete-branch`
**Then** worktree AND branch are removed

**Given** run aborted
**When** cleanup runs without flag
**Then** worktree removed, branch preserved for debugging

---

## Configuration

```yaml
# .adw/project.yaml
worktree:
  enabled: true                    # Enable worktree isolation
  base_dir: "trees"                # Relative to project root
  preserve_on_failure: true        # Keep worktree on failure for debugging
  max_concurrent: 15               # Maximum simultaneous runs
  port_range:
    backend_start: 9100
    frontend_start: 9200
  cleanup_on_success: true         # Auto-remove worktree on success
```

---

## Architecture Notes

**Directory Layout:**
```
my-project/
├── .adw/
│   ├── project.yaml
│   └── runs/
│       └── 01HQ.../           # Preserved artifacts
├── trees/                      # Worktrees directory
│   ├── .gitignore             # Contains: *
│   ├── 01HQXK5.../            # Active worktree
│   │   ├── (full project copy)
│   │   ├── .adw/
│   │   │   └── runs/01HQXK5.../
│   │   └── .ports.env
│   └── 01HQXK6.../            # Another concurrent run
└── src/
```

**Port Allocation Table:**
| Slot | Backend Port | Frontend Port |
|------|--------------|---------------|
| 0 | 9100 | 9200 |
| 1 | 9101 | 9201 |
| ... | ... | ... |
| 14 | 9114 | 9214 |

---

## Dependency Flowchart

```
Story 12.1 (Worktree Creation)
       │
       ├──▶ Story 12.2 (Directory Structure)
       │
       ├──▶ Story 12.3 (Port Allocation)
       │
       └──▶ Story 12.6 (Branch Management)
              │
              ▼
Story 12.4 (Concurrent Management)
       │
       ▼
Story 12.5 (Worktree Context in Phases)
```

---
