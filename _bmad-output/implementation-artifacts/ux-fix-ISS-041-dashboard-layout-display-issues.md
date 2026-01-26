# Story: UX Fix ISS-041 - Dashboard Layout and Display Issues

Status: ready-for-dev
Linear Issue: pending
Epic: 16 - Cross-Project Dashboard
Created: 2026-01-26

---

## Story

As a **developer using the ADW dashboard**,
I want **the dashboard to display runs clearly with proper spacing, readable durations, full run IDs, and accurate token counts**,
so that **I can quickly understand the status and cost of my workflow runs at a glance**.

## Acceptance Criteria

- [ ] **AC1: Recent runs section sizing** - The recent runs panel should size to fit its content without excessive whitespace. When showing 6 runs, it should only take ~8-10 lines, not 50+ lines with empty space.

- [ ] **AC2: Active runs duration display** - The duration in active runs should display on a single line in human-readable format (e.g., "88h 53m" instead of "5333m" on one line and "50s" on another).

- [ ] **AC3: Run ID display width** - Run IDs should use available horizontal space. With a wide terminal, show more of the ID (at least 12-16 characters) instead of truncating to 8 characters with "...".

- [ ] **AC4: Token aggregation** - Token counts should display actual values from LLM response files. The summary and per-project breakdown should show non-zero token counts for runs that used tokens.

## Tasks / Subtasks

### Task 1: Fix Recent Runs Panel Sizing
- [x] 1.1: In `create_recent_runs_table()`, remove fixed height constraints
- [x] 1.2: Let the table size naturally based on row count
- [x] 1.3: In `render()`, use `size` parameter only for fixed sections (summary, projects), let runs section use remaining space proportionally

### Task 2: Fix Active Runs Duration Display
- [x] 2.1: In `create_active_runs_panel()`, fix the duration column formatting
- [x] 2.2: Remove the line break between minutes and seconds (current: `"[yellow]◐[/]  {elapsed_min}m\n{elapsed_sec:02d}s"`)
- [x] 2.3: Format duration consistently: `{elapsed_min}m {elapsed_sec:02d}s` or convert to hours when > 60 minutes

### Task 3: Improve Run ID Column Width
- [ ] 3.1: Increase the run ID column `width` from 10-12 to 16-20 characters
- [ ] 3.2: Consider making width dynamic based on terminal size
- [ ] 3.3: Update both recent runs table and active runs panel

### Task 4: Investigate Token Display
- [ ] 4.1: Verify LLM response files exist in run directories under `.adw/runs/{run_id}/llm/`
- [ ] 4.2: Check if `_parse_llm_response_files()` is finding and parsing files correctly
- [ ] 4.3: If LLM files don't exist, investigate why they're not being persisted during runs
- [ ] 4.4: Add logging to help diagnose token aggregation issues

---

## Developer Context

### Technical Requirements

**Primary file to modify:** `src/adw/cli/dashboard.py`

This is a self-contained TUI module using Rich components:
- `DashboardLayout` - Generates Rich renderables (Panel, Table, Text)
- `DashboardController` - Coordinates data fetching and rendering
- `DashboardState` / `DashboardData` - State management

**Token investigation may involve:**
- `src/adw/core/stats_aggregator.py` - Parses LLM response files
- `src/adw/executors/` - LLM executors that should persist response files

### Architecture Compliance

**Must follow:**
- Rich library for all TUI components (Panel, Table, Text, Layout)
- Pydantic models for data (`GlobalStatistics`, `IndexEntry`, `TokenUsage`)
- Type annotations on all functions
- No `print()` - use Rich Console

**Layout architecture:**
```python
# Current structure in render():
main_layout.split_column(
    Layout(name="header", size=3),
    Layout(name="body"),           # <-- This is where sizing issue is
    Layout(name="footer", size=1),
)
# body splits into: summary (size=8), runs (flexible), projects (size=10)
```

### Library & Framework Requirements

- **Rich 14.1.0** - TUI framework
  - `Panel` - For bordered sections
  - `Table` - For run listings
  - `Layout` - For dashboard structure
  - `Live` - For auto-refresh

**Key Rich Layout behavior:**
- `size=N` fixes the section to N rows
- Omitting `size` lets the section expand to fill remaining space
- Tables inside Panels expand to fill Panel

### File Structure Requirements

**Files to modify:**
- `src/adw/cli/dashboard.py` - Main changes

**Files to investigate (token issue):**
- `src/adw/core/stats_aggregator.py` - `_parse_llm_response_files()`
- Check if `.adw/runs/{run_id}/llm/` directories exist with `*_response.json` files

### Testing Requirements

- Run `adw global dashboard` to verify visual changes
- Test with both empty state (no runs) and populated state
- Test with various terminal widths to verify ID column behavior
- Verify token counts match actual LLM response file contents
- Run existing tests: `pytest tests/unit/cli/test_dashboard.py`

---

## Git Intelligence

**Recent commits (context):**
- `6885a7c` feat(global): filter stats to registered projects and add clean command
- `22b9d44` feat(story-16-5): TUI Dashboard for cross-project ADW monitoring (#152)
- `20d2b04` feat(story-16-3): Cross-Project Statistics (#151)

The dashboard was just implemented in Story 16-5 (commit 22b9d44). This fix addresses UX issues discovered during QA of that implementation.

---

## Root Cause Analysis

### Issue 1: Excessive Whitespace in Recent Runs
**Location:** `DashboardLayout.create_recent_runs_table()` and `DashboardController.render()`

In `render()` at line 885-889:
```python
body_layout.split_column(
    Layout(name="summary", size=8),
    Layout(name="runs"),            # No size = takes remaining space
    Layout(name="projects", size=10),
)
```
The "runs" section takes ALL remaining space since it has no `size` constraint. The Table inside doesn't shrink the Panel.

**Fix approach:** Either:
1. Make runs section `ratio=1` so it shares space proportionally, OR
2. Calculate actual needed size based on row count

### Issue 2: Duration Split Across Lines
**Location:** `DashboardLayout.create_active_runs_panel()` lines 279-298

The table adds the duration column with `width=10`, but the duration string includes an icon prefix:
```python
f"[yellow]◐[/]  {duration}",  # where duration = f"{elapsed_min}m {elapsed_sec:02d}s"
```
The width is insufficient causing wrapping.

**Fix approach:**
1. Separate the status indicator from duration column, OR
2. Increase column width

### Issue 3: Truncated Run IDs
**Location:** Multiple places in `DashboardLayout`

- `create_active_runs_panel()` line 273: `table.add_column("ID", width=10)`
- `create_recent_runs_table()` line 330: `width=12`
- Truncation at lines 293 and 385: `run.run_id[:8] + "..."`

**Fix approach:** Use terminal width to determine ID column width, show 16+ characters

### Issue 4: Zero Token Display
**Location:** `StatsAggregator._parse_llm_response_files()` or LLM executor persistence

The aggregator correctly implements token parsing from `.adw/runs/{run_id}/llm/*_response.json` files. If showing 0, either:
1. LLM response files aren't being created, OR
2. The `stats` key structure differs from expected, OR
3. Cache is stale

**Investigation approach:** Check if LLM files exist in a completed run directory

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Rich for all CLI output** - No `print()`, use `console.print()`
- **Type annotations required** - All functions must have type hints
- **Pydantic models** - All structured data uses BaseModel
- **Python 3.13+** - Use modern syntax (`X | None` not `Optional[X]`)

---

## Dev Notes

### Key Code Sections to Modify

**1. Fix table sizing in render() around line 885:**
```python
# Instead of letting runs take all space, size based on content
active_rows = len(self.data.active_runs) if self.data.active_runs else 0
recent_rows = min(len(self.data.recent_runs), 6)  # max 6 shown
runs_size = 3 + active_rows * 2 + recent_rows + 4  # headers + rows + padding
```

**2. Fix duration column in create_active_runs_panel() line 277:**
```python
# Current: width=10 is too narrow for "◐  88h 53m"
table.add_column("Duration", width=14)  # Increase width
```

**3. Fix run ID width in create_recent_runs_table() line 330:**
```python
# Current: width=12
# Better: width=18 to show more of the ULID
table.add_column("RUN ID", style="cyan", no_wrap=True, width=18)
```

**4. Remove truncation or use more characters:**
```python
# Lines 293, 385: run.run_id[:8] + "..."
# Change to: run.run_id[:14] + ".." for better readability
```

### References

- [Source: ISS-041-dashboard-layout-display-issues.md] - Issue details with screenshot
- [Source: src/adw/cli/dashboard.py:256-305] - create_active_runs_panel()
- [Source: src/adw/cli/dashboard.py:306-400] - create_recent_runs_table()
- [Source: src/adw/cli/dashboard.py:809-939] - render()
- [Source: src/adw/core/stats_aggregator.py:120-151] - _parse_llm_response_files()

---

## Dev Agent Record

### Context Reference

Issue file: `_bmad-output/implementation-artifacts/issues/ISS-041-dashboard-layout-display-issues.md`
Screenshot: `_bmad-output/implementation-artifacts/issues/assets/ISS-041-dashboard-layout.png`

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - straightforward layout fix

### Completion Notes List

- Task 1: Fixed recent runs panel sizing by using `ratio=1` in Layout instead of unbounded sizing. The table in `create_recent_runs_table()` already sizes naturally - the issue was the parent Layout taking all remaining space.
- Task 2: Fixed active runs duration display - increased column width from 10 to 14 with no_wrap=True, reduced icon spacing, and added hours format for durations >= 60 minutes (e.g., "88h 53m" instead of "5333m 50s").

### File List

- `src/adw/cli/dashboard.py` - Modified render() to use ratio-based sizing for runs section
- `tests/unit/cli/test_dashboard.py` - Added TestDashboardLayoutSizing tests
