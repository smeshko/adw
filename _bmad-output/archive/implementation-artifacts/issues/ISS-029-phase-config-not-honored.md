# Issue: Phase Configuration from Command Configs Not Honored

**ID:** ISS-029
**Severity:** Critical
**Type:** Bug
**Status:** reported
**Reported:** 2026-01-19
**Reporter:** Ivo

## Related

- **Epic:** Epic 14 / Epic 15
- **Story:** N/A
- **Component:** Phase Configuration System (phase_runner.py, orchestrator.py, command.py)

## Description

Multiple critical bugs prevent phase-specific configuration from `.adw/commands/<phase>/config.yaml` from being honored at runtime:

### Bug 1: Timeout Not Applied
The `merged_config.timeout_seconds` is computed from command config but **never passed** to `_execute_llm()`. Phases timeout at the default 300s instead of configured values (e.g., 900s for build phase).

**Location:** `src/adw/core/phase_runner.py:168` and `src/adw/core/phase_runner.py:686-722`

### Bug 2: Phase `enabled` Flag Not Checked
The orchestrator iterates through `PHASE_SEQUENCE` unconditionally without checking the `enabled` flag. Disabled phases (e.g., ship with `enabled: false`) would still execute.

**Location:** `src/adw/core/orchestrator.py:338`

### Bug 3: Config Schema Mismatch
`CommandConfig` does not have an `enabled` field but has `extra="forbid"`. The `.adw/commands/ship/config.yaml` with `enabled: false` would fail Pydantic validation.

**Location:** `src/adw/models/command.py:94-166`

### Architectural Issue: Redundant `phases` Section
The `project.yaml` still has a `phases:` section (`ProjectConfig.phases` at `config.py:749`) that duplicates what should be in command-specific configs. This should be removed entirely.

## Reproduction Steps

1. Create a project with `.adw/commands/build/config.yaml` containing:
   ```yaml
   enabled: true
   timeout_seconds: 900
   ```
2. Create `.adw/commands/ship/config.yaml` containing:
   ```yaml
   enabled: false
   ```
3. Run `adw run "any feature"`
4. Observe build phase times out at 300s (not 900s)
5. Observe ship phase would execute (not skipped) if build succeeds

**Evidence from project-rulebook-be run:**
- Timeouts at exactly 5-minute intervals (300s default):
  - 14:35:03 → 14:40:04 (plan timeout)
  - 14:49:13 → 14:54:13 (build timeout)
- Config specified 900s but was ignored

## Expected Behavior

1. Per-phase `timeout_seconds` from `.adw/commands/<phase>/config.yaml` should be used
2. Phases with `enabled: false` should be skipped
3. `CommandConfig` should accept the `enabled` field
4. `phases:` section in `project.yaml` should be removed (delegated to command configs)

## Actual Behavior

1. Timeout always uses `LLMConfig.timeout_seconds` default (300s)
2. All phases execute unconditionally regardless of `enabled` setting
3. `enabled: false` in command config causes Pydantic validation error
4. Redundant configuration sources cause confusion

## Impact

- **User workflows fail**: Long-running phases (build, ship) timeout prematurely
- **No way to disable phases**: Ship phase cannot be disabled via config
- **Config validation fails**: Invalid `enabled` field causes errors
- **Violates principle of least surprise**: Config exists but is ignored

## User Impact Score

- **Users Affected:** All ADW users with custom phase configs
- **Frequency:** Every run with non-default phase configuration

## Workaround

None effective. Users cannot:
- Extend phase timeouts beyond 300s
- Disable specific phases via config

## Environment

- **OS:** macOS / Any
- **App Version:** adw-sdk (current staging)
- **DPI Scaling:** N/A

## Evidence

### Code Analysis

**phase_runner.py:168** - Timeout not passed:
```python
llm_result = self._execute_llm(phase, context, rendered_prompt)
# merged_config.timeout_seconds is computed but NOT used here
```

**phase_runner.py:721-722** - No timeout parameter:
```python
result = self.executor.execute(
    prompt, phase=phase, cwd=context.worktree_path
)  # ← No timeout parameter!
```

**orchestrator.py:338** - No enabled check:
```python
for phase in PHASE_SEQUENCE:  # ← Unconditionally iterates all phases
    context = self._execute_phase_with_transitions(context, phase)
```

**command.py:140** - Missing enabled field:
```python
model_config = ConfigDict(extra="forbid")  # Rejects unknown fields
# No 'enabled' field defined
```

### Logs

Run log from project-rulebook-be showing 5-minute timeout intervals:
```
2026-01-19 14:35:03 [INFO ] [phase] Phase starting
2026-01-19 14:40:04 [WARN ] [llm] Claude Code execution timed out  # 5 min!
2026-01-19 14:49:13 [INFO ] [phase] Phase starting
2026-01-19 14:54:13 [WARN ] [llm] Claude Code execution timed out  # 5 min!
```

## Proposed Fix

### 1. Add `enabled` field to `CommandConfig`
**File:** `src/adw/models/command.py`
```python
class CommandConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether this phase is enabled")
    # ... existing fields
```

### 2. Pass timeout to `_execute_llm`
**File:** `src/adw/core/phase_runner.py`
```python
# Line 168: Pass timeout
llm_result = self._execute_llm(phase, context, rendered_prompt, merged_config.timeout_seconds)

# Line 686: Accept and use timeout
def _execute_llm(self, phase: str, context: RunContext, prompt: str, timeout: int | None = None) -> LLMResult:
    ...
    result = self.executor.execute(prompt, phase=phase, cwd=context.worktree_path, timeout=timeout)
```

### 3. Check `enabled` flag in orchestrator
**File:** `src/adw/core/orchestrator.py`
```python
for phase in PHASE_SEQUENCE:
    self.interruption_handler.check_shutdown()

    if not self._is_phase_enabled(phase):
        logger.info("Phase disabled, skipping", extra={"phase": phase})
        continue

    context = self._execute_phase_with_transitions(context, phase)
```

### 4. Remove `phases` field from `ProjectConfig`
**File:** `src/adw/models/config.py`
- Remove `phases: dict[str, PhaseConfig]` field (line 749)
- Update all references to use command configs instead

### 5. Update dry_run.py
**File:** `src/adw/cli/dry_run.py`
- Load hooks from command config files instead of `config.phases`

## Files Affected

| File | Change |
|------|--------|
| `src/adw/models/command.py` | Add `enabled` field to `CommandConfig` |
| `src/adw/models/config.py` | Remove `phases` field, deprecate `PhaseConfig` |
| `src/adw/core/phase_runner.py` | Pass timeout to executor, simplify merge logic |
| `src/adw/core/orchestrator.py` | Add phase enabled check in run loop |
| `src/adw/cli/dry_run.py` | Load phase info from command configs |
| Tests | Update tests using `project_config.phases` |

## Resolution

- **Fix Story:** [bugfix-ISS-029-phase-config-not-honored.md](../bugfix-ISS-029-phase-config-not-honored.md)
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This issue was discovered during analysis of a failed ADW run in project-rulebook-be where:
- Build phase config specified `timeout_seconds: 900`
- Ship phase config specified `enabled: false`
- Neither setting was honored at runtime

The root cause is incomplete wiring between config loading and execution - configs are parsed correctly but never applied.
