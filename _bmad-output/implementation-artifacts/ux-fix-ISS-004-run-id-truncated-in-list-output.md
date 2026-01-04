# Story UX-FIX-ISS-004: Display Full Run IDs in List Command Output

Status: ready-for-dev
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-04

---

## Story

As a **user running ADW commands**,
I want **the `adw list` command to display full Run IDs without truncation**,
so that **I can copy complete run IDs to use with other commands like `logs`, `status`, `resume`, and `abort`**.

## Acceptance Criteria

- [ ] **AC1:** Run ID column displays the complete 26-character ULID without truncation
- [ ] **AC2:** The table layout remains readable and does not wrap awkwardly on standard terminal widths (80+ columns)
- [ ] **AC3:** The fix applies to both local runs display (`ListDisplay.show_runs()`) and global index display (`_display_index_entries()`)
- [ ] **AC4:** JSON output (`--json`) already shows full IDs (verify and preserve this behavior)
- [ ] **AC5:** User can copy full Run ID directly from list output for use in other commands

## Tasks / Subtasks

### Task 1: Modify ListDisplay._truncate_id() Method
- [ ] Open `src/adw/cli/list_display.py`
- [ ] Remove or disable truncation logic in `_truncate_id()` method (lines 80-91)
- [ ] Return full run_id without modification
- [ ] Update method docstring to reflect new behavior

### Task 2: Modify list.py _display_index_entries() Function
- [ ] Open `src/adw/cli/list.py`
- [ ] Remove truncation at line 214: `run_id_short = entry.run_id[:12] + "..."`
- [ ] Use full `entry.run_id` in table row

### Task 3: Adjust Table Column Width (if needed)
- [ ] Test output with full 26-character ULIDs
- [ ] If table wraps poorly, consider:
  - Reducing Feature column max_width from 40 to 30-35
  - Or rely on Rich's automatic column sizing
- [ ] Ensure table is readable on 80-column terminals

### Task 4: Update Unit Tests
- [ ] Update `tests/unit/cli/test_list_display.py`:
  - Modify tests expecting truncated IDs to expect full IDs
  - Add test verifying full ULID is displayed
- [ ] Update `tests/unit/cli/test_list.py`:
  - Verify _display_index_entries shows full IDs

### Task 5: Verify JSON Output
- [ ] Confirm `_output_json_list()` returns full run_id (already does - line 311)
- [ ] Confirm `_output_json_index_entries()` returns full run_id (already does - line 264)
- [ ] Add/verify test for JSON output containing full IDs

### Task 6: Run Tests and Build
- [ ] Run `uv run pytest tests/unit/cli/test_list*.py -v`
- [ ] Run `uv run pytest` full test suite
- [ ] Verify build passes: `uv run ruff check src/`

---

## Relevant Feature Documentation

N/A - No conditional docs matched for this UX fix.

---

## Developer Context

### Technical Requirements

1. **ULID Format**: Run IDs are 26-character ULIDs (e.g., `01HQXK5P3Z7V8R2M4N6T9W1Y3C`)
2. **No Data Loss**: The full ID is already stored; this is purely a display fix
3. **Rich Table**: Continue using Rich Table for output formatting
4. **Backward Compatibility**: CLI interface unchanged; only display behavior changes

### Architecture Compliance

From `architecture.md`:

```
### Run Identification

**Decision:** ULID via `python-ulid`

Run IDs are ULIDs (Universally Unique Lexicographically Sortable Identifiers).

**Example:** `01HQXK5P3Z7V8R2M4N6T9W1Y3C`
```

The architecture uses 26-character ULIDs. Displaying them fully aligns with the design intent.

From `project-context.md`:

```python
# Rich for ALL CLI output
from rich.console import Console
from rich.table import Table
console = Console()

# Tables for structured data
table = Table(title="Recent Runs")
table.add_column("Run ID", style="cyan", no_wrap=True)
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Rich | 14.1.0 | Table display with `no_wrap=True` on Run ID column |
| Typer | 0.21.0 | CLI command framework |

Key consideration: The `no_wrap=True` setting on the Run ID column already prevents wrapping. Showing full IDs should work well with Rich's table rendering.

### File Structure Requirements

**Files to modify:**
```
src/adw/cli/
├── list_display.py     # MODIFY: _truncate_id() method
└── list.py             # MODIFY: _display_index_entries() function

tests/unit/cli/
├── test_list_display.py  # MODIFY: Update ID assertions
└── test_list.py          # MODIFY: Verify full IDs in tests
```

**No new files required** - This is a modification to existing display logic.

### Testing Requirements

**Test Framework:** pytest

**Modify existing tests:**

```python
# tests/unit/cli/test_list_display.py

def test_truncate_id_returns_full_id():
    """Test that _truncate_id returns the full ID without truncation."""
    display = ListDisplay()
    full_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"

    result = display._truncate_id(full_id)

    assert result == full_id  # No truncation
    assert "..." not in result

def test_show_runs_displays_full_run_ids():
    """Test that show_runs displays complete run IDs."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=120)
    display = ListDisplay(console)

    run = create_test_run(run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C")
    display.show_runs([run])

    result = output.getvalue()
    assert "01HQXK5P3Z7V8R2M4N6T9W1Y3C" in result
    assert "..." not in result or "..." only appears in feature text
```

**Coverage Target:** >80% on modified files (already achieved in story 6-4)

---

## Previous Story Intelligence

### From Story 6-4 (List Recent Runs)

The original implementation decision to truncate IDs was made for table formatting:

```python
# From list_display.py line 80-91
def _truncate_id(self, run_id: str) -> str:
    """Truncate run ID for display."""
    if len(run_id) > 15:
        return f"{run_id[:12]}..."
    return run_id
```

This caused the user issue - the truncation prevents copying full IDs for use with other commands.

### Key Learnings:
- Rich Table handles column widths dynamically
- The `no_wrap=True` setting already ensures Run ID column doesn't wrap
- Feature column has `max_width=40` which can be reduced if needed

---

## Git Intelligence

Recent commit patterns from project:

```
a881abd docs(story-9-2): mark story ready for review
ce6387b test(story-9-2): add integration tests for git commit functionality
```

For this story, use commit pattern:
- `fix(ux-fix-004): display full run IDs in list output`
- `test(ux-fix-004): update tests for full run ID display`

---

## Latest Technical Information

### Rich Table Column Sizing

Rich Table automatically sizes columns based on content. With a 26-character Run ID column:

| Column | Characters | Notes |
|--------|------------|-------|
| Run ID | 26 | Full ULID |
| Feature | 30-35 | Can reduce from 40 if needed |
| Status | ~12 | "interrupted" is longest |
| Started | 16 | "YYYY-MM-DD HH:MM" |
| **Total** | ~85-90 | Fits 80+ column terminals |

The table should fit comfortably on standard terminals.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Rich Console output** - Use Rich Table for structured output
2. **Type annotations** - All functions must have type hints
3. **PEP 8 naming** - snake_case for functions, PascalCase for classes
4. **Test coverage** - >80% coverage requirement

---

## Dev Notes

### Current vs Expected Output

**Current (Problematic):**
```
         Recent Runs (10)
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Run ID          ┃ Feature                ┃  Status   ┃ Started         ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 01HQXK5P3Z7V... │ Add user authentication│ completed │ 2026-01-03 10:30│
└─────────────────┴────────────────────────┴───────────┴─────────────────┘
```

**Expected (Fixed):**
```
                         Recent Runs (10)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Run ID                      ┃ Feature                ┃  Status   ┃ Started         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 01HQXK5P3Z7V8R2M4N6T9W1Y3C │ Add user authentication│ completed │ 2026-01-03 10:30│
└────────────────────────────┴────────────────────────┴───────────┴─────────────────┘
```

### Code Changes Summary

**list_display.py - `_truncate_id()` method:**
```python
# BEFORE (lines 80-91)
def _truncate_id(self, run_id: str) -> str:
    """Truncate run ID for display."""
    if len(run_id) > 15:
        return f"{run_id[:12]}..."
    return run_id

# AFTER
def _truncate_id(self, run_id: str) -> str:
    """Return run ID for display.

    Note: Full ID is returned to allow copying for use with other commands.
    """
    return run_id
```

**list.py - `_display_index_entries()` function:**
```python
# BEFORE (line 214)
run_id_short = entry.run_id[:12] + "..."

# AFTER
run_id_short = entry.run_id  # Full ID for copy/paste
```

### Source Tree Components

Files to touch:
- `src/adw/cli/list_display.py` - Modify `_truncate_id()` method
- `src/adw/cli/list.py` - Modify `_display_index_entries()` function
- `tests/unit/cli/test_list_display.py` - Update test expectations
- `tests/unit/cli/test_list.py` - Verify full IDs in tests

### Project Structure Notes

- Aligns with CLI output patterns (no_wrap=True already set)
- No new dependencies required
- Minimal change with high impact on usability

### References

- [Source: src/adw/cli/list_display.py:80-91] - _truncate_id() method
- [Source: src/adw/cli/list.py:214] - Global index truncation
- [Source: issues/ISS-004-run-id-truncated-in-list-output.md] - Original issue
- [Source: _bmad-output/architecture.md#Run-Identification] - ULID format

---

## Dev Agent Record

### Context Reference

Story created from UX issue ISS-004. This is a targeted fix to improve CLI usability.

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Story created from UX issue ISS-004
- Simple fix with clear before/after code changes
- Test updates required but straightforward
- Estimated scope: 2 files modified, 2 test files updated

### File List

Files to modify:
- `src/adw/cli/list_display.py` - Remove ID truncation
- `src/adw/cli/list.py` - Remove global index ID truncation
- `tests/unit/cli/test_list_display.py` - Update ID assertions
- `tests/unit/cli/test_list.py` - Verify full IDs

---

## Dependencies

- **Depends On:** Story 6.4 (List Recent Runs) - already done
- **Blocks:** None
- **Related Issues:** ISS-004

### Dependency Rationale
- This is a UX fix for existing functionality from Story 6.4
- No new dependencies introduced

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-04 | BMAD Create-Story | Initial story creation from ISS-004 |
