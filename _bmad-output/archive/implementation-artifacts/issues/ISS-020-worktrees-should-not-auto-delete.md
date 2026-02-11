# Issue: Worktrees should not auto-delete - only via cleanup command

**ID:** ISS-020
**Severity:** Major
**Type:** UX Issue
**Status:** fixed
**Reported:** 2026-01-07
**Reporter:** Ivo

## Related

- **Epic:** 10 (Worktree Isolation)
- **Story:** N/A
- **Component:** Worktree Management

## Description

Worktrees are currently being automatically deleted in certain scenarios. The expected behavior is that worktrees should never be automatically deleted - deletion should only occur when the user explicitly runs the cleanup command.

## Reproduction Steps

1. Run a workflow that creates a worktree
2. Complete the run (or encounter specific completion conditions)
3. Observe that the worktree is automatically deleted

## Expected Behavior

Worktrees should persist indefinitely until the user explicitly runs the cleanup command. This allows users to:
- Inspect worktree contents after run completion
- Resume work or debug issues
- Maintain full control over worktree lifecycle

## Actual Behavior

Worktrees are automatically deleted in certain scenarios (e.g., after run completion, after single-phase runs), removing the user's ability to inspect or reuse them.

## Impact

- Loss of work context and debugging capability
- Unexpected behavior that disrupts workflow
- Users cannot inspect completed work in worktrees
- Reduces trust in the system's predictability

## User Impact Score

- **Users Affected:** All users using worktree isolation
- **Frequency:** Every completed run with worktree

## Workaround

None - once auto-deleted, the worktree cannot be recovered.

## Environment

- **OS:** macOS
- **App Version:** Current development
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-020-disable-worktree-auto-delete.md
- **Fixed In:** PR #85
- **Verified By:** Git history
- **Verified Date:** 2026-01-08

## Notes

Related to ISS-018 (single-phase-runs-delete-worktree-unexpectedly). This issue broadens the scope to ensure NO automatic worktree deletion occurs under any circumstances.
