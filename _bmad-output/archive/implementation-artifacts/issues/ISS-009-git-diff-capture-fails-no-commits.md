# Issue: Git diff capture fails - auto-commit not working

**ID:** ISS-009
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** 9
- **Story:** 9-2, 9-3
- **Component:** Git Integration

## Description

During the BUILD phase, the git diff capture fails with "Git diff command failed / Could not capture git diff". This occurs because the LLM creates new files but they are not committed, so `git diff HEAD~1` has nothing to diff against.

The auto-commit feature from Story 9.2 should stage and commit changes after each phase, but it's either not running or not handling untracked files.

## Reproduction Steps

1. Run `adw init` in a fresh project
2. Run `adw run "Create hello world command"`
3. Observe during BUILD phase: "Git diff command failed"
4. Check worktree after run:
   - `git log` shows no new commits
   - `git status` shows untracked files (not staged)

## Expected Behavior

After BUILD phase:
1. All created/modified files should be staged
2. A commit should be created: `[adw] Build: <feature-name>`
3. Git diff should capture the changes from that commit

## Actual Behavior

- Files are created but remain untracked
- No commit is made
- Git diff fails because there's no commit to diff against
- "Git diff command failed" / "Could not capture git diff" shown in output

## Impact

- PR description lacks diff information
- No incremental commits for recovery
- Git history doesn't reflect ADW work

## User Impact Score

- **Users Affected:** All users with git integration enabled
- **Frequency:** Every run

## Workaround

None - manual commits would defeat the purpose of automation.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0

## Evidence

### Console Output

```
⠹ LLM executing... · Tokens: 3662 · 0:02:03
Git diff command failed
Could not capture git diff
✓ BUILD completed (123.7s, 2 artifacts, 3662 tokens)
```

### Git Status in Worktree

```bash
$ cd trees/01KE6YXDTRCSZHKXTZWA32JSYC
$ git status
On branch adw/01KE6YXDTRCSZHKXTZWA32JSYC
Untracked files:
  docs/
  src/
  tests/

nothing added to commit but untracked files present

$ git log --oneline -1
442bc50 (HEAD -> adw/01KE6..., main) Initial commit
```

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Story 9.2 acceptance criteria states:
> **Given** Build phase completes successfully
> **When** post-hook runs
> **Then** changed files are staged and committed with message "[adw] Build: <feature>"

This is not happening. The post-hook either:
1. Isn't being triggered
2. Only stages modified files, not untracked files
3. Has a bug preventing commits

Need to investigate `src/adw/hooks/` or wherever post-phase hooks are implemented.
