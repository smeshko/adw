# Bugfix ISS-030: Project command config.yaml ignored without prompt.md

Status: complete
Linear Issue: not-configured
Epic: Bugfix (Critical)
Created: 2026-01-20

---

## Story

As a **developer using ADW**,
I want **project-level `.adw/commands/<phase>/config.yaml` to be loaded and merged with the resolved command's configuration even when no `prompt.md` file exists in the project directory**,
so that **I can customize phase settings (like `enabled: false`, `timeout_seconds`) without having to duplicate the entire bundled command prompt**.

## Acceptance Criteria

- [x] **AC1**: Project-level `config.yaml` files are read from `.adw/commands/<phase>/config.yaml` regardless of whether `prompt.md` exists in that directory
- [x] **AC2**: When a project has only `config.yaml` (no `prompt.md`), the command resolution still uses the bundled prompt but merges the project's config
- [x] **AC3**: Config resolution follows the hierarchy: project config → user config → bundled config (layered merge)
- [x] **AC4**: A phase can be disabled by creating `.adw/commands/<phase>/config.yaml` with `enabled: false` without any `prompt.md`
- [x] **AC5**: Phase timeout can be overridden via project config without duplicating the prompt
- [x] **AC6**: All existing tests pass (2959+ tests)
- [x] **AC7**: New unit tests verify the separate config resolution path
- [x] **AC8**: Integration test demonstrates disabling a phase with config-only directory

## Tasks / Subtasks

### Task 1: Implement Two-Tier Config Resolution in PhaseRunner

**Purpose**: Load project-level config.yaml separately from command resolution.

- [x] 1.1 Add `_load_project_config(phase: str) -> CommandConfig | None` method to `PhaseRunner`
- [x] 1.2 Method checks `{project_root}/.adw/commands/{phase}/config.yaml` directly (bypass command resolution)
- [x] 1.3 Returns parsed `CommandConfig` if file exists, `None` otherwise
- [x] 1.4 Update `_get_merged_config` to call `_load_project_config` and merge on top of resolved command's config

### Task 2: Update _get_merged_config to Merge Layered Configs

**Purpose**: Implement proper config layering - project config overrides resolved command config.

- [x] 2.1 Modify `_get_merged_config` to accept optional `project_config: CommandConfig | None`
- [x] 2.2 Implement merge logic: command config values, then project config overrides
- [x] 2.3 For dict fields (`input_files`), merge with project values taking precedence
- [x] 2.4 For scalar fields (`enabled`, `timeout_seconds`), project value wins if set

### Task 3: Update is_phase_enabled to Check Project Config

**Purpose**: Phase enabled check must consider project config override.

- [x] 3.1 Update `is_phase_enabled` to also call `_load_project_config`
- [x] 3.2 If project config has `enabled` set, it overrides command config
- [x] 3.3 Return False if either config disables the phase

### Task 4: Add Unit Tests

**Purpose**: Verify config resolution works correctly.

- [x] 4.1 Test `_load_project_config` returns config when file exists
- [x] 4.2 Test `_load_project_config` returns None when file doesn't exist
- [x] 4.3 Test `_get_merged_config` properly merges project config over command config
- [x] 4.4 Test `is_phase_enabled` respects project config override
- [x] 4.5 Test timeout_seconds from project config is used

### Task 5: Add Integration Test

**Purpose**: End-to-end test demonstrating the fix.

- [x] 5.1 Create test fixture with `.adw/commands/ship/config.yaml` containing `enabled: false` (no prompt.md)
- [x] 5.2 Test that ship phase is skipped during pipeline execution
- [x] 5.3 Test that other phases still execute normally with bundled commands

---

## Relevant Feature Documentation

### From docs/arch-orchestrator.md - Command Resolver Config Merging Section

```yaml
# defaults/commands/build/config.yaml (built-in)
timeout: 300
max_retries: 2

# .agent/commands/build/config.yaml (project override)
timeout: 600  # Override: longer timeout for this project

# Final merged config:
# timeout: 600
# max_retries: 2
```

**Key insight**: Architecture documents show config merging where "more specific wins". Current implementation only applies this when project has FULL command override (with prompt.md).

### From docs/arch-phase-pipeline.md - Phase Configuration Section

```yaml
# commands/<phase>/config.yaml
timeout_seconds: 300
max_retries: 2
require_approval: false
```

**Key insight**: The architecture supports per-phase config files for customization without requiring prompt duplication.

---

## Developer Context

### Critical Background - Root Cause Analysis

**The Bug**: `CommandResolver._is_valid_command_dir()` requires `prompt.md` to exist:

```python
# src/adw/commands/resolver.py:92-94
def _is_valid_command_dir(self, path: Path) -> bool:
    if not path.is_dir():
        return False
    return (path / "prompt.md").is_file()  # TOO STRICT
```

This causes the three-tier resolution to skip project directories that only contain `config.yaml`.

**Current Flow (Broken)**:
```
1. Resolver checks project/.adw/commands/ship/ → has config.yaml but NO prompt.md
2. Resolver considers directory INVALID, skips entirely
3. Resolver falls back to bundled/commands/ship/ (has both)
4. PhaseRunner loads config from bundled command only
5. Project config.yaml with enabled: false is IGNORED
6. Ship phase runs when it should be skipped
```

**Expected Flow (After Fix)**:
```
1. Resolver resolves command from bundled (or user) tier → gets prompt.md path
2. PhaseRunner loads command config from resolved tier
3. PhaseRunner ALSO checks project/.adw/commands/ship/config.yaml
4. PhaseRunner merges: bundled config + project config override
5. Project's enabled: false takes precedence
6. Ship phase is correctly skipped
```

### Technical Requirements

1. **DO NOT modify CommandResolver**: The resolver's job is to find the prompt.md. Config resolution is a separate concern.
2. **Config loading in PhaseRunner**: PhaseRunner already loads command config via `_load_command_config`. Add project config loading alongside.
3. **Merge strategy**: Project config values override command config values (when not None).
4. **Backwards compatibility**: Existing behavior must work - projects with full command overrides (prompt.md + config.yaml) still take precedence.

### Architecture Compliance

**Command Resolution (UNCHANGED)**:
```
User Override → Project Override → Default → [Resolved Prompt]
               (requires prompt.md)
```

**Config Resolution (NEW - in PhaseRunner)**:
```
Project Config → merge with → Resolved Command Config → [Merged PhaseConfig]
(.adw/commands/{phase}/config.yaml)    (wherever prompt was resolved from)
```

**Key Architectural Principle**: Separation of concerns:
- CommandResolver: Finds the prompt.md (full command resolution)
- PhaseRunner: Applies configuration (can layer project config on top)

### Library & Framework Requirements

- **Pydantic v2**: Use existing `CommandConfig.model_validate()` for parsing
- **PyYAML**: Use `yaml.safe_load()` for YAML parsing (already used in `_load_command_config`)
- **pathlib**: Use `Path` for all file operations
- **Python 3.11+**: Type hints with `| None` syntax

### File Structure Requirements

**Files to Modify**:
```
src/adw/
├── core/
│   └── phase_runner.py    # Add _load_project_config, update _get_merged_config
└── (no other files need changes)
```

**Test Files to Add/Modify**:
```
tests/
├── unit/core/
│   └── test_phase_runner.py    # Add config resolution tests
└── integration/
    └── test_config_override.py  # New integration test (optional)
```

### Testing Requirements

**Unit Tests** (in `tests/unit/core/test_phase_runner.py`):
```python
class TestProjectConfigLoading:
    def test_load_project_config_exists(self):
        """Project config is loaded when file exists."""

    def test_load_project_config_not_exists(self):
        """Returns None when no project config file."""

    def test_load_project_config_invalid_yaml(self):
        """Raises ConfigError for invalid YAML."""

class TestConfigMerging:
    def test_merge_project_overrides_command(self):
        """Project config values override command config."""

    def test_merge_preserves_command_when_project_not_set(self):
        """Command config values kept when project doesn't override."""

    def test_merge_input_files_dict(self):
        """Input files dict is merged, project takes precedence."""

class TestPhaseEnabledWithProjectConfig:
    def test_phase_enabled_respects_project_config(self):
        """is_phase_enabled returns False when project config disables."""
```

**Integration Test** (demonstrates real scenario):
```python
def test_disable_phase_via_config_only():
    """Phase can be disabled via config.yaml without prompt.md."""
    # Create .adw/commands/ship/config.yaml with enabled: false
    # Run pipeline
    # Assert ship phase was skipped
```

---

## Previous Story Intelligence

### ISS-029 Fix (Completed - Reference Pattern)

The ISS-029 fix modified the same code area. Key learnings:

1. **`_get_merged_config` helper added**: This method already exists and loads config from resolved command. Extend it to also load project config.

2. **`_load_command_config` pattern**: Use same pattern for `_load_project_config`:
```python
def _load_command_config(self, command: ResolvedCommand) -> CommandConfig | None:
    config_path = command.path / "config.yaml"
    if not config_path.exists():
        return None
    # Parse and return
```

3. **`is_phase_enabled` location**: This method is in `PhaseRunner` and calls `_load_command_config`. Update it to also check project config.

4. **Test patterns**: ISS-029 tests show how to mock config loading and test phase skipping.

### Related Files from ISS-029 Fix

```
src/adw/core/phase_runner.py - Lines 555-578: _get_merged_config
src/adw/core/phase_runner.py - Lines 580-606: is_phase_enabled
src/adw/core/phase_runner.py - Lines 516-553: _load_command_config
```

---

## Git Intelligence

### Recent Commit Pattern (ISS-029)

```
fix(ISS-029): Honor phase configuration from command configs (#135)
```

Follow similar pattern:
```
fix(ISS-030): Load project config.yaml without requiring prompt.md
```

### Files Changed in ISS-029 (Reference)

```
src/adw/core/phase_runner.py  # Primary changes here
```

This fix is similar - focused primarily on `phase_runner.py`.

---

## Latest Technical Information

No external library updates required. All changes are internal wiring in existing modules.

**Pydantic v2 Merge Pattern**:
```python
# Merge configs with project overriding command
merged_data = command_config.model_dump(exclude_unset=True)
if project_config:
    for key, value in project_config.model_dump(exclude_unset=True).items():
        if value is not None:  # Only override if explicitly set
            merged_data[key] = value
```

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns from codebase:

1. **Exception handling**: Use `ConfigError` with code/message/suggestion
2. **Logging**: Use `logger.debug()` with extra dict for structured logging
3. **Type hints**: Full annotations, `| None` syntax
4. **File operations**: Use `Path` objects, UTF-8 encoding

---

## Dev Notes

### Implementation Order

1. **Add `_load_project_config`** (isolated, testable)
2. **Update `_get_merged_config`** (integrate project config)
3. **Update `is_phase_enabled`** (use new merge logic)
4. **Add unit tests** (verify each piece)
5. **Add integration test** (verify end-to-end)

### Merge Logic Detail

```python
def _merge_with_project_config(
    self,
    command_config: CommandConfig | None,
    project_config: CommandConfig | None,
) -> PhaseConfig:
    """Merge command config with project config overlay.

    Project config values override command config values when set.
    """
    merged_data: dict[str, Any] = {}

    # Start with command config values
    if command_config:
        if command_config.timeout_seconds is not None:
            merged_data["timeout_seconds"] = command_config.timeout_seconds
        if command_config.input_files is not None:
            merged_data["input_files"] = dict(command_config.input_files)
        # ... other fields

    # Override with project config values (when set)
    if project_config:
        if project_config.timeout_seconds is not None:
            merged_data["timeout_seconds"] = project_config.timeout_seconds
        if project_config.enabled is not True:  # Only if explicitly disabled
            # Handle enabled flag specially - it affects phase execution
            pass
        if project_config.input_files is not None:
            # Merge dicts, project takes precedence
            existing = merged_data.get("input_files", {})
            merged_data["input_files"] = {**existing, **project_config.input_files}

    return PhaseConfig(**merged_data) if merged_data else PhaseConfig()
```

### Project Root Detection

PhaseRunner already has access to project root via:
- `self.project_config` (if set) has project info
- `context.worktree_path` for worktree-isolated runs
- Fall back to `Path.cwd()` if neither available

For config loading:
```python
def _load_project_config(self, phase: str) -> CommandConfig | None:
    """Load project-level config.yaml for a phase (if exists)."""
    # Determine project root
    project_root = Path.cwd()  # Or from self.project_config if available

    config_path = project_root / ".adw" / "commands" / phase / "config.yaml"

    if not config_path.exists():
        return None

    # Parse using same pattern as _load_command_config
    try:
        config_content = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(config_content)
        if data is None:
            data = {}
        return CommandConfig.model_validate(data)
    except yaml.YAMLError as e:
        raise ConfigError(
            code="INVALID_CONFIG",
            message=f"Invalid YAML in project config at {config_path}: {e}",
        ) from e
    except ValidationError as e:
        raise ConfigError(
            code="INVALID_CONFIG",
            message=f"Invalid config in project config at {config_path}: {e}",
        ) from e
```

### Edge Cases to Handle

1. **Both project and command config exist**: Merge correctly
2. **Only project config exists**: Load project config, merge with empty command config
3. **Neither exists**: Return empty PhaseConfig (existing behavior)
4. **Invalid project config YAML**: Raise ConfigError with helpful message
5. **Worktree runs**: Use worktree path as project root

### References

- [Source: src/adw/commands/resolver.py#_is_valid_command_dir] - Line 79-94 (root cause)
- [Source: src/adw/core/phase_runner.py#_get_merged_config] - Lines 555-578
- [Source: src/adw/core/phase_runner.py#_load_command_config] - Lines 516-553
- [Source: src/adw/core/phase_runner.py#is_phase_enabled] - Lines 580-606
- [Source: docs/arch-orchestrator.md#Config-Merging] - Architecture spec
- [Source: _bmad-output/implementation-artifacts/issues/ISS-030-project-config-ignored-without-prompt.md] - Issue details

---

## Dev Agent Record

### Context Reference

Issue file: `_bmad-output/implementation-artifacts/issues/ISS-030-project-config-ignored-without-prompt.md`

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

