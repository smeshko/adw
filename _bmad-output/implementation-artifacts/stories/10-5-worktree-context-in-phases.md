# Story 10.5: Worktree Context in Phases

Status: in-progress
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want phases to execute in the worktree context,
so that file operations happen in the isolated environment.

## Acceptance Criteria

**Given** a phase executes
**When** LLM is invoked
**Then** working directory is set to worktree path

**Given** hooks execute
**When** environment is set up
**Then** `ADW_WORKTREE_PATH` is available

**Given** template variables
**When** rendered
**Then** `{{worktree_path}}` resolves to absolute worktree path

**Given** artifact paths
**When** stored in context
**Then** they're relative to worktree root

## Tasks / Subtasks

### Task 1: Set Working Directory for LLM Execution
- [x] Modify `ClaudeCodeExecutor.execute()` to accept `cwd: Path | None`
- [x] Pass `worktree_path` from RunContext when executing LLM
- [x] Ensure all subprocess calls use worktree as working directory
- [x] Handle case where worktree_path is None (legacy mode)

### Task 2: Add ADW_WORKTREE_PATH to Hook Environment
- [x] Add `ADW_WORKTREE_PATH` to hook environment variables
- [x] Set to absolute worktree path, or project root if no worktree
- [x] Update documentation of environment variables

### Task 3: Add worktree_path Template Variable
- [x] Register `worktree_path` in template variable resolver
- [x] Resolve to absolute path of worktree
- [x] Resolve to project root if no worktree (backward compatibility)
- [x] Add to variable documentation

### Task 4: Implement Relative Artifact Paths
- [x] Modify artifact storage to use relative paths
- [x] Store artifacts at `<worktree>/.adw/runs/<run_id>/artifacts/`
- [x] When storing in context, convert to relative path from worktree root
- [x] When loading, resolve relative to current worktree

### Task 5: Update RunContext Path Resolution
- [x] Add helper method `resolve_artifact_path(relative: str) -> Path`
- [x] Method considers worktree_path if present
- [x] Ensure all artifact references go through this method

### Task 6: Source .ports.env in Hooks
- [ ] Auto-source `.ports.env` before hook script runs
- [ ] Make `BACKEND_PORT`, `FRONTEND_PORT` available to hooks
- [ ] Add `ADW_PORTS_FILE` environment variable

### Task 7: Integration Testing
- [ ] Test phase execution in worktree context
- [ ] Test hook receives correct environment variables
- [ ] Test template variables resolve correctly
- [ ] Test artifact paths work across worktree lifecycle

---

## Dependencies

**Depends On:**
- 10-2: Worktree Directory Structure (needs directory layout for artifacts)
- 10-4: Concurrent Run Management (needs concurrent infrastructure)

**Blocks:** None (this is Wave 4 - final wave)

**Can Parallel With:** None

---

## Developer Context

### Technical Requirements

1. **Working Directory Handling**
   - Use `subprocess.run(cwd=worktree_path)` for all subprocess calls
   - Ensure environment variables point to correct paths
   - Handle path resolution for both absolute and relative paths

2. **Environment Variable Consistency**
   - All ADW_* environment variables should be consistent
   - `ADW_WORKTREE_PATH` is the worktree root
   - `ADW_PROJECT_ROOT` remains the original project root
   - `ADW_ARTIFACTS_DIR` points to worktree's artifacts directory

3. **Template Variable Resolution**
   - `{{worktree_path}}` - absolute worktree path
   - `{{project_root}}` - original project root (unchanged)
   - `{{artifacts_dir}}` - worktree's artifacts directory

### Architecture Compliance

**Modified Files:**
```
src/adw/
├── executors/
│   └── claude_code.py    # Add cwd parameter
├── hooks/
│   └── environment.py    # Add ADW_WORKTREE_PATH
├── commands/
│   └── template.py       # Add worktree_path variable
├── core/
│   └── phase_runner.py   # Pass worktree context
└── models/
    └── context.py        # Add resolve_artifact_path()
```

**Executor Changes:**
```python
# src/adw/executors/claude_code.py
class ClaudeCodeExecutor:
    async def _stream_subprocess(
        self,
        prompt: str,
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> LLMResult:
        """Execute Claude Code with optional working directory."""
        process = await asyncio.create_subprocess_exec(
            self.claude_path,
            "--print",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,  # NEW: Set working directory
        )
        # ... rest of implementation
```

**Environment Changes:**
```python
# src/adw/hooks/environment.py
def get_hook_environment(context: RunContext) -> dict[str, str]:
    """Build environment variables for hook execution."""
    env = os.environ.copy()
    env.update({
        "ADW_RUN_ID": context.run_id,
        "ADW_PHASE": context.current_phase,
        "ADW_PROJECT_ROOT": str(context.project_root),
        "ADW_ARTIFACTS_DIR": str(context.artifacts_dir),
        # NEW: Worktree path
        "ADW_WORKTREE_PATH": str(context.worktree_path or context.project_root),
        # Port variables from .ports.env if available
        **_load_ports_env(context),
    })
    return env
```

**Template Changes:**
```python
# src/adw/commands/template.py
def get_template_variables(context: RunContext) -> dict[str, str]:
    """Get all available template variables."""
    return {
        "run_id": context.run_id,
        "project_root": str(context.project_root),
        "current_phase": context.current_phase,
        # NEW: Worktree path
        "worktree_path": str(context.worktree_path or context.project_root),
        # ... other variables
    }
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| pathlib | stdlib | Path manipulation |
| os | stdlib | Environment handling |
| asyncio | stdlib | Subprocess with cwd |

### File Structure Requirements

**Environment Variables (Complete Set):**

| Variable | Value | Description |
|----------|-------|-------------|
| `ADW_RUN_ID` | ULID | Current run identifier |
| `ADW_PHASE` | string | Current phase name |
| `ADW_PROJECT_ROOT` | path | Original project root |
| `ADW_WORKTREE_PATH` | path | Worktree root (or project root) |
| `ADW_ARTIFACTS_DIR` | path | Artifacts directory |
| `ADW_CONTEXT_FILE` | path | Path to context.json |
| `ADW_PORTS_FILE` | path | Path to .ports.env |
| `BACKEND_PORT` | int | Allocated backend port |
| `FRONTEND_PORT` | int | Allocated frontend port |

**Template Variables (Complete Set):**

| Variable | Resolves To |
|----------|-------------|
| `{{run_id}}` | Current run ULID |
| `{{project_root}}` | Original project root |
| `{{worktree_path}}` | Worktree root (or project root) |
| `{{current_phase}}` | Current phase name |
| `{{artifacts_dir}}` | Phase artifacts directory |
| `{{feature_request}}` | Original feature request |
| `{{backend_port}}` | Allocated backend port |
| `{{frontend_port}}` | Allocated frontend port |

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/executors/test_claude_code.py
class TestWorktreeContext:
    def test_execute_uses_worktree_cwd(self, executor, worktree_path):
        """Subprocess runs with worktree as working directory."""

    def test_execute_without_worktree_uses_project_root(self, executor):
        """Falls back to project root when no worktree."""


# tests/unit/hooks/test_environment.py
class TestWorktreeEnvironment:
    def test_includes_worktree_path(self, context_with_worktree):
        """ADW_WORKTREE_PATH is set correctly."""

    def test_worktree_path_fallback(self, context_without_worktree):
        """Falls back to project root when no worktree."""


# tests/unit/commands/test_template.py
class TestWorktreeVariables:
    def test_worktree_path_resolves(self, context_with_worktree):
        """{{worktree_path}} resolves to worktree."""

    def test_worktree_path_fallback(self, context_without_worktree):
        """Falls back to project root when no worktree."""
```

**Integration Tests:**
```python
# tests/integration/test_worktree_phases.py
class TestPhaseInWorktree:
    def test_llm_executes_in_worktree(self, project_with_worktree, mock_executor):
        """LLM execution happens in worktree directory."""

    def test_hook_receives_worktree_env(self, project_with_worktree, hook_script):
        """Hook script receives ADW_WORKTREE_PATH."""

    def test_artifacts_stored_in_worktree(self, project_with_worktree):
        """Artifacts are stored in worktree's .adw directory."""

    def test_artifacts_preserved_after_cleanup(self, project_with_worktree):
        """Key artifacts are copied to main project after worktree removal."""
```

---

## Previous Story Intelligence

**From Story 10-2:**
- Directory structure defines where artifacts live in worktree
- Artifact preservation copies files to main project

**From Story 10-4:**
- Concurrent run management tracks active worktrees

---

## Git Intelligence

**Relevant Patterns:**
- Template variable patterns from `commands/template.py`
- Environment variable patterns from `hooks/environment.py`
- Executor subprocess patterns from `executors/claude_code.py`

---

## Latest Technical Information

**asyncio.create_subprocess_exec() with cwd:**
```python
process = await asyncio.create_subprocess_exec(
    *args,
    cwd="/path/to/worktree",  # Sets working directory
    env=env,                   # Custom environment
)
```

**Path Resolution Best Practices:**
- Always use absolute paths for subprocess cwd
- Store relative paths in context for portability
- Resolve relative paths at load time

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- **Type annotations**: All Path parameters typed
- **Backward compatibility**: Handle None worktree_path
- **Structured logging**: Log cwd changes

---

## Dev Notes

### Backward Compatibility

All changes must be backward compatible:
- `worktree_path = None` means run in project root (legacy)
- All path resolution falls back to project root
- Template variables resolve to project root when no worktree

### Error Handling

- If worktree path doesn't exist at execution time, fail with clear error
- If artifacts directory can't be created, fail with suggestion
- If template variable can't resolve, fail at template loading time

### References

- [Source: _bmad-output/epics/epic-10-worktree-isolation.md#Story 10.5]
- [Source: _bmad-output/architecture.md#Hook Execution Environment]
- [Source: _bmad-output/architecture.md#Template Engine]

---

## Dev Agent Record

### Context Reference

Epic 10: Worktree Isolation - Story 10.5

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

**Task 1: Set Working Directory for LLM Execution**
- Added `cwd: Path | None` parameter to LLMExecutor Protocol in `src/adw/executors/base.py`
- Updated `ClaudeCodeExecutor.execute()` and `_stream_subprocess()` to accept and pass cwd to subprocess
- Updated `MockExecutor.execute()` for interface compatibility
- Updated `RetryExecutor` to pass through cwd parameter
- Updated `PhaseRunner._execute_llm()` to pass `context.worktree_path` to executor
- Added unit tests for worktree working directory support
- All 124 executor tests pass
- All 21 phase runner tests pass

**Task 2: Add ADW_WORKTREE_PATH to Hook Environment**
- Added `ADW_WORKTREE_PATH` environment variable to `build_hook_environment()`
- Priority: context.worktree_path > project_root > (not set)
- Added `project_root` parameter for fallback behavior
- Added unit tests for worktree path environment variable
- All 109 hooks tests pass

**Task 3: Add worktree_path Template Variable**
- Added `worktree_path` to template variables in `PhaseRunner._load_and_render_prompt()`
- Resolves to absolute path string when set, empty string when None
- Added unit tests for worktree_path template variable
- All 23 phase runner tests pass

**Tasks 4 & 5: Artifact Path Resolution**
- Added `resolve_artifact_path()` method to RunContext for worktree-aware path resolution
- Added `get_runs_dir()` method to get worktree-relative runs directory
- Priority: worktree_path > project_root > cwd
- Added 6 unit tests for artifact path resolution
- All 49 context model tests pass

### File List

**Modified:**
- src/adw/executors/base.py - Added cwd parameter to Protocol
- src/adw/executors/claude_code.py - Added cwd parameter to execute() and _stream_subprocess()
- src/adw/executors/mock.py - Added cwd parameter for interface compatibility
- src/adw/executors/retry.py - Added cwd parameter passthrough
- src/adw/core/phase_runner.py - Pass worktree_path to executor, added worktree_path template variable
- src/adw/hooks/environment.py - Added ADW_WORKTREE_PATH and project_root parameter
- src/adw/models/context.py - Added resolve_artifact_path() and get_runs_dir() methods
- tests/unit/executors/test_claude_code.py - Added TestWorktreeWorkingDirectory tests
- tests/unit/hooks/test_environment.py - Added TestWorktreePathEnvironment tests
- tests/unit/core/test_phase_runner.py - Added TestPhaseRunnerWorktreeContext tests
- tests/unit/models/test_context.py - Added TestRunContextArtifactPathResolution tests
