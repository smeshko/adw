# Issue: Remove Evidence Gathering Completely

**ID:** ISS-021
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-09
**Reporter:** Ivo

## Related

- **Epic:** 16
- **Story:** N/A
- **Component:** Evidence Gathering / Orchestrator

## Description

Evidence gathering runs as a post-processing step after the validate phase completes, even though it's no longer needed. With the validation simplification in Epic 16, evidence gathering serves no purpose and should be completely removed from the codebase.

The evidence gathering system was designed for a previous validation architecture that captured test results, screenshots, and other artifacts. This is now obsolete.

## Reproduction Steps

1. Run `adw run "Create hello world cli command"` on a test project
2. Observe logs showing evidence gathering after validate phase:
   ```
   09:08:31 [INFO ] [phase] Starting evidence gathering
   09:08:31 [INFO ] [phase] CLI evidence gathered
   09:08:31 [INFO ] [phase] Evidence manifest generated
   09:08:31 [INFO ] [phase] Evidence copied to validate artifacts
   09:08:31 [INFO ] [phase] Evidence optimization completed
   ```
3. Evidence is gathered even though it's not used

## Expected Behavior

Evidence gathering should not run at all. The entire evidence gathering subsystem should be removed.

## Actual Behavior

Evidence gathering runs after every validate phase, consuming time and resources for no benefit.

## Impact

- Unnecessary processing time on every run
- Confusing logs suggesting evidence is being collected
- Dead code maintenance burden
- Cognitive overhead for developers understanding the codebase

## User Impact Score

- **Users Affected:** All users
- **Frequency:** Every run

## Workaround

None - evidence gathering always runs.

## Environment

- **OS:** macOS/Linux
- **App Version:** 0.1.6
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

See reproduction steps above.

### Screen Recording

N/A

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Files to Remove/Modify

### Remove entirely:
- `src/adw/evidence/` - entire directory
- `src/adw/models/evidence.py`
- `tests/unit/evidence/` - entire directory

### Modify:
- `src/adw/core/orchestrator.py` - remove evidence gathering calls (~lines 1534-1785)
- `src/adw/core/constants.py` - remove evidence-related constants
- `src/adw/models/__init__.py` - remove evidence model exports

## Notes

This is part of the Epic 16 validation simplification effort. Evidence gathering was designed for the old multi-phase validation loop that has been replaced.
