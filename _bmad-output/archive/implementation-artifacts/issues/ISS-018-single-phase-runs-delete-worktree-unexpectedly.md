# Issue: Single-phase runs delete worktree unexpectedly

**ID:** ISS-018
**Severity:** Major
**Type:** UX Issue
**Status:** fixed
**Reported:** 2026-01-07
**Reporter:** Ivo

## Related

- **Epic:** 10 (Worktree Isolation)
- **Story:** ux-fix-ISS-018-single-phase-worktree-retention
- **Component:** Worktree Management

## Description

When running a single phase (e.g., `adw run "blah" --phase plan`), the worktree is deleted after the phase completes. This is inconsistent with multi-phase behavior which keeps the worktree until all requested phases complete.

The core issue: if someone runs a *single phase*, their intent is to **stop and inspect** the output before deciding next steps. Deleting the worktree contradicts that intent.

## Reproduction Steps

1. Run `adw run "description" --phase plan`
2. Phase completes successfully
3. Worktree is deleted

## Expected Behavior

Worktree should remain after single-phase completion for inspection and continuation. A message should indicate where it is and how to clean up, e.g.:

```
✓ Phase 'plan' complete
Worktree: /path/to/worktree
Run 'adw worktree clean <name>' when done
```

## Actual Behavior

Worktree is deleted immediately after single-phase completion.

## Impact

User cannot inspect the working state, continue from where they left off, or iterate on the phase output. While artifacts are preserved in `.adw/runs/<runId>`, the working context (the actual file structure in the worktree) is lost.

## User Impact Score

- **Users Affected:** All users running single-phase workflows
- **Frequency:** Every single-phase run

## Workaround

None - artifacts exist in run folder but worktree is gone.

## Environment

- **OS:** macOS / Linux / Windows
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

- **Fix Story:** ux-fix-ISS-018-single-phase-worktree-retention.md
- **Fixed In:** PR #84
- **Verified By:** Git history
- **Verified Date:** 2026-01-07

## Notes

Recommendation: Don't delete the worktree on single-phase runs. Print a message telling the user where it is and how to clean it up when done. Simple, matches intent, no magic.
