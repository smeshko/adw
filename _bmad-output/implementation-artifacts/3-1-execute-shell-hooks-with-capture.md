# Story 3.1: Execute Shell Hooks with Capture

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2025-12-31

---

## Story

As a developer,
I want to execute shell scripts as pre-hooks and post-hooks,
so that I can run custom logic before and after LLM execution.

## Acceptance Criteria

**Given** a pre-hook script at `commands/plan/pre-hook.sh`
**When** the hook is executed
**Then** stdout is captured and returned for use in templates
**And** stderr is logged

**Given** a hook script that exits with code 0
**When** execution completes
**Then** the hook is considered successful

**Given** a hook script that exits with non-zero code
**When** execution completes
**Then** HookError is raised with exit code, stdout, and stderr

**Given** a hook script that takes longer than the configured timeout
**When** timeout is reached
**Then** the process is killed and HookError is raised with code "HOOK_TIMEOUT"

**Given** environment variables in the run context
**When** the hook executes
**Then** they are available to the script (ADW_RUN_ID, ADW_PHASE, ADW_FEATURE, etc.)

**Given** a command directory without hooks
**When** hook execution is requested
**Then** it's silently skipped (not an error)

## Tasks / Subtasks

### Task 1: Create HookResult Model
- [x] Create `src/adw/models/hook.py` with `HookResult` Pydantic model
- [x] Fields: `stdout: str`, `stderr: str`, `exit_code: int`, `duration_ms: int`, `hook_type: str` (pre/post)
- [x] Add to `src/adw/models/__init__.py` exports

### Task 2: Create HookEnvironment Helper
- [x] Create `src/adw/hooks/environment.py`
- [x] Implement `build_hook_environment(context: RunContext, phase: str) -> dict[str, str]`
- [x] Include: `ADW_RUN_ID`, `ADW_PHASE`, `ADW_ARTIFACTS_DIR`, `ADW_CONTEXT_FILE`, `ADW_FEATURE`
- [x] Merge with current process environment (`os.environ`)

### Task 3: Implement HookRunner Class
- [x] Create `src/adw/hooks/runner.py`
- [x] Implement `HookRunner` class with `__init__(config: HookConfig)`
- [x] Implement `run_hook(hook_path: Path, context: RunContext, phase: str, timeout: int | None = None) -> HookResult`
- [x] Use `asyncio.create_subprocess_exec()` for subprocess execution with timeout
- [x] Capture stdout and stderr separately
- [x] Return `HookResult` on success

### Task 4: Implement Error Handling
- [x] Raise `HookError` with code `HOOK_FAILED` on non-zero exit
- [x] Raise `HookError` with code `HOOK_TIMEOUT` when timeout exceeded
- [x] Include stdout, stderr, exit_code in error for debugging
- [x] Use existing `HookError` from `adw.exceptions`

### Task 5: Implement Hook Discovery
- [x] Implement `find_hook(command_dir: Path, hook_type: str) -> Path | None`
- [x] Look for `pre-hook.sh` or `post-hook.sh` in command directory
- [x] Return `None` if not found (not an error)
- [x] Support both `.sh` extension and extensionless scripts

### Task 6: Write Unit Tests
- [x] Create `tests/unit/hooks/test_runner.py`
- [x] Test successful hook execution with stdout capture
- [x] Test failed hook (non-zero exit) raises `HookError`
- [x] Test timeout handling raises `HookError` with `HOOK_TIMEOUT`
- [x] Test environment variables passed correctly
- [x] Test missing hook returns `None` (no error)
- [x] Create test fixtures at `tests/fixtures/hooks/` with sample scripts
- [x] Target: >90% coverage for hooks module (achieved 100%)

### Task 7: Integration Tests
- [ ] Create `tests/integration/test_hooks.py`
- [ ] Test hook execution with real shell scripts
- [ ] Test environment variable propagation
- [ ] Test timeout behavior with slow scripts

---

## Developer Context

### Technical Requirements

- **Async Pattern**: Use `asyncio.create_subprocess_exec()` for non-blocking subprocess execution
- **Timeout Handling**: Use `asyncio.wait_for()` or `asyncio.timeout()` (Python 3.11+)
- **Process Termination**: On timeout, kill process with `process.kill()` then await cleanup
- **Stream Capture**: Read stdout/stderr using `process.communicate()`
- **Exit Code**: Get via `process.returncode` after process completes

### Architecture Compliance

**From architecture.md - Hook Execution Environment Decision:**

| Variable | Description |
|----------|-------------|
| `ADW_RUN_ID` | Current run ULID |
| `ADW_PHASE` | Current phase name |
| `ADW_ARTIFACTS_DIR` | Path to artifacts directory |
| `ADW_CONTEXT_FILE` | Path to full context.json |

**Working Directory:** Project root (where `.adw/` lives)

**Exception Pattern (MUST follow):**
```python
# CORRECT - catch specific, re-raise with context
try:
    result = subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    raise HookError(
        code="HOOK_FAILED",
        phase=phase,
        message=f"Hook exited with code {e.returncode}",
        suggestion="Check hook script for errors",
        recoverable=False
    ) from e
```

**HookError already exists at `src/adw/exceptions.py:160`:**
```python
class HookError(ADWError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        phase: str,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        suggestion: str | None = None,
        recoverable: bool = False,
    ) -> None:
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Python | 3.13+ | `asyncio.create_subprocess_exec()` for subprocess |
| Pydantic | 2.12+ | `HookResult` model |
| Rich | 14.1.0 | Console output for logging (optional) |

**Key asyncio APIs:**
```python
import asyncio

async def run_hook():
    process = await asyncio.create_subprocess_exec(
        "/bin/bash", script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=hook_env,
        cwd=project_root,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise HookError(code="HOOK_TIMEOUT", ...)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── hooks/
│   ├── __init__.py        # Already exists (empty)
│   ├── runner.py          # NEW: HookRunner class
│   └── environment.py     # NEW: Environment variable builder
├── models/
│   └── hook.py            # NEW: HookResult model

tests/
├── unit/
│   └── hooks/
│       ├── __init__.py    # NEW
│       └── test_runner.py # NEW
├── integration/
│   └── test_hooks.py      # NEW
└── fixtures/
    └── hooks/             # NEW: Sample hook scripts
        ├── success.sh
        ├── failure.sh
        └── slow.sh
```

**Naming conventions (PEP 8):**
- Class: `HookRunner`, `HookResult`
- Functions: `run_hook()`, `build_hook_environment()`
- Constants: `DEFAULT_HOOK_TIMEOUT = 60`

### Testing Requirements

**Test Framework:** pytest with pytest-asyncio for async tests

**Required Fixtures:**
```python
@pytest.fixture
def hook_config() -> HookConfig:
    return HookConfig(shell="/bin/bash", timeout_seconds=60)

@pytest.fixture
def run_context() -> RunContext:
    return RunContext(
        run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        feature_description="Test feature",
        current_phase="plan",
        started_at=datetime.now(),
    )

@pytest.fixture
def temp_hook_script(tmp_path: Path) -> Path:
    script = tmp_path / "pre-hook.sh"
    script.write_text("#!/bin/bash\necho 'hello'")
    script.chmod(0o755)
    return script
```

**Coverage Target:** >80% overall, >90% for hooks module

---

## Previous Story Intelligence

This is the first story in Epic 3. Key learnings from Epic 2 that apply:

- **From Story 2.3 (Phase Prompts)**: Template engine already handles `{{file:path}}` includes. Hook stdout can be injected into templates.
- **From Story 2.4 (Schema Validation)**: Validation patterns established. HookResult should follow same Pydantic model patterns.
- **From Epic 1**: Exception hierarchy is well-established. Use `HookError` from `src/adw/exceptions.py`.

**Existing Code Patterns to Follow:**
- Models defined in `src/adw/models/` with comprehensive docstrings
- Exceptions use `code`, `message`, `suggestion`, `recoverable` pattern
- Tests mirror source structure in `tests/unit/`

---

## Git Intelligence

Recent commits show:
- Story 2-3 and 2-4 recently completed (template engine, schema validation)
- Code formatting with ruff is enforced
- Sprint status is tracked in YAML format

**Code conventions observed:**
- Full type annotations on all functions
- Pydantic models with Field descriptions
- Docstrings on all public classes and methods

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Exception Hierarchy**: Never raise bare `Exception` - use `HookError` from hierarchy
2. **Type Annotations**: Required on all public functions with modern `|` syntax
3. **Async Model**: "Sync with Async Islands" - use `asyncio.run()` wrapper for async hook execution
4. **Structured Logging**: Use `logger.info("Hook executed", phase="plan", duration_ms=1234)`
5. **Context Managers**: Use for any resource that needs cleanup

---

## Dev Notes

### Key Implementation Points

1. **Async Wrapper Pattern** - The `HookRunner.run_hook()` method should be synchronous externally but use `asyncio.run()` internally:
   ```python
   def run_hook(self, hook_path: Path, ...) -> HookResult:
       return asyncio.run(self._execute_hook(hook_path, ...))
   ```

2. **Graceful Skip** - When no hook exists, return `None` (not an error):
   ```python
   def find_hook(self, command_dir: Path, hook_type: str) -> Path | None:
       for ext in ["", ".sh"]:
           path = command_dir / f"{hook_type}-hook{ext}"
           if path.exists() and path.is_file():
               return path
       return None
   ```

3. **Environment Isolation** - Start with copy of `os.environ`, then add ADW variables:
   ```python
   env = os.environ.copy()
   env.update({
       "ADW_RUN_ID": context.run_id,
       "ADW_PHASE": phase,
       # ...
   })
   ```

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming) ✓
- `hooks/` module already exists but is empty - populate with `runner.py` and `environment.py`
- No conflicts detected with existing code

### References

- [Source: _bmad-output/architecture.md#Hook-Execution-Environment]
- [Source: _bmad-output/architecture.md#Error-Handling]
- [Source: src/adw/exceptions.py:160-231] - HookError definition
- [Source: src/adw/models/config.py:64-75] - HookConfig definition
- [Source: _bmad-output/project-context.md#Async-Model]

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created HookResult model with stdout, stderr, exit_code, duration_ms, hook_type fields. Added is_success computed property. Model validates hook_type as Literal["pre", "post"] and enforces non-negative duration. Tests cover all validation rules.
- Task 2: Created build_hook_environment() function. Merges os.environ with ADW-specific variables (ADW_RUN_ID, ADW_PHASE, ADW_FEATURE, ADW_ARTIFACTS_DIR, ADW_CONTEXT_FILE). All values are strings for subprocess compatibility.
- Task 3-5: Implemented HookRunner class with asyncio subprocess execution. Uses asyncio.create_subprocess_exec() with wait_for() for timeout. Captures stdout/stderr separately. Raises HookError with HOOK_FAILED or HOOK_TIMEOUT codes. Also implemented find_hook() for hook discovery with .sh and extensionless support.
- Task 6: Unit tests complete with 31 tests, 100% coverage on hooks module. Added test fixtures at tests/fixtures/hooks/.

### File List

- src/adw/models/hook.py (NEW)
- src/adw/models/__init__.py (MODIFIED)
- src/adw/hooks/environment.py (NEW)
- src/adw/hooks/runner.py (NEW)
- tests/unit/hooks/__init__.py (NEW)
- tests/unit/hooks/test_hook_result.py (NEW)
- tests/unit/hooks/test_environment.py (NEW)
- tests/unit/hooks/test_runner.py (NEW)
- tests/fixtures/hooks/success.sh (NEW)
- tests/fixtures/hooks/failure.sh (NEW)
- tests/fixtures/hooks/slow.sh (NEW)
- tests/fixtures/hooks/env_check.sh (NEW)

---

## Dependencies

- **Depends On:** None
- **Blocks:** None
- **Can Parallel With:** Story 3.2

### Dependency Rationale
- No dependencies - this story can start immediately
- Story 3.1 and 3.2 are independent Wave 1 stories that can be developed in parallel
