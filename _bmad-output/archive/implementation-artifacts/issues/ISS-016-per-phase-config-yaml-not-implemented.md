# Issue: Per-phase config.yaml loading not implemented

**ID:** ISS-016
**Severity:** Major
**Type:** Missing Feature
**Status:** reported
**Reported:** 2026-01-06
**Reporter:** Ivo

## Related

- **Epic:** Epic 12 (Task Manager Integration / Tech Debt)
- **Story:** N/A
- **Component:** Command Resolution / Phase Configuration
- **Architecture Reference:** `_bmad-output/architecture.md` lines 857-879

## Description

The architecture document specifies that each phase command folder should contain a `config.yaml` file with phase-specific configuration, but this was never implemented. The command loader has no support for loading these files.

**Architecture specification (lines 857-879):**
```
├── defaults/commands/
│   ├── plan/
│   │   ├── prompt.md
│   │   ├── config.yaml    ← PLANNED but NOT IMPLEMENTED
│   │   └── schema.json
│   ├── build/
│   │   ├── prompt.md
│   │   ├── config.yaml    ← PLANNED but NOT IMPLEMENTED
│   │   ├── pre.sh
│   │   └── post.sh
│   ├── verify/
│   │   ├── prompt.md
│   │   └── config.yaml    ← PLANNED but NOT IMPLEMENTED
│   ...
```

**Actual implementation:**
- `src/adw/defaults/commands/plan/` - only has `prompt.md` and `pre.sh`
- `src/adw/defaults/commands/build/` - only has `prompt.md` and `post.sh`
- `src/adw/defaults/commands/verify/` - only has `prompt.md`
- No `config.yaml` files exist in any phase folder
- `src/adw/commands/loader.py` has no support for loading `config.yaml`

## Expected Behavior

Each phase command folder should support an optional `config.yaml` that defines:
- Default `input_files` for that phase
- Default timeout settings
- Default pre/post hooks
- Phase-specific LLM settings (model, temperature, etc.)
- Artifact capture rules (related to ISS-012)

Example `commands/plan/config.yaml`:
```yaml
# Default configuration for plan phase
timeout_seconds: 600

input_files:
  prd: "docs/prd.md"
  architecture: "docs/architecture.md"

llm:
  model: claude-sonnet-4-20250514
  temperature: 0.7
```

This config would be:
1. Loaded by CommandResolver/Loader when resolving a phase
2. Merged with project-level `adw.yaml` config (project overrides defaults)
3. Made available to PhaseRunner for execution

## Actual Behavior

- No `config.yaml` files exist in phase folders
- CommandResolver only looks for `prompt.md`, `pre.sh`, `post.sh`, `schema.json`
- Phase configuration must be entirely specified in project `adw.yaml`
- No way to bundle sensible defaults with commands

## Impact

1. **No bundled defaults:** Users must configure everything in `adw.yaml` even for common patterns
2. **No command portability:** Custom commands can't ship with their own configuration
3. **Inconsistent with architecture:** Implementation diverges from documented design
4. **Related to ISS-012:** The artifact capture refactoring (ISS-012) also plans to use `command.yaml` - these should be unified

## Related Issues

- **ISS-012:** Config-driven artifact capture (plans to add `command.yaml` for artifacts)
- **ISS-015:** Phase-specific input context (adds `input_files` to `adw.yaml` PhaseConfig) - FIXED

## Proposed Solution

### Option A: Implement `config.yaml` per phase (as architected)

1. Create `config.yaml` files in each `defaults/commands/*/` folder
2. Add `CommandConfig` model to parse config.yaml
3. Update `CommandResolver` to load and return config
4. Merge with project `adw.yaml` PhaseConfig in PhaseRunner
5. Update ISS-012 to use same config.yaml instead of separate `command.yaml`

### Option B: Extend `command.yaml` approach from ISS-012

1. Rename ISS-012's `command.yaml` concept to `config.yaml`
2. Extend schema to include all phase settings (not just artifacts)
3. Implement loading and merging in CommandResolver

**Recommendation:** Option A aligns with the original architecture and provides a cleaner separation. The `config.yaml` name is more intuitive than `command.yaml`.

## Files to Modify

| File | Changes |
|------|---------|
| `src/adw/commands/resolver.py` | Add config.yaml loading |
| `src/adw/commands/loader.py` | Add CommandConfig model parsing |
| `src/adw/models/command.py` | Add CommandConfig model |
| `src/adw/core/phase_runner.py` | Merge command config with phase config |
| `src/adw/defaults/commands/*/config.yaml` | Create default configs |

## Acceptance Criteria

- [ ] Each phase command folder can have an optional `config.yaml`
- [ ] CommandResolver loads and returns config alongside resolved command
- [ ] Config is merged with project `adw.yaml` (project takes precedence)
- [ ] Default `input_files`, `timeout_seconds`, hooks are respected
- [ ] Existing behavior preserved when no config.yaml exists
- [ ] All existing tests pass
- [ ] New tests cover config loading and merging

## Environment

- **OS:** macOS
- **App Version:** adw-sdk (development)
- **Architecture Doc:** `_bmad-output/architecture.md` lines 857-879, 1075

## Notes

This issue represents a gap between the documented architecture and actual implementation. The architecture was designed with extensibility in mind - commands should be self-contained packages with their own configuration. Currently, all configuration must live in project `adw.yaml`, limiting the reusability and portability of custom commands.
