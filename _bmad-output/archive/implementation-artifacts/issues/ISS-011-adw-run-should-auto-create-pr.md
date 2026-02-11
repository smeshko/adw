# Issue: adw run should automatically create PR when remote exists

**ID:** ISS-011
**Severity:** Minor
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-05
**Reporter:** Ivo

## Related

- **Epic:** 9
- **Story:** 9-5
- **Component:** Git Integration/PR Creation

## Description

After `adw run` completes successfully, the PR description is generated but the actual PR is not created. Users must run a separate `adw pr <run_id>` command. When a git remote exists and `gh` CLI is available, the PR should be created automatically as part of the run completion flow.

## Reproduction Steps

1. Run `adw init` in a project with git remote configured
2. Run `adw run "Create hello world command"`
3. Run completes, shows:
   ```
   PR Description: .adw/runs/.../artifacts/document/pr_description.md
   ```
4. No PR is created
5. Must manually run `adw pr <run_id>`

## Expected Behavior

When `adw run` completes successfully:
1. Check if git remote exists
2. Check if `gh` CLI is available
3. If both true, automatically create PR using generated description
4. Display PR URL in completion summary
5. If remote/gh not available, show current behavior (path to description)

## Actual Behavior

PR description is generated but PR is never created automatically. User must run separate command.

## Impact

- Extra manual step required after every run
- Breaks the "autonomous" workflow promise
- Users may forget to create PR

## User Impact Score

- **Users Affected:** All users wanting automated PRs
- **Frequency:** Every completed run

## Workaround

Run `adw pr <run_id>` after each successful run.

## Environment

- **OS:** macOS
- **App Version:** 0.1.0

## Evidence

### Current Output

```
╭─────────────────────────── Pipeline Summary ───────────────────────────╮
│ ✓ plan → ✓ build → ✓ verify → ✓ validate → ✓ document                  │
│                                                                         │
│ Status: completed                                                       │
│ Duration: 390.7s                                                        │
│ Tokens: 10,846                                                          │
│                                                                         │
│ PR Description: .adw/runs/.../artifacts/document/pr_description.md      │
╰─────────────────────────────────────────────────────────────────────────╯
```

### Expected Output

```
╭─────────────────────────── Pipeline Summary ───────────────────────────╮
│ ✓ plan → ✓ build → ✓ verify → ✓ validate → ✓ document                  │
│                                                                         │
│ Status: completed                                                       │
│ Duration: 390.7s                                                        │
│ Tokens: 10,846                                                          │
│                                                                         │
│ PR Created: https://github.com/org/repo/pull/123                        │
╰─────────────────────────────────────────────────────────────────────────╯
```

## Resolution

- **Fix Story:** Pending
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Implementation approach:
1. After document phase completes, check:
   - `git remote -v` returns a remote
   - `which gh` finds GitHub CLI
2. If checks pass:
   - Call the same logic as `adw pr <run_id>`
   - Display PR URL in summary
3. If checks fail:
   - Show current behavior (PR description path)
   - Optionally show hint: "Run 'adw pr <run_id>' to create PR"

Config option could be added:
```yaml
# .adw/project.yaml
git:
  auto_create_pr: true  # default: true if remote exists
```
