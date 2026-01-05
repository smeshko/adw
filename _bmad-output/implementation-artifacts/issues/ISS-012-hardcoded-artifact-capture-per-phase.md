# Issue: Hardcoded Artifact Capture Per Phase

**ID:** ISS-012
**Severity:** Minor
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** N/A
- **Story:** N/A
- **Component:** PhaseRunner

## Description

Phase-specific artifact capture is hardcoded with `if phase == "..."` checks instead of a generic, config-driven approach. This violates the Open/Closed Principle and makes the system harder to extend.

## Reproduction Steps

1. Open `src/adw/core/phase_runner.py`
2. Navigate to lines 652-719
3. Observe hardcoded phase checks for artifact capture

## Expected Behavior

Artifact capture should be config-driven, allowing:
- Commands to declare their own artifacts in `command.yaml`
- New artifact types without modifying PhaseRunner
- Custom commands to define their own artifact capture

## Actual Behavior

Hardcoded special cases exist for each phase:
```python
if phase == "document":
    artifacts.append("pr_description.md")
if phase == "verify":
    self._capture_evidence_manifest(context)
if phase == "build":
    self._capture_git_diff_artifacts(context)
```

## Impact

- Violates Open/Closed Principle
- Adding new artifact types requires modifying PhaseRunner core code
- Custom commands cannot define their own artifact capture
- Increases maintenance burden

## User Impact Score

- **Users Affected:** Developers extending ADW
- **Frequency:** Every new artifact type addition

## Workaround

Manually modify PhaseRunner when adding new artifact types.

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

- **Fix Story:** refactor-ISS-012-config-driven-artifact-capture.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

**Proposed alternatives:**

| Approach | Implementation |
|----------|----------------|
| Config-driven | `command.yaml` declares `artifacts: [git_diff, evidence_manifest]` |
| Post-hook based | Hooks already receive `artifacts_dir` - they could write directly |
| Plugin system | Register artifact captors per phase type |

**Effort:** Medium

**Source:** `docs/development/tech-debt/orchestrator-phase-runner.md`
