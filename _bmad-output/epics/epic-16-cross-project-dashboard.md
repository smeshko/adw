# Epic 16: Cross-Project Dashboard (Post-MVP)

**Goal:** Enable users to view and analyze runs across all their ADW-enabled projects from a single interface, with analytics, token/cost tracking, and dashboard views.

**Priority:** Post-MVP

**Dependencies:** Epics 1-7 (core functionality must be stable)

**Architecture Reference:** See `architecture.md` → "Future Enhancement: Cross-Project Run Visibility & Dashboard"

**Last Updated:** 2026-01-19 (revised to reflect current implementation)

---

## Existing Infrastructure (Already Implemented)

Before detailing stories, it's important to acknowledge what already exists:

### IndexManager (`src/adw/core/index_manager.py`)
- **Location:** `~/.adw/index.jsonl` (JSONL format, append-only)
- **Capabilities:**
  - `register_run(context, project_path)` - Registers new runs
  - `update_run(run_id, **updates)` - Updates run status
  - `get_recent_runs(limit, project_path, status)` - Queries with filters
  - Auto-archival when >10,000 entries to `~/.adw/index-archive/YYYY-MM.jsonl`

### IndexEntry Model (`src/adw/models/index.py`)
```python
class IndexEntry(BaseModel):
    run_id: str                    # ULID identifier
    project_path: str              # Absolute path to project
    project_name: str              # Directory name (derived)
    feature_description: str       # Feature request
    started_at: datetime           # UTC timestamp
    completed_at: datetime | None
    status: Literal["running", "completed", "failed", "interrupted", "aborted"]
    phase_reached: str | None
    phases_completed: list[str]
```

### What's Missing (Epic 16 Scope)
1. **CLI commands** to query the global index (`adw global list`, etc.)
2. **Project registry** for explicit project management (+ init wizard integration)
3. **Statistics and analytics** commands
4. **TUI dashboard** for visual monitoring

**Dropped from scope (2026-01-25):**
- ~~Export capabilities~~ - Not needed
- ~~RunContext enhancements (tags/username)~~ - Not needed
- ~~Index performance optimization~~ - Not needed

---

## Story 16.1: Project Registry

As a user,
I want to explicitly register and manage projects with ADW,
So that I can control which projects appear in cross-project views.

**Acceptance Criteria:**

**Given** command `adw register` in a project directory
**When** executed
**Then** the project path and name are added to `~/.adw/projects.yaml`

**Given** command `adw register --name "my-api"`
**When** executed
**Then** the custom name is used instead of directory name

**Given** a project already registered
**When** `adw register` is run again
**Then** the registration is updated (not duplicated)

**Given** command `adw unregister`
**When** executed
**Then** the project is removed from the registry

**Given** command `adw projects`
**When** executed
**Then** all registered projects are listed with their paths and run counts

**Given** command `adw projects --discover`
**When** executed
**Then** unique projects from `~/.adw/index.jsonl` are listed (auto-discovery)

### Init Wizard Integration

**Given** user runs `adw init` wizard
**When** the GLOBAL_REGISTRY step is reached (after BASICS step)
**Then** user is prompted: "Register this project in ADW global dashboard? (Y/n)"

**Given** user confirms registration in wizard
**When** wizard completes
**Then** project is automatically added to `~/.adw/projects.yaml`

**Given** user declines registration in wizard
**When** wizard completes
**Then** project is NOT added to registry (can be added later via `adw register`)

**Given** user confirms registration
**When** prompted for custom name
**Then** user can optionally provide a display name (default: directory name from BASICS step)

**Technical Notes:**
- Registry file: `~/.adw/projects.yaml`
- Schema: `{projects: [{path, name, registered_at}]}`
- Auto-discovery via IndexManager as fallback (no explicit registration required)
- Registration is optional—`adw global` commands work with index alone

**Implementation:**
- New file: `src/adw/core/project_registry.py`
- CLI: Add commands to `src/adw/cli/app.py`
- New wizard step: `src/adw/cli/wizard/global_registry.py`
- Update `WizardStep` enum in `src/adw/cli/wizard/flow.py` to add `GLOBAL_REGISTRY` after `BASICS`

---

## Story 16.2: Global Run List

As a user,
I want to list runs across all projects,
So that I can see my development activity in one place.

**Acceptance Criteria:**

**Given** command `adw global list`
**When** executed
**Then** runs from all projects in the index are displayed, sorted by time (newest first)

**Given** command `adw global list --project my-api`
**When** executed
**Then** only runs matching that project name are shown

**Given** command `adw global list --status failed`
**When** executed
**Then** only failed runs across all projects are shown

**Given** command `adw global list --since 7d`
**When** executed
**Then** only runs from the last 7 days are shown

**Given** the run list
**When** displayed
**Then** each entry shows: run_id, project_name, feature (truncated), status, duration, started_at

**Technical Notes:**
- **Builds on existing:** `IndexManager.get_recent_runs()` already supports `project_path` and `status` filters
- Add `--since` filter by parsing ULID timestamp or `started_at` field
- Combine filters: `--project` + `--status` + `--since`
- Consider pagination with `--limit` and `--offset` for large result sets

**Implementation:**
- New CLI group: `src/adw/cli/global_commands.py`
- Register via `app.add_typer(global_app, name="global")`

---

## Story 16.3: Cross-Project Statistics

As a user,
I want to see aggregate statistics across all my projects,
So that I can understand my overall ADW usage patterns.

**Acceptance Criteria:**

**Given** command `adw global stats`
**When** executed
**Then** displays aggregate metrics across all projects

**Given** the statistics output
**When** displayed
**Then** includes:
- Total runs (all time, this week, today)
- Success rate overall and per project
- Average run duration
- Total token usage (from LLM response files)
- Estimated cost (based on model pricing)

**Given** command `adw global stats --project my-api`
**When** executed
**Then** shows statistics for that project only

**Given** command `adw global stats --format json`
**When** executed
**Then** outputs machine-readable JSON for integration

**Technical Notes:**
- Token data from `.adw/runs/<run_id>/llm/*_response.json` files:
  ```json
  {
    "stats": {
      "input_tokens": 1234,
      "output_tokens": 5678,
      "duration_ms": 45000
    }
  }
  ```
- Cost estimation requires model pricing table (configurable in `~/.adw/config.yaml`)
- Cache stats to `~/.adw/stats-cache.json` with TTL (invalidate on new runs)
- Requires reading LLM files from project directories—only works for accessible projects

**Implementation:**
- New: `src/adw/core/stats_aggregator.py`
- CLI: `adw global stats` command

---

## ~~Story 16.4: Index Performance Optimization~~ [DROPPED]

> **Status:** DROPPED (2026-01-25) - Performance optimization not needed for current scope.

~~As a power user with thousands of runs,
I want queries to remain fast,
So that cross-project commands don't slow down my workflow.~~

**Acceptance Criteria:**

**Given** the existing JSONL index at `~/.adw/index.jsonl`
**When** it contains >5,000 entries
**Then** queries should complete in <500ms

**Given** command `adw global index info`
**When** executed
**Then** shows index stats: entry count, file size, archive count

**Given** command `adw global index rebuild`
**When** executed
**Then** the index is rebuilt from all registered project run directories

**Given** index file is corrupted or missing entries
**When** detected during query
**Then** warning is shown with suggestion to rebuild

**Technical Notes:**
- **Current implementation:** JSONL at `~/.adw/index.jsonl` (already exists)
- **Archival:** Already implemented—archives to `~/.adw/index-archive/YYYY-MM.jsonl` when >10,000 entries
- **Future option:** Migrate to SQLite if JSONL becomes a bottleneck at scale
- **Rebuild:** Scan all project `.adw/runs/*/context.json` files to reconstruct index

**Implementation:**
- Enhance `IndexManager` with `get_stats()` and `rebuild_from_projects()` methods
- CLI: `adw global index info` and `adw global index rebuild`

**Note:** This story is **optional**—the current JSONL implementation is sufficient for most users. Only implement if performance issues are observed at scale.

---

## Story 16.5: TUI Dashboard

As a user,
I want a terminal dashboard showing my ADW activity,
So that I can monitor runs visually.

**Acceptance Criteria:**

**Given** command `adw global dashboard`
**When** executed
**Then** a Rich-based TUI dashboard is displayed

**Given** the dashboard
**When** displayed
**Then** shows:
- Summary panel (total runs, success rate, active runs)
- Recent runs table with status indicators
- Per-project breakdown
- Token/cost summary (if data available)

**Given** active runs exist
**When** dashboard is open
**Then** status updates periodically (polling the index)

**Given** keyboard navigation
**When** user presses arrow keys
**Then** can navigate between runs and view details

**Given** command `adw global dashboard --refresh 5`
**When** executed
**Then** dashboard refreshes every 5 seconds

**Technical Notes:**
- Built with Rich `Live` and `Layout` components
- Keyboard handling via Rich or `prompt_toolkit`
- Consider `textual` for more advanced TUI if needed later
- Poll `~/.adw/index.jsonl` for updates (lightweight, already JSONL streaming)

**Implementation:**
- New: `src/adw/cli/dashboard.py`
- Dependency: `rich` (already in project)

### Visual Design Reference (ASCII Mockups)

#### Main Dashboard View
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                              ADW GLOBAL DASHBOARD                                    [Q]uit    ┃
┃                              ════════════════════                                    [R]efresh ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃   ╭─────────────────╮  ╭─────────────────╮  ╭─────────────────╮  ╭─────────────────╮           ┃
┃   │   TOTAL RUNS    │  │   THIS WEEK     │  │     TODAY       │  │  SUCCESS RATE   │           ┃
┃   │                 │  │                 │  │                 │  │                 │           ┃
┃   │      1,247      │  │       89        │  │       12        │  │     94.3%       │           ┃
┃   │                 │  │                 │  │                 │  │   ████████░░    │           ┃
┃   ╰─────────────────╯  ╰─────────────────╯  ╰─────────────────╯  ╰─────────────────╯           ┃
┃                                                                                                ┃
┃   AVG DURATION: 4m 23s    │    TOTAL TOKENS: 2.4M    │    EST. COST: $47.82                    ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ RECENT RUNS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃  RUN ID      PROJECT          FEATURE                      STATUS       DURATION    STARTED   ┃
┃  ─────────────────────────────────────────────────────────────────────────────────────────────  ┃
┃  a7f3c2e1    adw-final        Add user authentication...   ● RUNNING       2m 14s   just now  ┃
┃  b8e4d3f2    myapp-backend    Fix database connection...   ✓ COMPLETED     5m 32s   5 min ago ┃
┃  c9f5e4a3    adw-final        Implement caching layer...   ✓ COMPLETED     3m 18s   12 min ago┃
┃  d0a6f5b4    frontend-ui      Update navigation compo...   ✗ FAILED        1m 45s   18 min ago┃
┃  e1b7a6c5    myapp-backend    Add rate limiting middl...   ✓ COMPLETED     4m 52s   25 min ago┃
┃  f2c8b7d6    adw-final        Refactor error handling...   ⊘ INTERRUPTED   6m 03s   32 min ago┃
┃                                                                                                ┃
┃                          [↑/↓] Navigate   [Enter] View Details   [Page↓] More                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━ PER-PROJECT BREAKDOWN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃  PROJECT            PATH                              RUNS    SUCCESS    TOKENS     COST       ┃
┃  ─────────────────────────────────────────────────────────────────────────────────────────────  ┃
┃  adw-final          ~/Developer/Projects/adw/adw...    423      96.2%     892K    $18.24       ┃
┃  myapp-backend      ~/Developer/Projects/myapp-b...    512      93.8%     1.1M    $21.45       ┃
┃  frontend-ui        ~/Developer/Projects/frontend...   312      91.7%     412K     $8.13       ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Last refreshed: 2s ago                                                   Auto-refresh: 30s [P]ause
```

#### Filtered by Project View
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━ PROJECT: adw-final ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃   Path: /Users/dev/Projects/adw/adw-final                                       [Esc] Clear   ┃
┃                                                                                                ┃
┃   ╭──────────────╮  ╭──────────────╮  ╭──────────────╮  ╭──────────────╮  ╭──────────────╮     ┃
┃   │    RUNS      │  │  THIS WEEK   │  │    TODAY     │  │   SUCCESS    │  │  AVG DURATION│     ┃
┃   │     423      │  │      34      │  │      5       │  │    96.2%     │  │    3m 47s    │     ┃
┃   ╰──────────────╯  ╰──────────────╯  ╰──────────────╯  ╰──────────────╯  ╰──────────────╯     ┃
┃                                                                                                ┃
┃   TOKENS: 892,341 (input: 743,892 / output: 148,449)         EST. COST: $18.24                 ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ STATUS BREAKDOWN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃   ✓ COMPLETED     407  ████████████████████████████████████████████████░░░░░░   96.2%          ┃
┃   ✗ FAILED          9  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    2.1%          ┃
┃   ⊘ INTERRUPTED     6  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    1.4%          ┃
┃   ⦻ ABORTED         1  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0.2%          ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### Empty State
```
                         ╭────────────────────────────────────────────────╮
                         │                                                │
                         │            No Projects Registered              │
                         │                                                │
                         │   ┌────────────────────────────────────────┐   │
                         │   │                                        │   │
                         │   │     Run `adw init` in any project      │   │
                         │   │     directory to register it and       │   │
                         │   │     start tracking runs globally.      │   │
                         │   │                                        │   │
                         │   │     Or use: adw register               │   │
                         │   │                                        │   │
                         │   └────────────────────────────────────────┘   │
                         │                                                │
                         ╰────────────────────────────────────────────────╯
```

#### Active Runs State
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━ ACTIVE RUNS (2) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                ┃
┃  ● a7f3c2e1 │ adw-final      │ Add user authentication flow...      │ ◐  2m 14s │ 12.4K tok   ┃
┃  ● x2y9z8w7 │ myapp-backend  │ Implement webhook endpoint for...    │ ◑  0m 47s │  3.1K tok   ┃
┃                                                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### Keyboard Shortcuts
```
  NAVIGATION                      ACTIONS                         VIEWS
  ──────────────────────────────────────────────────────────────────────────
  ↑/k      Move up                Enter    View run details       1    Summary
  ↓/j      Move down              R        Refresh now            2    Runs list
  PgUp     Page up                P        Pause/resume refresh   3    Projects
  PgDn     Page down              /        Filter by project
  Home     Go to top              Esc      Clear filter
  End      Go to bottom           Q        Quit dashboard
```

#### Status Indicators
```
  ● RUNNING      Active ADW session in progress (yellow, animated spinner)
  ✓ COMPLETED    Successfully finished (green)
  ✗ FAILED       Terminated with error (red)
  ⊘ INTERRUPTED  User cancelled mid-run (orange)
  ⦻ ABORTED      System/crash termination (dim red)
```

---

## ~~Story 16.6: Run Context Enhancements~~ [DROPPED]

> **Status:** DROPPED (2026-01-25) - Tags and username tracking not needed.

~~As a developer,
I want additional metadata captured per run,
So that cross-project analytics are more useful.~~

**Acceptance Criteria:**

**Given** command `adw run "feature" --tag urgent --tag backend`
**When** executed
**Then** tags are stored in `RunContext.tags`

**Given** the system can detect current user
**When** a run starts
**Then** username is stored in `RunContext.initiated_by`

**Given** cross-project queries
**When** filtering by tag (`adw global list --tag urgent`)
**Then** only runs with matching tags are returned

**Given** `.adw/project.yaml` contains `project_name: "my-api"`
**When** a run starts
**Then** explicit project name is used instead of directory name

**Technical Notes:**

Add to `src/adw/models/context.py` (RunContext):
```python
tags: list[str] = Field(
    default_factory=list,
    description="User-defined tags for categorization"
)
initiated_by: str | None = Field(
    default=None,
    description="Username who initiated the run"
)
```

Add to `IndexEntry` model:
```python
tags: list[str] = Field(default_factory=list)
initiated_by: str | None = None
```

- `initiated_by` from `os.getlogin()` or `$USER` environment variable
- Tags are free-form strings, no validation required
- **Note:** `project_name` already exists in `IndexEntry` (derived from directory). For explicit naming, add optional `project_name` field to `.adw/project.yaml` schema.

**Implementation:**
- Update: `src/adw/models/context.py`
- Update: `src/adw/models/index.py`
- Update: `src/adw/core/index_manager.py` (pass tags through)
- Update: CLI `adw run` to accept `--tag` flags

---

## ~~Story 16.7: Export and Reporting~~ [DROPPED]

> **Status:** DROPPED (2026-01-25) - Export functionality not needed.

~~As a user,
I want to export run data for external analysis,
So that I can create custom reports or integrate with other tools.~~

**Acceptance Criteria:**

**Given** command `adw global export --format csv`
**When** executed
**Then** all run data is exported as CSV to stdout

**Given** command `adw global export --format json`
**When** executed
**Then** all run data is exported as JSON array

**Given** command `adw global export --since 30d --project my-api -o report.csv`
**When** executed
**Then** only matching runs are exported to the specified file

**Given** the export
**When** generated
**Then** includes: run_id, project_name, feature_description, status, phases_completed, duration, started_at, completed_at

**Given** command `adw global report weekly`
**When** executed
**Then** a formatted weekly summary report is displayed

**Technical Notes:**
- CSV: Standard library `csv` module
- JSON: `model_dump_json()` from Pydantic
- Report templates: Markdown format using Rich for pretty printing
- Future: Custom report templates (post-post-MVP)

**Implementation:**
- CLI: `adw global export` and `adw global report` commands
- New: `src/adw/core/export.py`

---

## Implementation Notes

### Phased Rollout (Revised 2026-01-25)

1. **Phase A (Foundation):** Story 16.1 - Project registry + init wizard integration
2. **Phase B (Core):** Story 16.2 - Global run list command
3. **Phase C (Analytics):** Story 16.3 - Cross-project statistics
4. **Phase D (Polish):** Story 16.5 - TUI dashboard

**Dropped:** ~~16.4 (Index Optimization)~~, ~~16.6 (Tags/Username)~~, ~~16.7 (Export)~~

### File Locations

```
~/.adw/
├── index.jsonl          # Global run index (EXISTS)
├── index-archive/       # Archived entries by month (EXISTS)
│   └── YYYY-MM.jsonl
├── projects.yaml        # Project registry (NEW - Story 16.1)
├── config.yaml          # User preferences (NEW - for cost rates)
└── stats-cache.json     # Cached statistics (NEW - Story 16.3)
```

### CLI Command Structure (Revised 2026-01-25)

```
# Global commands
adw global list [--project NAME] [--status STATUS] [--since DURATION] [--limit N]
adw global stats [--project NAME] [--format json]
adw global dashboard [--refresh SECONDS]

# Project registration
adw register [--name NAME]
adw unregister
adw projects [--discover]

# Init wizard (updated)
adw init  # Now includes GLOBAL_REGISTRY step after BASICS
```

**Removed:** ~~adw global export~~, ~~adw global report~~, ~~adw global index info/rebuild~~

### No Breaking Changes

This epic is purely additive:
- Existing runs continue to work unchanged
- Project registration is optional (index-based discovery works)
- New context fields have defaults (backward compatible)
- Existing `adw list` continues to work for project-local queries

### Dependencies on Existing Code

| Component | Location | Usage |
|-----------|----------|-------|
| IndexManager | `src/adw/core/index_manager.py` | All global queries |
| IndexEntry | `src/adw/models/index.py` | Run metadata model |
| WizardFlowController | `src/adw/cli/wizard/flow.py` | Init wizard integration (16.1) |
| CLI app | `src/adw/cli/app.py` | Command registration |

---

## Epic 16: Dependency Flowchart (Revised 2026-01-25)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [16.1] Project Registry                                                      ║
║  - Project management CLI (adw register, adw projects)                        ║
║  - ~/.adw/projects.yaml                                                       ║
║  - Init wizard GLOBAL_REGISTRY step                                           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 16.1                                                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [16.2] Global Run List                                                       ║
║  - adw global list command                                                    ║
║  - Creates global_app CLI group                                               ║
║  - Foundation for all other global commands                                   ║
║  - Filters: --project, --status, --since (NO --tag filter)                    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 16.2                                                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [16.3] Cross-Project Statistics                                              ║
║  - adw global stats command                                                   ║
║  - Token/cost aggregation from LLM response files                             ║
║  - Success rate, average duration                                             ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WAVE 4: After 16.1, 16.2, 16.3                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  [16.5] TUI Dashboard                                                         ║
║  - Rich-based terminal dashboard                                              ║
║  - Combines: project list, run list, statistics                               ║
║  - Live refresh with keyboard navigation                                      ║
║  - See ASCII mockups in Story 16.5 section                                    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

DROPPED STORIES (strikethrough in document):
  ╳ [16.4] Index Performance Optimization - Not needed
  ╳ [16.6] Run Context Enhancements (tags/username) - Not needed
  ╳ [16.7] Export and Reporting - Not needed
```

**Execution Summary (4 stories):**
- **Wave 1:** 16.1 - Project registry + init wizard integration
- **Wave 2:** 16.2 - Global run list (core infrastructure)
- **Wave 3:** 16.3 - Statistics
- **Wave 4:** 16.5 - TUI dashboard (requires 16.1 + 16.2 + 16.3)

**Critical Path:** 16.1 → 16.2 → 16.3 → 16.5

---

## Revision History

- **2026-01-25 (Scope Revision):**
  - DROPPED stories 16.4 (Index Performance), 16.6 (Tags/Username), 16.7 (Export/Reporting)
  - ADDED init wizard integration to 16.1 (GLOBAL_REGISTRY step after BASICS)
  - ADDED ASCII mockups for TUI dashboard (Story 16.5)
  - Updated dependency flowchart to reflect 4-story scope
  - Removed `--tag` filter from 16.2 (no longer applicable without 16.6)
- **2026-01-25:** Added dependency flowchart and created all story files via create-epic workflow.
- **2026-01-19:** Major revision to acknowledge existing IndexManager infrastructure. Fixed paths from `~/.config/adw/` to `~/.adw/`. Rewrote Story 16.4 (index already exists as JSONL). Clarified Story 16.6 (project_name already in IndexEntry). Updated technical notes throughout.
- **Original:** Initial epic creation (pre-IndexManager implementation)
