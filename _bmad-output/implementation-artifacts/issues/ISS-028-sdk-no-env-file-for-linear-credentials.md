# Issue: SDK does not auto-load .env for Linear credentials

**ID:** ISS-028
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-19
**Reporter:** Ivo

## Related

- **Epic:** Epic 12 (Task Manager Integration)
- **Story:** N/A
- **Component:** Task Manager / Configuration

## Description

The Linear task manager requires `LINEAR_API_KEY` and `LINEAR_TEAM_ID` environment variables, but the SDK does not auto-load any `.env` file. The error messages misleadingly suggest "Add LINEAR_API_KEY to your .env file" when the SDK doesn't actually load `.env` files at all.

This creates confusion for multi-project use:
- Different projects may use different Linear workspaces (different API keys)
- Different projects definitely have different team IDs
- Mixing ADW credentials in the project's own `.env` file (used for app config like database URLs) is problematic and confusing

## Reproduction Steps

1. Run `adw init` in a new project
2. Configure task_manager type as "linear" in `.adw/project.yaml`
3. Run `adw run "test feature"` without setting environment variables
4. Observe error: "LINEAR_API_KEY environment variable is not set" with suggestion "Add LINEAR_API_KEY to your .env file"
5. Create a `.env` file in project root with the credentials
6. Run `adw run "test feature"` again
7. Same error occurs - SDK does not load the `.env` file

## Expected Behavior

- ADW should have a dedicated `.adw/.env` file for ADW-specific credentials
- This file should be created (with placeholder template) during `adw init`
- The SDK should auto-load `.adw/.env` before any command runs
- The `.adw/.env` file should be gitignored by default
- Error messages should correctly reference `.adw/.env` not just ".env file"

## Actual Behavior

- No `.env` file loading mechanism exists in the SDK
- Credentials must be set as shell environment variables (export or direnv)
- Error message suggests ".env file" but SDK doesn't load it
- No project-specific credential isolation for multi-project ADW users

## Impact

Users cannot easily configure Linear credentials per-project. They must either:
1. Set global shell environment variables (only one Linear workspace possible)
2. Use direnv with `.envrc` files (requires extra tooling)
3. Manually source a `.env` file before each ADW command

This is especially problematic for developers working on multiple projects with different Linear workspaces.

## User Impact Score

- **Users Affected:** All users using Linear integration
- **Frequency:** Every project setup

## Workaround

Use `direnv` with a project-level `.envrc` file:
```bash
# .envrc
export LINEAR_API_KEY=lin_api_xxxxx
export LINEAR_TEAM_ID=your-team-uuid
```
Then run `direnv allow` in the project directory.

Alternatively, export variables in shell profile for single-workspace use.

## Environment

- **OS:** macOS / Linux / Windows
- **App Version:** 0.1.18
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

Relevant code locations:
- `src/adw/task_managers/linear.py:64-81` - `_get_api_key()` reads from `os.environ.get()`
- `src/adw/task_managers/linear.py:83-100` - `_get_team_id()` reads from `os.environ.get()`
- No `python-dotenv` or similar in `pyproject.toml` dependencies

### Screen Recording

N/A

## Resolution

- **Fix Story:** [ux-fix-ISS-028-env-file-for-credentials](../stories/ux-fix-ISS-028-env-file-for-credentials.md)
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

Proposed implementation:
1. Add `python-dotenv` to dependencies
2. Load `.adw/.env` early in CLI bootstrap (app.py callback)
3. Create `.adw/.env` template during `adw init`
4. Add `.env` to `.adw/.gitignore`
5. Update error messages to reference `.adw/.env`

This keeps ADW credentials separate from project app credentials and supports multi-project/multi-workspace use cases.
