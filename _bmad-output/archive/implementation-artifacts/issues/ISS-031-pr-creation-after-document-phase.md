# Issue: Auto-PR creation runs after all phases instead of after document phase

**ID:** ISS-031
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-20
**Reporter:** Ivo

## Related

- **Epic:** Epic 15 (Ship Phase & Deployment)
- **Story:** N/A
- **Component:** Orchestrator / Document Phase

## Description

Auto-PR creation logic in `orchestrator.py:386-394` runs only after ALL phases complete successfully. However, the ship phase's `pre.sh` hook validates that a PR already exists before allowing the phase to proceed. This creates a chicken-and-egg problem: ship fails because no PR exists, but PR creation never runs because ship failed first.

The PR must be created as part of the document phase (or immediately after it), not at the end of the entire run.

**Root Cause:** `src/adw/core/orchestrator.py:386-394`
```python
# This code is AFTER the phase loop completes - too late!
# Attempt auto-PR creation if enabled (Story ISS-011)
pr_result = None
if self.progress_display:
    pr_result = self.progress_display.try_auto_create_pr(
        run_id=context.run_id,
        context=context,
        runs_dir=self.runs_dir,
        auto_create_pr_enabled=self.git_config.auto_create_pr,
    )
```

## Reproduction Steps

1. Configure project with `git.auto_create_pr: true` in `.adw/project.yaml`
2. Ensure ship phase is enabled (default)
3. Run `adw run <feature>`
4. Plan, build, validate, document phases complete successfully
5. Ship phase starts
6. Ship `pre.sh` hook runs `gh pr view` to validate PR exists
7. Hook fails with "Error: No pull request found for branch"
8. Ship phase fails, run marked as failed
9. PR creation code never executes (it's after the phase loop)

## Expected Behavior

PR should be created as part of (or immediately after) the document phase completes, before ship phase begins. The workflow should be:

```
plan -> build -> validate -> document -> [CREATE PR] -> ship (validates & merges PR)
```

The document phase already generates `pr_description.md` artifact, making it the natural place for PR creation.

## Actual Behavior

```
plan -> build -> validate -> document -> ship (FAILS: no PR) -> [PR creation never runs]
```

PR creation is in post-run logic that only executes after all phases complete successfully. Since ship fails, the code path that creates the PR is never reached.

## Impact

- Ship phase always fails on first run when auto-PR is enabled
- Users must manually create PR, then resume the run
- Blocks the intended automated deployment workflow
- Confusing error message doesn't indicate the root cause

## User Impact Score

- **Users Affected:** All users with `auto_create_pr: true` and ship phase enabled
- **Frequency:** Every run with this configuration

## Workaround

1. Disable ship phase with `.adw/commands/ship/config.yaml` containing `enabled: false` (but this requires ISS-030 to be fixed first)
2. Or manually create PR after document phase completes, then resume run
3. Or run with ship phase disabled, create PR manually after run completes

## Environment

- **OS:** macOS / Linux / Windows
- **App Version:** 0.1.19
- **DPI Scaling:** N/A (CLI)

## Evidence

### Screenshots

N/A

### Logs

```
✓ plan -> ✓ build -> ✓ validate -> ✓ document -> · ship  80%
04:29:03 [INFO ] [phase] Phase completed
✓ plan -> ✓ build -> ✓ validate -> ✓ document -> ► ship  80%

04:29:03 [INFO ] [phase] Starting phase
04:29:03 [INFO ] [phase] Phase starting
04:29:04 [ERROR] [phase] Pre-hook failed
04:29:04 [ERROR] [phase] Phase failed

Error: Hook script exited with code 1
Suggestion: Check pre-hook script at .../commands/ship/pre.sh
```

Ship pre-hook output:
```
Ship phase pre-hook: Validating PR exists...
Current branch: feature/rule-151
Checking for PR on branch: feature/rule-151
Error: No pull request found for branch 'feature/rule-151'
Create a PR first with: gh pr create
```

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-031-pr-creation-after-document-phase.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Proposed Fix

**Option B: Create PR between document and ship phases in orchestrator**
- Add orchestrator logic after document phase completes
- Check if `auto_create_pr` is enabled
- Create PR

## Notes

This issue is related to ISS-030 (config ignored). The user attempted to work around this by disabling ship phase, but that config was also ignored due to ISS-030. Both issues need to be fixed for the ship workflow to function correctly.
