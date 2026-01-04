# Story: Bugfix ISS-005 - Feature Description Not Captured

Status: ready-for-dev
Linear Issue: not-configured
Epic: 6 - Run Management & Recovery
Created: 2026-01-04

---

## Story

As a **CLI user**,
I want **my feature description to be saved and displayed correctly**,
so that **I can identify my runs in the list output by their actual purpose**.

## Acceptance Criteria

- [ ] When running `adw run "my specific feature"`, the exact text "my specific feature" is saved to RunContext
- [ ] The `adw list` command displays the actual feature description, not a generic placeholder
- [ ] Feature descriptions are preserved through the full data flow (CLI → Orchestrator → RunContext → context.json → IndexEntry → List display)
- [ ] Integration test verifies end-to-end feature description preservation
- [ ] Existing runs with correct feature descriptions continue to display correctly

## Tasks / Subtasks

### Task 1: Investigate Root Cause
- [x] Check if `context.json` files in `.adw/runs/` contain correct feature_description
- [x] Verify `~/.adw/index.jsonl` entries have correct feature_description
- [x] Trace the data flow from CLI argument to storage
- [x] Identify where the "Add feature" placeholder might be originating

**Investigation Results:**
- ✅ **BUG NOT REPRODUCIBLE** - The system is working correctly
- Feature descriptions ARE being stored correctly in `~/.adw/index.jsonl`
- Example: `"feature_description":"Add heelo world cli command"` stored and displayed correctly
- The "Add feature" entries are from pytest test runs (paths like `/private/var/folders/.../pytest...`)
- Tests use "Add feature" as placeholder text, polluting the global index
- User error: Issue report mentioned `adw start` but command is `adw run`

### Task 2: Implement Preventive Fix (based on investigation)
Since the bug is not reproducible, implement preventive measures:
- [x] Verify code paths are correct (confirmed in Task 1)
- [x] Update IndexManager to use test-specific index path during pytest runs
- [x] Ensure test runs don't pollute the user's global index

**Implementation:**
- Added `ADW_TEST_INDEX_PATH` environment variable support to `IndexManager`
- Created `isolated_global_index` autouse fixture in `tests/conftest.py`
- Added tests for environment variable precedence behavior

### Task 3: Add Integration Test
- [x] Create test that runs `adw run "unique test feature xyz"`
- [x] Verify context.json contains "unique test feature xyz"
- [x] Verify `adw list` output contains "unique test feature xyz"
- [x] Test with special characters and edge cases

**Implementation:**
- Created `tests/integration/cli/test_feature_description.py` with 10 tests
- Tests cover: CLI header display, RunContext serialization, ContextManager persistence, IndexManager storage
- Edge cases: spaces, special characters, quotes, hyphens

### Task 4: Cleanup Test Runs
- [ ] Document that existing runs with "Add feature" are from test executions
- [ ] Consider adding a cleanup command or option to purge test runs

---

## Developer Context

### Issue Report Reference

**ISS-005:** Feature description shows generic text instead of user input
- **Reported:** 2026-01-04
- **Severity:** Major
- **Type:** Bug
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-005-feature-description-not-captured.md`

**Symptoms:**
- User runs `adw start "add hello world"` (note: command is `adw run`, not `adw start`)
- `adw list` shows "Add feature" instead of "add hello world"
- All runs appear to have the same generic feature description

### Technical Requirements

**Data Flow Analysis (verified correct in code):**
```
CLI (feature argument)
  → orchestrator.run(feature_description)
    → RunContext(feature_description=feature_description)
      → context_manager.save(context)  # Saves to .adw/runs/{id}/context.json
      → index_manager.register_run(context)  # Saves to ~/.adw/index.jsonl
        → list command reads from RunContext or IndexEntry
          → list_display.show_runs() displays run.feature_description
```

**Key Files:**
| File | Purpose | Line Numbers |
|------|---------|--------------|
| `src/adw/cli/app.py` | CLI run command captures feature | 111-115, 232 |
| `src/adw/core/orchestrator.py` | Creates RunContext with feature | 216-222 |
| `src/adw/models/context.py` | RunContext model with feature_description | 47-49 |
| `src/adw/core/index_manager.py` | Creates IndexEntry with feature | 88-92 |
| `src/adw/cli/list.py` | Reads and displays runs | 110-140, 164-168 |
| `src/adw/cli/list_display.py` | Renders feature in table | 65 |

### Architecture Compliance

- **Pydantic Models:** RunContext and IndexEntry both have `feature_description: str` as required field
- **Persistence:** JSON serialization should preserve string values exactly
- **CLI Framework:** Typer captures positional arguments correctly

### Library & Framework Requirements

- **Typer 0.9+:** CLI framework - `typer.Argument()` captures positional args
- **Pydantic v2:** Model serialization/deserialization
- **Rich:** Table display (truncation handled by `_truncate_text`)

### File Structure Requirements

**Files to modify (if bug found):**
- `src/adw/cli/app.py` - Run command
- `src/adw/core/orchestrator.py` - Run orchestration
- `src/adw/core/index_manager.py` - Global index

**Files to add:**
- `tests/integration/cli/test_feature_description.py` - End-to-end test

### Testing Requirements

**Unit Tests:**
- Verify RunContext stores feature_description correctly
- Verify IndexEntry serializes feature_description correctly

**Integration Tests:**
- Full CLI flow: `adw run "specific feature"` → `adw list` → verify output
- Test with various feature descriptions:
  - Simple text: "add login"
  - With spaces: "add user authentication system"
  - With special chars: "fix bug #123"
  - With quotes: "add 'dark mode' toggle"

---

## Previous Story Intelligence

**Story 6-1 (Start New Run):** Implemented the run command with feature description capture
- Feature is a required positional argument
- Validation ensures non-empty feature description
- Special characters escaped for template safety

**Story 6-4 (List Recent Runs):** Implemented the list command
- Reads from local `.adw/runs/` or global `~/.adw/index.jsonl`
- ListDisplay renders feature_description with truncation

---

## Git Intelligence

**Recent commits related to run/list:**
- Run command implemented in Epic 6
- List command implemented in Story 6-4
- No recent changes to feature_description handling

---

## Investigation Hypothesis

Based on code analysis, the implementation appears correct. Possible causes:

1. **Test artifacts:** The runs showing "Add feature" may be from test executions that use placeholder text
2. **User command typo:** User mentioned `adw start` but command is `adw run` - ensure correct command used
3. **Dry run behavior:** If using `--dry-run`, no actual run is created
4. **Index corruption:** Global index might have stale/test data

**Recommended investigation steps:**
1. Run `cat ~/.adw/index.jsonl` to inspect actual stored data
2. Check `.adw/runs/*/context.json` files for feature_description values
3. Execute fresh `adw run "test123"` and verify storage
4. Run `adw list` and correlate with stored data

---

## Project Context Reference

See: `docs/project-context.md`

Key patterns:
- Pydantic models for data validation
- JSON persistence for run state
- Rich console for CLI output
- Typer for CLI framework

---

## Dev Notes

- The code path appears correct - investigate actual stored data first
- May be a data issue rather than code issue
- Consider adding debug logging to trace feature_description through the flow
- Test runs use "Add feature" as placeholder - distinguish from production runs

### References

- [Source: src/adw/cli/app.py#run command - lines 108-250]
- [Source: src/adw/core/orchestrator.py#run method - lines 180-320]
- [Source: src/adw/cli/list_display.py#show_runs - lines 47-78]
- [Source: _bmad-output/implementation-artifacts/issues/ISS-005-feature-description-not-captured.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-005-feature-description-not-captured.md
- Related: ISS-004 (Run ID truncation - separate issue)

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Story created with comprehensive context
- Root cause investigation required before implementation
- May be data/test artifact issue rather than code bug

### File List

- `src/adw/cli/app.py`
- `src/adw/core/orchestrator.py`
- `src/adw/core/index_manager.py`
- `src/adw/cli/list.py`
- `src/adw/cli/list_display.py`
- `src/adw/models/context.py`
- `src/adw/models/index.py`
- `tests/integration/cli/test_feature_description.py` (to create)
