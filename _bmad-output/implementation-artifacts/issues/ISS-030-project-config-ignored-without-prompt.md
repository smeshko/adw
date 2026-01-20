# Issue: Project command config.yaml ignored without prompt.md

**ID:** ISS-030
**Severity:** Critical
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-20
**Reporter:** Ivo

## Related

- **Epic:** N/A
- **Story:** N/A
- **Component:** Command Resolution / Phase Runner

## Description

Project-level `.adw/commands/{phase}/config.yaml` is completely ignored if the directory doesn't contain a `prompt.md` file. The `CommandResolver._is_valid_command_dir()` method requires `prompt.md` to exist for a directory to be considered a valid command directory. This causes the resolver to fall back to bundled defaults even when the user has explicitly configured overrides.

The expectation is that projects should NOT need their own custom prompt to override configuration. A project-specific command config should ALWAYS be read and merged with the resolved command's configuration.

**Root Cause:** `src/adw/commands/resolver.py:92-94`
```python
def _is_valid_command_dir(self, path: Path) -> bool:
    if not path.is_dir():
        return False
    return (path / "prompt.md").is_file()  # Too strict - ignores config-only dirs
```

## Reproduction Steps

1. Run `adw init` on a project
2. Create `.adw/commands/ship/config.yaml` with content: `enabled: false`
3. Do NOT create `.adw/commands/ship/prompt.md`
4. Run `adw run <feature>`
5. Observe ship phase runs despite being explicitly disabled in project config

## Expected Behavior

Project-level `config.yaml` should be read and merged with the resolved command's config, allowing users to override settings (like `enabled`, `timeout_seconds`) without providing a custom prompt. The resolution flow should be:

```
Command resolution: project/ship/prompt.md? -> user/ship/prompt.md? -> bundled/ship/prompt.md
Config resolution:  project/ship/config.yaml? -> merge with resolved command's config
```

## Actual Behavior

1. Resolver checks project tier: `.adw/commands/ship/` exists but has no `prompt.md`
2. Resolver considers directory invalid, skips it entirely
3. Resolver falls back to bundled ship command (which has `enabled: true` by default)
4. Project-level `config.yaml` with `enabled: false` is completely ignored
5. Ship phase runs when it should have been skipped

## Impact

- Users cannot disable phases without duplicating entire command prompts
- Users cannot configure phase timeouts without duplicating prompts
- Silent failure with no warning that config was ignored
- Unexpected phase execution leading to failed runs
- Blocks users from customizing workflow behavior

## User Impact Score

- **Users Affected:** All users attempting to customize phase behavior
- **Frequency:** Every run where project-level config overrides are needed

## Workaround

Copy the entire bundled command directory (including `prompt.md`) to the project's `.adw/commands/{phase}/` directory, then modify `config.yaml`. This is cumbersome and defeats the purpose of configuration layering.

## Environment

- **OS:** macOS / Linux / Windows
- **App Version:** 0.1.19
- **DPI Scaling:** N/A (CLI)

## Evidence

### Screenshots

N/A

### Logs

```
# Ship phase ran despite enabled: false in project config
✓ plan -> ✓ build -> ✓ validate -> ✓ document -> ► ship  80%
04:29:03 [INFO ] [phase] Starting phase
04:29:03 [INFO ] [phase] Phase starting
04:29:04 [ERROR] [phase] Pre-hook failed
```

### Screen Recording

N/A

## Resolution

- **Fix Story:** bugfix-ISS-030-project-config-ignored-without-prompt.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Proposed Fix

**Option A: Two-tier config resolution (Recommended)**
- Keep command resolution as-is (prompt.md required for full override)
- Add separate config resolution in `PhaseRunner` that checks project -> user -> bundled for `config.yaml`
- Merge project config on top of resolved command's config in `PhaseRunner._load_command_config()`

## Notes

This issue was discovered when running ADW on project-rulebook-be. The project had `.adw/commands/ship/config.yaml` with `enabled: false` but ship phase still attempted to run, failing on the pre-hook which validates PR existence.
