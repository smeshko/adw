# Issue: Worktree cleanup fails when LLM creates untracked files

**ID:** ISS-008
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** 10
- **Story:** 10-1
- **Component:** Worktree/Cleanup

## Description

After a successful `adw run`, the worktree cleanup fails with "Failed to cleanup worktree" because the LLM creates new files that are untracked in git. The `git worktree remove` command refuses to delete worktrees with uncommitted changes unless `--force` is used.

## Reproduction Steps

1. Run `adw init` in a fresh project
2. Run `adw run "Create hello world command"`
3. LLM creates new files (src/, docs/, tests/)
4. Run completes successfully
5. Observe "Failed to cleanup worktree" message
6. Run `git worktree list` - worktree still exists
7. Check worktree: `git status` shows untracked files

## Expected Behavior

On successful run completion, the worktree should be cleaned up automatically. Either:
- Files created by LLM should be committed before cleanup
- OR cleanup should use `--force` for successful runs
- OR untracked files should be handled gracefully

## Actual Behavior

Worktree remains after successful run. The cleanup fails silently (logs warning but doesn't inform user clearly).

## Impact

- Worktrees accumulate, consuming disk space
- Users must manually clean up with `adw cleanup --force`
- Confusing UX - run "succeeds" but cleanup fails

## User Impact Score

- **Users Affected:** All users running ADW with worktree isolation
- **Frequency:** Every run that creates new files

## Workaround

Run `adw cleanup <run_id> --force` after each run.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0

## Evidence

### Console Output

```
✓ Run completed: 01KE6YXDTRCSZHKXTZWA32JSYC
Failed to cleanup worktree
```

### Worktree Status

```bash
$ git worktree list
/Users/.../test-project                                   442bc50 [main]
/Users/.../test-project/trees/01KE6YXDTRCSZHKXTZWA32JSYC  442bc50 [adw/01KE6...]

$ cd trees/01KE6YXDTRCSZHKXTZWA32JSYC && git status
Untracked files:
  docs/
  src/
  tests/
```

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Root cause in `src/adw/core/orchestrator.py:333`:
```python
self._cleanup_worktree(context.run_id, preserve=False)
```

This calls `WorktreeManager.remove_worktree()` without `force=True`, which fails when `_has_uncommitted_changes()` returns True.

Potential fixes:
1. Use `force=True` for successful run cleanup (simplest)
2. Auto-commit all changes before cleanup (aligns with Story 9.2)
3. Stage and commit untracked files as part of post-build hook
