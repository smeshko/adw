# Story: UX Fix ISS-036 - Progress Bar Shows Disabled Phases

Status: ready-for-dev
Linear Issue: not-configured
Epic: 5 - Pipeline Orchestration (Story 5-5-display-phase-progress)
Created: 2026-01-21

---

## Story

As a **CLI user**,
I want **the progress bar to only show enabled phases**,
so that **the percentage reflects my actual workflow and I don't see phases I've disabled**.

## Acceptance Criteria

- [ ] `ProgressDisplay.__init__` accepts optional `enabled_phases` parameter
- [ ] When `enabled_phases` is provided, only those phases appear in progress bar
- [ ] Percentage calculation uses only enabled phases (e.g., 4/4 = 100% when ship disabled)
- [ ] Phase number display shows correct total (e.g., "Phase 3/4" not "Phase 3/5")
- [ ] `bootstrap.py` determines enabled phases from config and passes to `ProgressDisplay`
- [ ] Default behavior unchanged when `enabled_phases` not provided (backward compatibility)
- [ ] Unit tests cover enabled phases filtering in progress display
- [ ] Integration test verifies disabled phases don't appear in output

## Tasks / Subtasks

### Task 1: Add enabled_phases Parameter to ProgressDisplay
- [x] Add `enabled_phases: list[str] | None = None` parameter to `__init__`
- [x] Store `self._enabled_phases` defaulting to `PHASE_SEQUENCE` if None
- [x] Update type hints and docstring

### Task 2: Update _show_progress_bar Method
- [x] Use `self._enabled_phases` instead of `PHASE_SEQUENCE` in iteration
- [x] Calculate percentage as `len(completed) / len(self._enabled_phases)`
- [x] Ensure progress bar only shows phases in `_enabled_phases`

### Task 3: Update on_phase_start Method
- [x] Calculate `phase_num` relative to `self._enabled_phases`
- [x] Calculate `total_phases` from `len(self._enabled_phases)`
- [x] Display "Phase X/Y" using enabled phases count

### Task 4: Update show_pipeline_summary Method
- [x] Use `self._enabled_phases` for phase status line
- [x] Only show phases that are in `_enabled_phases`

### Task 5: Update bootstrap.py to Pass Enabled Phases
- [x] After loading config, determine enabled phases using `CommandResolver`
- [x] Pass `enabled_phases` to `ProgressDisplay` constructor
- [x] Handle case where config loading fails (use all phases)

### Task 6: Write Unit Tests
- [ ] Test `ProgressDisplay` with custom `enabled_phases`
- [ ] Test percentage calculation with 4 enabled phases
- [ ] Test phase number display with reduced phase count
- [ ] Test backward compatibility when `enabled_phases=None`
- [ ] Test progress bar only shows enabled phases

---

## Relevant Feature Documentation

### Conditional Docs Loaded

- **docs/arch-phase-pipeline.md** - Phase sequence, artifact flow, skip phases via configuration
- **docs/arch-orchestrator.md** - Phase execution flow, PhaseRunner protocol

---

## Developer Context

### Issue Report Reference

**ISS-036:** Progress bar shows disabled phases

- **Reported:** 2026-01-21
- **Severity:** Major
- **Type:** UX Issue
- **File:** `_bmad-output/implementation-artifacts/issues/ISS-036-progress-bar-shows-disabled-phases.md`

**Root Cause Location:** `src/adw/cli/progress.py:120-146`

```python
# PROBLEM: Always uses PHASE_SEQUENCE (all 5 phases)
def _show_progress_bar(self, current_phase: str | None = None) -> None:
    phase_status = []
    for phase in PHASE_SEQUENCE:  # ← Iterates ALL phases
        ...

    # Calculate percentage
    completed = len(self._completed_phases)
    total = len(PHASE_SEQUENCE)  # ← Always 5, even if phases disabled
    percentage = (completed / total) * 100
```

**Current Output (ship disabled):**
```
✓ plan → ✓ build → ✓ validate → ✓ document → · ship  80%
```

**Expected Output (ship disabled):**
```
✓ plan → ✓ build → ✓ validate → ✓ document  100%
```

### Technical Requirements

**Phase Sequence:** `PHASE_SEQUENCE = ("plan", "build", "validate", "document", "ship")`

**Enabled Phase Detection:**
The `PhaseRunner.is_phase_enabled(phase)` method already exists and checks:
1. Command config's `enabled` field
2. Project config's `enabled` field (overrides command)

**Recommended Implementation Approach:**

```python
# progress.py - Constructor change
def __init__(
    self,
    console: Console | None = None,
    enabled_phases: list[str] | None = None,
) -> None:
    self.console = console or Console()
    # Use provided phases or default to all phases
    self._enabled_phases = enabled_phases or list(PHASE_SEQUENCE)
    self._current_phase: str | None = None
    self._completed_phases: list[str] = []
    # ... rest unchanged

# progress.py - Progress bar change
def _show_progress_bar(self, current_phase: str | None = None) -> None:
    phase_status = []
    for phase in self._enabled_phases:  # Use enabled phases
        color = self.PHASE_COLORS.get(phase, "white")
        if phase in self._completed_phases:
            phase_status.append(f"[green]✓[/] [{color}]{phase}[/]")
        elif phase == current_phase:
            phase_status.append(f"[yellow]►[/] [{color}]{phase}[/]")
        else:
            phase_status.append(f"[dim]· {phase}[/]")

    status_line = " → ".join(phase_status)

    # Calculate percentage based on enabled phases only
    completed = len(self._completed_phases)
    total = len(self._enabled_phases)  # Use enabled phases
    percentage = (completed / total) * 100

    self.console.print(f"{status_line}  [bold cyan]{percentage:.0f}%[/]")
```

**Bootstrap Integration:**

```python
# bootstrap.py - Pass enabled phases to ProgressDisplay
def create_orchestrator(...) -> Orchestrator:
    # ... existing code ...

    # Determine enabled phases from config (after PhaseRunner created)
    enabled_phases = None
    if with_progress:
        enabled_phases = [
            p for p in PHASE_SEQUENCE
            if phase_runner.is_phase_enabled(p)
        ]
        progress_display = ProgressDisplay(console, enabled_phases=enabled_phases)

    # ... rest unchanged
```

### Architecture Compliance

**File Locations:**
- Primary change: `src/adw/cli/progress.py`
- Secondary change: `src/adw/cli/bootstrap.py`
- Test file: `tests/unit/cli/test_progress.py`

**Pydantic Models:**
- No model changes needed

**Exception Handling:**
- No exception handling changes needed
- Invalid phases in `enabled_phases` simply won't match PHASE_COLORS (uses "white")

**Logging Requirements:**
- No logging changes needed (progress display is UI only)

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Rich | 14.1.0 | Console output, progress display |

**No new dependencies required.**

### File Structure Requirements

**Files to Modify:**

1. **`src/adw/cli/progress.py`** (PRIMARY)
   - Add `enabled_phases` parameter to `__init__`
   - Update `_show_progress_bar()` to use `_enabled_phases`
   - Update `on_phase_start()` for phase number calculation
   - Update `show_pipeline_summary()` for final status display

2. **`src/adw/cli/bootstrap.py`** (SECONDARY)
   - Determine enabled phases using `PhaseRunner.is_phase_enabled()`
   - Pass `enabled_phases` to `ProgressDisplay` constructor

3. **`tests/unit/cli/test_progress.py`** (TESTS)
   - Add tests for `enabled_phases` parameter
   - Add tests for percentage calculation with reduced phases
   - Add tests for backward compatibility

**Files NOT to Modify:**
- `src/adw/core/orchestrator.py` - Already uses `is_phase_enabled()` correctly
- `src/adw/core/phase_runner.py` - `is_phase_enabled()` already works correctly
- `src/adw/core/constants.py` - `PHASE_SEQUENCE` should remain all 5 phases

### Testing Requirements

**Unit Tests (Required):**

```python
# tests/unit/cli/test_progress.py

class TestEnabledPhasesFiltering:
    """Tests for enabled phases filtering (ISS-036)."""

    def test_init_with_enabled_phases(self) -> None:
        """Test ProgressDisplay accepts enabled_phases parameter."""
        enabled = ["plan", "build", "validate", "document"]
        progress = ProgressDisplay(enabled_phases=enabled)
        assert progress._enabled_phases == enabled

    def test_init_default_enabled_phases(self) -> None:
        """Test ProgressDisplay defaults to all phases when None."""
        progress = ProgressDisplay()
        assert progress._enabled_phases == list(PHASE_SEQUENCE)

    def test_progress_bar_shows_only_enabled_phases(self) -> None:
        """Test progress bar only displays enabled phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]  # No ship
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress._show_progress_bar(current_phase="plan")

        output_text = output.getvalue()
        assert "ship" not in output_text.lower()
        assert "plan" in output_text
        assert "document" in output_text

    def test_percentage_calculation_with_enabled_phases(self) -> None:
        """Test percentage uses enabled phases count."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]  # 4 phases
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress._completed_phases = ["plan", "build", "validate", "document"]
        progress._show_progress_bar()

        output_text = output.getvalue()
        # 4/4 = 100%, not 4/5 = 80%
        assert "100" in output_text and "%" in output_text

    def test_phase_number_with_enabled_phases(self) -> None:
        """Test phase number shows correct total."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress.on_phase_start("validate")

        output_text = output.getvalue()
        # validate is 3rd of 4 enabled phases
        assert "3/4" in output_text

    def test_summary_shows_only_enabled_phases(self) -> None:
        """Test pipeline summary only shows enabled phases."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=80)
        enabled = ["plan", "build", "validate", "document"]
        progress = ProgressDisplay(console, enabled_phases=enabled)

        progress.show_pipeline_summary(
            completed_phases=["plan", "build", "validate", "document"],
            status="completed",
            total_duration_ms=10000,
            total_tokens=5000,
        )

        output_text = output.getvalue()
        assert "ship" not in output_text.lower()
```

**Integration Test:**
- Full pipeline test with ship disabled in config
- Verify progress output shows 4 phases and 100% on completion

---

## Previous Story Intelligence

**Story 5-5-display-phase-progress:**
- Original implementation of progress display
- Used hardcoded `PHASE_SEQUENCE` for progress bar
- Added `PHASE_COLORS` mapping for visual consistency

**Story ISS-029 (Phase Config Not Honored):**
- Fixed phase enabled/disabled config detection
- Added `is_phase_enabled()` to `PhaseRunner`
- Ship phase now properly disabled via config

**Key Learning:**
ISS-036 became visible after ISS-029 was fixed. Before ISS-029, disabled phases weren't actually skipped, so the progress display was "accidentally correct". Now that phases are properly disabled, the progress display needs to respect the same configuration.

---

## Git Intelligence

**Recent Commits:**
```
64b52a5 [adw] Plan: Add user authentication with OAuth2
83fea70 [adw] Plan: Add user authentication
b2c3f36 chore: bump version to 0.1.21
8cc4f0a Merge branch 'staging' of github.com:smeshko/adw into staging
65149f4 status updates
```

**Files Changed in Story 5-5:**
- `src/adw/cli/progress.py` - Created progress display
- `src/adw/core/orchestrator.py` - Integrated progress display calls
- `tests/unit/cli/test_progress.py` - Added unit tests

**Existing Patterns:**
1. `_completed_phases` list tracks completed phases
2. `_show_progress_bar()` iterates phases and builds status line
3. Phase position calculated using `PHASE_SEQUENCE.index()`
4. Percentage calculated as `len(completed) / len(PHASE_SEQUENCE)`

---

## Latest Technical Information

**Rich Library (v14.1.0):**
- Progress bar formatting unchanged
- Console.print() works as documented
- No version-specific concerns

**No version updates or API changes needed.**

---

## Project Context Reference

See: `docs/CONDITIONAL_DOCS.md`

Key patterns from project context:

1. **Constructor Parameters:**
   ```python
   def __init__(
       self,
       console: Console | None = None,
       enabled_phases: list[str] | None = None,  # New parameter
   ) -> None:
   ```

2. **Default Value Pattern:**
   ```python
   self._enabled_phases = enabled_phases or list(PHASE_SEQUENCE)
   ```

3. **Immutable Constants:**
   - `PHASE_SEQUENCE` remains unchanged (tuple)
   - Instance variable `_enabled_phases` is a list for flexibility

4. **Backward Compatibility:**
   - All existing code calling `ProgressDisplay()` without parameters continues to work
   - Only `bootstrap.py` needs to pass the new parameter

---

## Dev Notes

### Implementation Strategy

**Minimal Change Approach:**
1. Add optional `enabled_phases` parameter with `None` default
2. Store as `_enabled_phases` with fallback to `PHASE_SEQUENCE`
3. Replace all `PHASE_SEQUENCE` references with `self._enabled_phases`
4. Update `bootstrap.py` to compute and pass enabled phases

### Edge Cases to Handle

1. **All phases enabled:** Progress bar shows all 5 phases (current behavior)
2. **Ship disabled:** Progress bar shows 4 phases, 100% when all 4 complete
3. **Multiple phases disabled:** e.g., only plan+build enabled → 50% = 1/2
4. **No phases enabled:** Edge case - should still work (0 phases, 0%)
5. **Invalid phase names:** Silently handled by PHASE_COLORS.get() returning "white"

### Method Changes Summary

| Method | Change |
|--------|--------|
| `__init__` | Add `enabled_phases` parameter |
| `_show_progress_bar` | Use `_enabled_phases` instead of `PHASE_SEQUENCE` |
| `on_phase_start` | Calculate phase number from `_enabled_phases` |
| `on_phase_complete` | No change (already uses `_completed_phases`) |
| `show_pipeline_summary` | Use `_enabled_phases` for phase status line |

### Backward Compatibility

- `ProgressDisplay()` with no args → all 5 phases shown (unchanged)
- `ProgressDisplay(console=c)` → all 5 phases shown (unchanged)
- `ProgressDisplay(console=c, enabled_phases=None)` → all 5 phases shown
- `ProgressDisplay(console=c, enabled_phases=[...])` → only listed phases shown

### References

- [Source: src/adw/cli/progress.py:77-90] - Constructor to modify
- [Source: src/adw/cli/progress.py:120-146] - Progress bar calculation
- [Source: src/adw/cli/progress.py:92-118] - on_phase_start method
- [Source: src/adw/cli/progress.py:228-325] - show_pipeline_summary method
- [Source: src/adw/cli/bootstrap.py:226-228] - ProgressDisplay instantiation
- [Source: src/adw/core/phase_runner.py:710-756] - is_phase_enabled method
- [Source: _bmad-output/implementation-artifacts/issues/ISS-036-progress-bar-shows-disabled-phases.md]

---

## Dev Agent Record

### Context Reference

- Issue: ISS-036-progress-bar-shows-disabled-phases.md
- Related: Story 5-5 (original progress display), ISS-029 (phase config honored)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

N/A

### Completion Notes List

(To be filled by dev agent)

### File List

**Expected files to modify:**
- `src/adw/cli/progress.py` - Add enabled_phases parameter, update display logic
- `src/adw/cli/bootstrap.py` - Compute enabled phases, pass to ProgressDisplay
- `tests/unit/cli/test_progress.py` - Add tests for enabled phases filtering
