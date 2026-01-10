# Issue: Tests Not Cleaning Up Worktrees

**ID:** ISS-024
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-10
**Reporter:** Ivo

## Related

- **Epic:** 10 (Worktree Isolation)
- **Story:** N/A
- **Component:** Test Infrastructure / Worktree Management

## Description

After running the test suite, many worktrees with ULID names are left behind and not cleaned up. This indicates that test fixtures or teardown logic is not properly removing worktrees created during test execution.

## Reproduction Steps

1. Run the test suite: `pytest`
2. After tests complete, check for leftover worktrees
3. Observe multiple worktree directories with ULID names remain

## Expected Behavior

All worktrees created during test execution should be cleaned up automatically when tests complete, regardless of whether tests pass or fail.

## Actual Behavior

Worktrees with ULID names accumulate after test runs, suggesting:
- Test fixtures don't have proper teardown/cleanup
- Worktree cleanup fails silently
- Tests that fail may skip cleanup

## Impact

- Disk space accumulation over time
- Clutter in the project directory
- Potential git issues with orphaned worktrees
- Confusing development experience

## User Impact Score

- **Users Affected:** All developers running tests
- **Frequency:** Every test run

## Workaround

Manually clean up worktrees after test runs:
```bash
git worktree list
git worktree remove <path> --force
```

## Environment

- **OS:** macOS/Linux
- **App Version:** 0.1.6
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Suggested Fix

1. Review test fixtures that create worktrees
2. Ensure `pytest` fixtures use proper `yield` with cleanup in finally block
3. Add `autouse=True` fixture for session-level worktree cleanup
4. Consider adding a test teardown hook that cleans all ULID-named worktrees

## Notes

Check `tests/` directory for fixtures related to worktree creation, particularly in `conftest.py` files.
