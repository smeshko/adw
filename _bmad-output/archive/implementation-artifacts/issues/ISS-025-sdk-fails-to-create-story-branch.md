# Issue: SDK fails to create story branch - commits go directly to staging

**ID:** ISS-025
**Severity:** Critical
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-18
**Reporter:** Ivo

## Related

- **Epic:** 10 (Worktree Isolation)
- **Story:** 10-1, 10-6
- **Component:** Worktree/Git Integration

## Description

When running Story 13.5 (run ID `01KF636397JZC18V4K8MGS59G7`), the SDK did not create a story branch. The `branch_name` field in `context.json` was `null`, and all commits were made directly to the `staging` branch. This resulted in PR #111 being incorrectly created to merge `staging` into `main` instead of `story/13-5` into `staging`.

## Reproduction Steps

1. Run `adw run` for Story 13.5 with worktree enabled
2. Observe that `context.json` shows `branch_name: null`
3. Observe commits are made directly to staging branch
4. PR is created from staging → main instead of story branch → staging

## Expected Behavior

- SDK MUST create a feature/story branch when creating a worktree
- SDK MUST validate that work is being done on a story branch, NOT staging/main
- If branch creation fails, the entire run MUST fail with a clear, propagated error
- PR should be created from story branch → staging

## Actual Behavior

- No story branch created (`branch_name: null`)
- 5 commits for Story 13.5 went directly to staging
- PR #111 created to merge staging → main (wrong direction)

## Impact

This breaks the entire git workflow. Work cannot be properly reviewed via PRs, staging branch gets polluted with unreviewed code, and PRs target the wrong branch. This defeats the purpose of worktree isolation and branch-based development.

## User Impact Score

- **Users Affected:** All users relying on worktree isolation
- **Frequency:** Every run where branch creation silently fails

## Workaround

Manual intervention required - create branch retroactively, cherry-pick commits, force-push to clean staging.

## Environment

- **OS:** macOS
- **App Version:** 0.1.12
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** bugfix-ISS-025-sdk-fails-to-create-story-branch.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Key evidence from run `01KF636397JZC18V4K8MGS59G7`:
- `context.json` field `branch_name: null`
- `commit_shas: []` (empty array)
- Commits visible on staging: `4bdb3c9`, `6fefcf7`, `c0078a1`, `19ff296`, `931f92c`
- PR #111 incorrectly targets main instead of staging

The SDK must enforce branch creation as a hard requirement and fail fast if it cannot create the story branch.
