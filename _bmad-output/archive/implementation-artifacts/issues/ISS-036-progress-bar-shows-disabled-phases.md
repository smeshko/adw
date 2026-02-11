# Issue: Progress Bar Shows Disabled Phases

**ID:** ISS-036
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-21
**Reporter:** Ivo

## Related

- **Epic:** Epic 5 (Pipeline Orchestration)
- **Story:** 5-5-display-phase-progress
- **Component:** Progress Display (progress.py)

## Description

The progress bar displays all 5 phases (plan, build, validate, document, ship) regardless of which phases are actually enabled in the configuration. This causes:

1. Disabled phases (like `ship` with `enabled: false`) appear in the progress bar
2. Percentage calculations include disabled phases, showing misleading completion %
3. Users see phases they've explicitly disabled

**Location:** `src/adw/cli/progress.py:120-146`

## Reproduction Steps

1. Configure a project with ship phase disabled:
   ```yaml
   # .adw/commands/ship/config.yaml
   enabled: false
   ```
2. Run `adw run "any feature"`
3. Observe progress bar shows:
   ```
   ✓ plan → ✓ build → ✓ validate → ✓ document → · ship  80%
   ```
4. Note the 80% calculation includes the disabled ship phase

**Evidence from project-rulebook-be run:**
```
✓ plan → ✓ build → · validate → · document → · ship  40%
```
Ship was disabled but still shown.

## Expected Behavior

1. Progress bar only shows enabled phases
2. Percentage calculated based on enabled phases only
3. If 4 phases enabled and 4 completed = 100%

## Actual Behavior

1. All 5 phases shown regardless of config
2. Percentage based on 5 phases (e.g., 4/5 = 80% even when ship disabled)
3. Disabled phases appear as pending (·)

## Impact

- **Misleading progress**: Users think run is 80% complete when it's actually 100%
- **Confusion**: "Why is ship showing if I disabled it?"
- **Poor UX**: Progress indicator doesn't reflect actual workflow

## Workaround

None. Progress display always shows all phases.

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Evidence

### Code Analysis

**progress.py:120-146** - Uses hardcoded PHASE_SEQUENCE:
```python
def _show_progress_bar(self, current_phase: str | None = None) -> None:
    phase_status = []
    for phase in PHASE_SEQUENCE:  # ← Always iterates all 5 phases
        ...

    # Calculate percentage
    completed = len(self._completed_phases)
    total = len(PHASE_SEQUENCE)  # ← Always 5, even if phases disabled
    percentage = (completed / total) * 100
```

## Proposed Fix

### 1. Accept enabled phases in constructor
**File:** `src/adw/cli/progress.py`
```python
def __init__(
    self,
    console: Console | None = None,
    enabled_phases: list[str] | None = None
) -> None:
    self.console = console or Console()
    self._enabled_phases = enabled_phases or list(PHASE_SEQUENCE)
    ...
```

### 2. Use enabled phases in progress bar
```python
def _show_progress_bar(self, current_phase: str | None = None) -> None:
    phase_status = []
    for phase in self._enabled_phases:  # Use enabled phases
        ...

    # Calculate percentage based on enabled phases
    completed = len(self._completed_phases)
    total = len(self._enabled_phases)  # Only count enabled
    percentage = (completed / total) * 100
```

### 3. Pass enabled phases from orchestrator
**File:** `src/adw/core/orchestrator.py` or `bootstrap.py`
```python
# Determine enabled phases from config
enabled_phases = [p for p in PHASE_SEQUENCE if self._is_phase_enabled(p)]
progress_display = ProgressDisplay(console, enabled_phases=enabled_phases)
```

## Files Affected

| File | Change |
|------|--------|
| `src/adw/cli/progress.py` | Accept and use enabled_phases parameter |
| `src/adw/cli/bootstrap.py` | Pass enabled phases to ProgressDisplay |
| `src/adw/core/orchestrator.py` | Determine enabled phases from config |

## Resolution

- **Fix Story:** [ux-fix-ISS-036-progress-bar-shows-disabled-phases.md](../ux-fix-ISS-036-progress-bar-shows-disabled-phases.md)
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This issue becomes more apparent with ISS-029 fixed (phase enabled config now honored). With ship frequently disabled, users now see the misleading progress more often.
