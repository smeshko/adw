# Issue: Resume Logic Scattered Across Codebase

**ID:** ISS-014
**Severity:** Minor
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** 13 (Webhook Infrastructure / Tech Debt)
- **Story:** refactor-ISS-014-centralize-resume-logic
- **Component:** Core Architecture

## Description

Resume logic is scattered across 4 different locations, resulting in duplicated validation, inconsistent behavior, and unused code. This violates DRY principles and makes the resume functionality harder to maintain and extend.

## Reproduction Steps

1. Search for resume logic in the codebase
2. Find implementations in:
   - `cli/resume.py`
   - `orchestrator.resume()`
   - `interruption.py`
   - `validation/state_manager.py`
3. Observe duplicated validation and phase determination logic

## Expected Behavior

Single source of truth for resume logic in a centralized `ResumeManager` class that handles:
- Validation (can_resume checks)
- Resolution (find run, determine phase)
- Preparation (context updates)
- Status reporting

## Actual Behavior

Resume logic duplicated across 4 locations:

| Location | What it does | Issue |
|----------|--------------|-------|
| `cli/resume.py` | Finds run, validates status, determines phase, calls orchestrator | Duplicates validation logic |
| `orchestrator.resume()` | Loads context, validates, executes phases | Duplicates status check, phase logic |
| `interruption.py` | `can_resume()`, `prepare_resume()`, `get_resume_phase()` | Exported but **UNUSED** |
| `validation/state_manager.py` | Separate resume system for validation loop | Different semantics (iteration-level) |

### Specific Duplications:

**1. "Can resume" check - appears in 3 places:**
```python
# interruption.py:366
return context.status != "completed"

# orchestrator.py:723
if context.status == "completed": raise ConfigError

# resume.py:164
if context.status == "completed": raise ConfigError
```

**2. Resume phase determination - appears in 2 places:**
```python
# resume.py:75
resume_phase = from_phase or context.current_phase

# orchestrator.py:732
resume_phase = from_phase or context.current_phase
```

**3. Status transition to "running" - appears in 2 places:**
```python
# interruption.py:396-401 -> prepare_resume() sets status="running" (UNUSED)
# orchestrator.py:743 -> context.model_copy(update={"status": "running"})
```

## Impact

- Duplicated code increases maintenance burden
- Inconsistent behavior risk when updating one location but not others
- Dead code in `interruption.py` (unused functions)
- Harder to test resume logic in isolation
- Confusing for developers working on resume functionality

## User Impact Score

- **Users Affected:** Developers maintaining ADW
- **Frequency:** Every resume-related change

## Workaround

None - must be aware of all 4 locations when modifying resume logic.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** refactor-ISS-014-centralize-resume-logic.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

**Proposed Solution:** Create centralized `ResumeManager` class.

**New Files:**
- `src/adw/core/resume_manager.py` - Centralized handler
- `src/adw/models/resume.py` - ResumeInfo, ResumeStatus models

**Affected Components:**
- `cli/resume.py` - Simplifies significantly, delete `_find_run_to_resume()`
- `orchestrator.py` - Inject ResumeManager, refactor `resume()`
- `interruption.py` - Remove unused `can_resume`, `prepare_resume`, `get_resume_phase`
- `cli/bootstrap.py` - Wire up ResumeManager

**Benefits:**
1. Single source of truth for resume logic
2. Testable in isolation
3. Reusable across CLI, orchestrator, future API
4. Clear separation of concerns
5. Removes dead code

**Effort:** Medium

**Source:** `docs/development/tech-debt/resume-logic-centralization.md`
