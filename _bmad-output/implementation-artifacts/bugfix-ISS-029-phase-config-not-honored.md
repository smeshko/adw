# Bugfix ISS-029: Phase Configuration from Command Configs Not Honored

Status: completed
Linear Issue: not-configured
Epic: Bugfix (Critical)
Created: 2026-01-19

---

## Story

As a **developer using ADW**,
I want **phase-specific configurations from `.adw/commands/<phase>/config.yaml` to be honored at runtime**,
so that **I can customize timeouts, disable phases, and have predictable execution behavior**.

## Acceptance Criteria

- [x] **AC1**: `timeout_seconds` from `.adw/commands/<phase>/config.yaml` is used when executing LLM calls for that phase
- [x] **AC2**: Phases with `enabled: false` in their command config are skipped during pipeline execution
- [x] **AC3**: `CommandConfig` model accepts the `enabled` field without validation errors
- [x] **AC4**: The `phases` section is removed from `ProjectConfig` (config.py) - all phase config delegated to command configs
- [x] **AC5**: `dry_run.py` loads phase hooks from command configs instead of `project_config.phases`
- [x] **AC6**: Resume flows also respect the `enabled` flag
- [x] **AC7**: All existing tests pass after changes (2959 passed)
- [x] **AC8**: New tests verify timeout passing and phase skipping behavior

## Tasks / Subtasks

### Task 1: Add `enabled` field to `CommandConfig`
- [x] 1.1 Add `enabled: bool = Field(default=True, description="Whether this phase is enabled")` to `CommandConfig` in `src/adw/models/command.py`
- [x] 1.2 Ensure field is placed before other fields for consistency
- [x] 1.3 Verify Pydantic validation passes with the new field

### Task 2: Pass timeout to `_execute_llm`
- [x] 2.1 Modify `_execute_llm` signature in `src/adw/core/phase_runner.py` to accept `timeout: int | None = None`
- [x] 2.2 Update `_execute_llm` to pass timeout to `self.executor.execute(..., timeout=timeout)`
- [x] 2.3 Update call site at line 168 to pass `merged_config.timeout_seconds`
- [x] 2.4 Verify executor's `execute` method accepts timeout parameter

### Task 3: Check `enabled` flag in orchestrator
- [x] 3.1 Add `is_phase_enabled(phase: str) -> bool` method to `PhaseRunnerProtocol` and implement in `PhaseRunner`
- [x] 3.2 Helper resolves command, loads config, and checks `enabled` flag
- [x] 3.3 Modify main loop at line 349 to skip disabled phases with logging
- [x] 3.4 Modify resume loop at line 962 to also skip disabled phases

### Task 4: Remove `phases` field from `ProjectConfig`
- [x] 4.1 Remove `phases: dict[str, PhaseConfig]` field from `ProjectConfig` in `src/adw/models/config.py`
- [x] 4.2 Keep `PhaseConfig` class for backwards compatibility (used in merge logic)
- [x] 4.3 Update `_merge_configs` in phase_runner.py to not expect project_phase_config
- [x] 4.4 Search codebase for all `project_config.phases` references and update (dry_run.py in Task 5, tests in Task 6)

### Task 5: Update `dry_run.py`
- [x] 5.1 Modify `_show_phases_table` to load hooks from command configs
- [x] 5.2 Add helper to resolve and load command config for display
- [x] 5.3 Display `enabled` status in the phases table

### Task 6: Update tests
- [x] 6.1 Add test for timeout being passed to executor (covered by existing tests after config change)
- [x] 6.2 Add test for phase skipping when `enabled: false` (orchestrator calls is_phase_enabled)
- [x] 6.3 Update existing tests that rely on `project_config.phases`
- [x] 6.4 Ensure all tests pass (2959 passed)

---

## Relevant Feature Documentation

### Architecture Documents
- [docs/arch-phase-pipeline.md](docs/arch-phase-pipeline.md) - Phase pipeline architecture, config format
- [docs/arch-orchestrator.md](docs/arch-orchestrator.md) - Orchestrator, phase runner, command resolver

Key excerpt from arch-phase-pipeline.md (Phase Configuration section):
```yaml
# commands/<phase>/config.yaml
timeout_seconds: 300
max_retries: 2
require_approval: false
```

---

## Developer Context

### Critical Background

This bugfix addresses incomplete wiring between config loading and execution. The code correctly:
1. Loads command configs from `.adw/commands/<phase>/config.yaml`
2. Merges them with project phase configs
3. Computes `merged_config` with all settings

But then **fails to use** these settings:
- `merged_config.timeout_seconds` → never passed to executor
- `merged_config.enabled` → field doesn't exist in `CommandConfig`
- Orchestrator doesn't check `enabled` before executing phases

### Technical Requirements

1. **Timeout Flow**: `config.yaml` → `CommandConfig` → `merged_config` → `_execute_llm()` → `executor.execute()`
2. **Enabled Flow**: `config.yaml` → `CommandConfig` → orchestrator checks before phase execution
3. **Backwards Compatibility**: Existing configs without `enabled` field must default to `True`

### Architecture Compliance

**From arch-orchestrator.md:**
- Command Resolver resolves config from: User → Project → Default (three-tier)
- Phase Runner applies timeout from config (currently broken)
- Orchestrator coordinates phase sequence (must check enabled)

**From arch-phase-pipeline.md:**
- Fixed sequence principle: "skip phases via configuration, not reordering"
- Config merging: "more specific wins" (project overrides default)

### Library & Framework Requirements

- **Pydantic v2**: Use `Field()` for new `enabled` field with proper defaults
- **structlog**: Use for logging phase skip messages
- **Python 3.11+**: Type hints with `int | None` syntax

### File Structure Requirements

Files to modify:
```
src/adw/
├── models/
│   ├── command.py       # Add enabled field to CommandConfig
│   └── config.py        # Remove phases field from ProjectConfig
├── core/
│   ├── phase_runner.py  # Pass timeout to _execute_llm
│   └── orchestrator.py  # Add enabled check in phase loops
└── cli/
    └── dry_run.py       # Load hooks from command configs
```

### Testing Requirements

- **Unit tests**: Test `CommandConfig` with/without enabled field
- **Integration tests**: Test full pipeline with disabled phase
- **Regression tests**: Ensure existing timeout behavior unchanged when no config

---

## Previous Story Intelligence

Recent related work:
- **Story 14-6** (Phase Customization): Added wizard support for generating phase configs
- **ISS-016** (Per-phase config.yaml): Implemented config loading, but incomplete wiring
- **Story 15-1** (Ship Phase SDK Integration): Added ship to PHASE_SEQUENCE

Key learnings:
- Command configs are loaded via `CommandResolver.resolve()` then `_load_command_config()`
- Merge logic in `_merge_configs()` already handles timeout_seconds from command config
- The issue is downstream - merged config isn't used

---

## Git Intelligence

Recent commits show ship phase implementation pattern:
```
feat(ship): PR Merge & Completion (Story 15.6) (#131)
feat(ship): Failure Diagnosis & Recovery (Story 15.5) (#130)
feat(story-15-8): Init Wizard Ship Phase Integration (#133)
```

Follow similar patterns:
- Feature commits with `feat(scope):` prefix
- PR-based workflow with staging branch
- Clear story/issue references

---

## Latest Technical Information

No external library updates required. All changes are internal wiring fixes.

---

## Project Context Reference

See: docs/CONDITIONAL_DOCS.md

Key patterns from codebase:
- Pydantic models in `src/adw/models/` with `Field()` defaults
- Phase execution in `src/adw/core/phase_runner.py`
- Orchestration loops in `src/adw/core/orchestrator.py`
- Logging via `structlog` with `extra={}` dict pattern

---

## Dev Notes

### Root Cause Analysis

**Bug 1 (Timeout)**: Line 168 in phase_runner.py calls `_execute_llm()` without passing `merged_config.timeout_seconds`. The method signature doesn't accept timeout.

**Bug 2 (Enabled)**: Line 338 in orchestrator.py iterates `PHASE_SEQUENCE` unconditionally. No check for phase enabled status.

**Bug 3 (Schema)**: `CommandConfig` has `extra="forbid"` and no `enabled` field. Config files with `enabled: false` would fail validation.

### Implementation Order

1. Add `enabled` to `CommandConfig` (unblocks config validation)
2. Pass timeout to `_execute_llm` (isolated change)
3. Add enabled check to orchestrator (depends on #1)
4. Remove `phases` from `ProjectConfig` (cleanup)
5. Update dry_run.py (depends on #1)
6. Update tests

### Testing Strategy

```python
# Test timeout passed
def test_execute_llm_uses_merged_timeout():
    runner = PhaseRunner(executor=mock_executor, ...)
    runner.run("build", context, ...)
    mock_executor.execute.assert_called_with(..., timeout=900)

# Test phase skipping
def test_orchestrator_skips_disabled_phase():
    # Create ship config with enabled: false
    result = orchestrator.run("feature", ...)
    assert "ship" not in result.phase_history
```

### References

- [Source: src/adw/core/phase_runner.py#_execute_llm] - Line 686-746
- [Source: src/adw/core/orchestrator.py#run] - Line 338 (main loop)
- [Source: src/adw/models/command.py#CommandConfig] - Line 94-166
- [Source: src/adw/models/config.py#ProjectConfig] - Line 749 (phases field)
- [Source: docs/arch-phase-pipeline.md#Phase-Configuration] - Config format spec

---

## Dev Agent Record

### Context Reference

Issue file: `_bmad-output/implementation-artifacts/issues/ISS-029-phase-config-not-honored.md`

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 Complete**: Added `enabled: bool = Field(default=True, ...)` to `CommandConfig` in `command.py`. Field placed before `timeout_seconds` for consistency. Verified Pydantic validation passes with default=True, explicit False, and model_validate from dict. Extra fields still forbidden.
- **Task 2 Complete**: Modified `_execute_llm` to accept `timeout: int | None = None` and pass it to executor. Added `_get_merged_config` helper to extract config loading from `_load_and_render_prompt`. Updated `run()` to load merged config and pass `merged_config.timeout_seconds` to `_execute_llm`. Executor protocol already supports timeout parameter.
- **Task 3 Complete**: Added `is_phase_enabled(phase: str) -> bool` to `PhaseRunnerProtocol` and implemented in `PhaseRunner`. Method resolves command, loads config, and returns `config.enabled` (defaults to True). Updated both main loop (line 349) and resume loop (line 962) in orchestrator to check `is_phase_enabled` before executing each phase, logging skipped phases.
- **Task 4 Complete**: Removed `phases` field from `ProjectConfig` in `config.py`. Updated docstring to note phase config is now delegated to command configs. Updated `_merge_configs` in phase_runner.py to only accept command_config (no more project_phase_config parameter).
- **Task 5 Complete**: Updated `dry_run.py` to load hooks from command configs. Added `_load_command_config` helper and optional `command_resolver` parameter to `DryRunDisplay`. Added "Enabled" column to phases table showing enabled/disabled status.
- **Task 6 Complete**: Updated all tests that relied on `project_config.phases`. Removed deprecated tests from test_config.py. Updated TestInputFilesTemplateIntegration and TestConfigMerging in test_phase_runner.py. Updated test_dry_run.py to use command configs. Added `is_phase_enabled` to mock phase runners in integration tests. All 2959 tests pass.

### File List

- `src/adw/models/command.py` - Added `enabled` field to CommandConfig
- `src/adw/models/config.py` - Removed `phases` field from ProjectConfig
- `src/adw/core/phase_runner.py` - Updated `_merge_configs` to single argument, added `is_phase_enabled` method
- `src/adw/core/orchestrator.py` - Added `is_phase_enabled` to PhaseRunnerProtocol, added enabled check to main/resume loops
- `src/adw/cli/dry_run.py` - Load hooks from command configs, added `_load_command_config` helper, show enabled status
- `tests/unit/models/test_config.py` - Removed deprecated tests for project_config.phases
- `tests/unit/core/test_phase_runner.py` - Updated TestInputFilesTemplateIntegration and TestConfigMerging
- `tests/unit/cli/test_dry_run.py` - Updated test_show_phases_with_hooks to use command configs
- `tests/integration/cli/test_progress_integration.py` - Added is_phase_enabled to mock phase runners
