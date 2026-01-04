# Issue: Dry-run mode shows minimal output instead of execution preview

**ID:** ISS-002
**Severity:** Major
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-04
**Reporter:** Ivo

## Related

- **Epic:** 6
- **Story:** 6-1
- **Component:** CLI

## Description

The `--dry-run` flag implementation at `src/adw/cli/app.py:186-188` is incomplete. The help text promises "Show what would happen without executing" but the implementation only prints a message and exits immediately.

Current implementation:
```python
if dry_run:
    console.print("[yellow]Dry run mode - no execution[/]")
    return
```

This is a gap between documented behavior and actual functionality.

## Reproduction Steps

1. Run `adw run --dry-run "any feature description"`
2. Observe minimal output

## Expected Behavior

The dry-run mode should display:
1. Phases to execute (all 5 default phases, or just the --phase specified)
2. Hooks that would run (pre/post for each phase)
3. Config being used (project language, test commands, etc.)
4. From-run artifacts (if --from-run specified)

## Actual Behavior

Prints `[yellow]Dry run mode - no execution[/]` and returns immediately without showing any execution preview information.

## Impact

Users cannot preview the execution plan before committing to a run. This prevents:
- Verifying correct phase selection
- Checking hook configuration
- Validating project config before execution
- Understanding what artifacts would be used from previous runs

## User Impact Score

- **Users Affected:** All users using --dry-run flag
- **Frequency:** Every dry-run invocation

## Workaround

None - users must run actual execution to see what happens, which defeats the purpose of dry-run.

## Environment

- **OS:** Windows 10/11
- **App Version:** 0.1.0-dev
- **DPI Scaling:** 100%

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-002-dry-run-minimal-output.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This appears to be incomplete implementation rather than a regression. The feature was scaffolded but never fully implemented.
