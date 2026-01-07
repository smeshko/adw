# Issue: Epic 11 phases not unified - verify and validate both still execute

**ID:** ISS-019
**Severity:** Critical
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-07
**Reporter:** Ivo

## Related

- **Epic:** 11
- **Story:** 11.1
- **Component:** Pipeline Orchestration / Phase Execution

## Description

Epic 11 goal was to replace separate Verify and Validate phases with a single unified "Validation Loop" phase. The implementation was marked "done" but PHASE_SEQUENCE in `src/adw/core/constants.py` still contains both phases (5 phases instead of 4).

Story 11.1 completion notes incorrectly state "validate already exists so no modification needed" - missing the point that the verify phase should have been removed and its functionality absorbed into the unified Validation phase.

The epic explicitly states:
```
OLD: Plan → Build → Verify → Validate → Document
NEW: Plan → Build → Validation Loop → Document
```

## Reproduction Steps

1. Run `adw run --feature "any feature"`
2. Observe phase execution output
3. Note that both "verify" AND "validate" phases execute sequentially
4. Check `src/adw/core/constants.py:11-17` - PHASE_SEQUENCE has 5 phases

## Expected Behavior

Pipeline should execute 4 phases:
- Plan → Build → Validation → Document

The unified Validation phase should:
- Run EvidenceValidator (replaces evidence gathering from verify)
- Run ReviewValidator (replaces code review from verify prompt)
- Run TestValidator
- Execute the triage/fix loop as implemented

## Actual Behavior

Pipeline executes 5 phases:
- Plan → Build → Verify → Validate → Document

Where:
- Verify phase: Runs LLM prompt + gathers evidence + optimizes evidence
- Validate phase: Runs ValidationPhase with all validators (including duplicate evidence/review)

## Impact

- **Duplicate work**: Evidence gathered twice (verify phase + EvidenceValidator)
- **Duplicate review**: Code review happens twice (verify prompt + ReviewValidator)
- **Longer execution**: Pipeline runs ~40% longer than intended
- **Confusing UX**: Users see 5 phases when docs describe 4
- **Token waste**: Extra LLM calls for verify phase prompt

## User Impact Score

- **Users Affected:** All users
- **Frequency:** Every run

## Workaround

None - phases are hardcoded in `src/adw/core/constants.py`

## Environment

- **OS:** macOS/Linux/Windows
- **App Version:** Current
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** bugfix-ISS-019-epic-11-phases-not-unified.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

### Root Cause Analysis

The implementer of Story 11.1 misunderstood the Epic 11 requirement:

1. **What they did**: Created ValidationPhase class, validators, and attached it to the existing "validate" phase
2. **What they should have done**:
   - Changed PHASE_SEQUENCE from 5 phases to 4
   - Removed "verify" phase entirely
   - Renamed "validate" to "validation" (optional but clearer)
   - Moved evidence gathering logic from orchestrator into EvidenceValidator

### Fix Requirements

1. Update `src/adw/core/constants.py`:
   ```python
   PHASE_SEQUENCE = ("plan", "build", "validation", "document")
   ```

2. Remove verify-specific logic from `src/adw/core/orchestrator.py`:
   - Lines 1179-1181: Platform detection (move to validation phase start)
   - Lines 1189-1195: Evidence gathering/optimization (already in EvidenceValidator)

3. Delete `src/adw/defaults/commands/verify/` directory

4. Update ValidationPhase to handle platform detection at start

5. Update all references to phase names throughout codebase

### Files Affected

- `src/adw/core/constants.py` - PHASE_SEQUENCE
- `src/adw/core/orchestrator.py` - Remove verify-specific logic
- `src/adw/defaults/commands/verify/` - Delete directory
- `src/adw/validation/phase.py` - Add platform detection
- Various test files referencing phase names
