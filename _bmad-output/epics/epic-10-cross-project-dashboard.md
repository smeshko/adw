# Epic 10: Cross-Project Dashboard (Post-MVP)

**Goal:** Enable users to view and analyze runs across all their ADW-enabled projects from a single interface, with analytics, token/cost tracking, and dashboard views.

**Priority:** Post-MVP

**Dependencies:** Epics 1-7 (core functionality must be stable)

**Architecture Reference:** See `architecture.md` → "Future Enhancement: Cross-Project Run Visibility & Dashboard"

---

## Story 10.1: Project Registry

As a user,
I want to register projects with ADW globally,
So that I can track runs across multiple projects.

**Acceptance Criteria:**

**Given** command `adw register` in a project directory
**When** executed
**Then** the project path and name are added to `~/.config/adw/projects.yaml`

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

**Technical Notes:**
- Registry file: `~/.config/adw/projects.yaml`
- Schema: `{projects: [{path, name, registered_at}]}`
- Auto-register on first `adw run` (optional, configurable)

---

## Story 10.2: Global Run List

As a user,
I want to list runs across all registered projects,
So that I can see my development activity in one place.

**Acceptance Criteria:**

**Given** command `adw global list`
**When** executed
**Then** runs from all registered projects are displayed, sorted by time

**Given** command `adw global list --project my-api`
**When** executed
**Then** only runs from that project are shown

**Given** command `adw global list --status failed`
**When** executed
**Then** only failed runs across all projects are shown

**Given** command `adw global list --since 7d`
**When** executed
**Then** only runs from the last 7 days are shown

**Given** the run list
**When** displayed
**Then** each entry shows: run_id, project, feature (truncated), status, duration, started_at

**Technical Notes:**
- Aggregates `context.json` from all registered projects
- ULID provides natural time-based sorting
- Consider pagination for large result sets

---

## Story 10.3: Cross-Project Statistics

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
- Total token usage
- Estimated cost (based on model pricing)

**Given** command `adw global stats --project my-api`
**When** executed
**Then** shows statistics for that project only

**Given** command `adw global stats --format json`
**When** executed
**Then** outputs machine-readable JSON for integration

**Technical Notes:**
- Token counts from `llm/*_response.json`
- Cost estimation requires model pricing table (configurable)
- Cache stats for performance (invalidate on new runs)

---

## Story 10.4: Central Run Index (Optional)

As a power user,
I want a central index of all runs,
So that queries across thousands of runs are fast.

**Acceptance Criteria:**

**Given** config `global.index_enabled: true`
**When** any run state changes
**Then** the change is mirrored to `~/.config/adw/run-index.sqlite`

**Given** the index exists
**When** `adw global list` is run
**Then** it queries the index instead of scanning filesystems

**Given** command `adw global index rebuild`
**When** executed
**Then** the index is rebuilt from all registered project run directories

**Given** index and filesystem are out of sync
**When** detected
**Then** warning is shown with suggestion to rebuild

**Given** index is corrupted
**When** any query fails
**Then** graceful fallback to filesystem scanning with warning

**Technical Notes:**
- SQLite for simplicity (single file, no server)
- Schema mirrors `RunContext` essential fields
- Dual-write pattern: update index in `context_manager.py`
- Index is optional - filesystem scanning always works

---

## Story 10.5: TUI Dashboard

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
- Token/cost summary

**Given** active runs exist
**When** dashboard is open
**Then** status updates in real-time (polling or watching)

**Given** keyboard navigation
**When** user presses arrow keys
**Then** can navigate between runs and view details

**Given** command `adw global dashboard --refresh 5`
**When** executed
**Then** dashboard refreshes every 5 seconds

**Technical Notes:**
- Built with Rich `Live` and `Layout`
- Keyboard handling via Rich or `prompt_toolkit`
- Consider `textual` for more advanced TUI if needed

---

## Story 10.6: Run Context Enhancements

As a developer,
I want additional metadata captured per run,
So that cross-project analytics are more useful.

**Acceptance Criteria:**

**Given** a new run starts
**When** `project.yaml` contains `project_name`
**Then** it is stored in `RunContext.project_name`

**Given** command `adw run "feature" --tag urgent --tag backend`
**When** executed
**Then** tags are stored in `RunContext.tags`

**Given** the system can detect current user
**When** a run starts
**Then** username is stored in `RunContext.initiated_by`

**Given** cross-project queries
**When** filtering by tag
**Then** only runs with matching tags are returned

**Technical Notes:**
- Add to `models/context.py`:
  ```python
  project_name: str | None = None
  tags: list[str] = []
  initiated_by: str | None = None
  ```
- `initiated_by` from `os.getlogin()` or `$USER`
- Tags are free-form strings, no validation

---

## Story 10.7: Export and Reporting

As a user,
I want to export run data for external analysis,
So that I can create custom reports or integrate with other tools.

**Acceptance Criteria:**

**Given** command `adw global export --format csv`
**When** executed
**Then** all run data is exported as CSV

**Given** command `adw global export --format json`
**When** executed
**Then** all run data is exported as JSON array

**Given** command `adw global export --since 30d --project my-api`
**When** executed
**Then** only matching runs are included

**Given** the export
**When** generated
**Then** includes: run_id, project, feature, status, phases, duration, tokens, cost_estimate, started_at, completed_at

**Given** command `adw global report weekly`
**When** executed
**Then** a formatted weekly summary report is generated

**Technical Notes:**
- CSV for spreadsheet import
- JSON for programmatic consumption
- Report templates could be customizable (post-post-MVP)

---

## Implementation Notes

### Phased Rollout

1. **Phase A (Foundation):** Stories 10.1, 10.2, 10.6 - Basic registry and listing
2. **Phase B (Analytics):** Stories 10.3, 10.7 - Statistics and export
3. **Phase C (Performance):** Story 10.4 - Central index for scale
4. **Phase D (Polish):** Story 10.5 - TUI dashboard

### File Locations

```
~/.config/adw/
├── config.yaml          # User preferences (existing)
├── projects.yaml        # Project registry (new)
└── run-index.sqlite     # Optional central index (new)
```

### No Breaking Changes

This epic is purely additive:
- Existing runs continue to work unchanged
- Project registration is optional (can query by path)
- Index is optional (filesystem scanning is fallback)
- New context fields have defaults (backward compatible)

---
