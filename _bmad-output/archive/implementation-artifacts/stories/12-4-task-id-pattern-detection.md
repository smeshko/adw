# Story 12.4: Task ID Pattern Detection

Status: done
Linear Issue: not-configured
Epic: 12 - Task Manager Integration
Created: 2026-01-08

---

## Story

As a user,
I want adw to auto-detect when I provide a task ID vs a feature string,
So that I don't need special flags.

## Acceptance Criteria

**Given** input "RULE-123"
**When** Linear configured with team_key: RULE
**Then** recognized as Linear task ID

**Given** input "Add user authentication"
**When** any task manager configured
**Then** treated as literal feature string

**Given** input "PROJECT-456"
**When** Linear configured with team_key: RULE
**Then** not recognized, treated as feature string

**Given** ambiguous input
**When** could be task ID or feature
**Then** explicit flag `--task-id` available for override

**Given** `--no-task-manager` flag
**When** provided with any input
**Then** input treated as literal feature string, no task manager used

## Tasks / Subtasks

### Task 1: Create InputResolver
- [x] Create `src/adw/task_managers/resolver.py` with `InputResolver`
- [x] Initialize with `TaskManager` instance
- [x] Implement `resolve(input_str: str, force_task_id: bool = False) -> ResolvedInput`
- [x] `ResolvedInput` enum: `TASK_ID`, `FEATURE_STRING`

### Task 2: Implement Pattern Detection Logic
- [x] Call `task_manager.resolve_task_id(input_str)`
- [x] If returns task ID -> `TASK_ID`
- [x] If returns None -> `FEATURE_STRING`
- [x] If `force_task_id=True` and resolve fails -> raise error

### Task 3: Add CLI Flags
- [x] Add `--task-id` flag to `adw run` command
- [x] Add `--no-task-manager` flag to `adw run` command
- [x] Update CLI help text with flag descriptions
- [x] Flags are mutually exclusive

### Task 4: Integrate with Run Command
- [x] Pass flags to InputResolver
- [x] `--task-id`: Force task ID interpretation
- [x] `--no-task-manager`: Force feature string interpretation
- [x] Neither: Auto-detect based on pattern

### Task 5: Add Ambiguity Handling
- [x] Define ambiguity criteria (e.g., short strings that match pattern)
- [x] If ambiguous, prefer task ID if pattern matches
- [x] Log info message about interpretation for transparency
- [x] Suggest `--task-id` or `--no-task-manager` for explicit control

### Task 6: Write Tests
- [x] Unit tests for `InputResolver.resolve` (6 tests)
- [x] Unit tests for pattern matching edge cases (5 tests)
- [x] CLI tests for `--task-id` flag (3 tests)
- [x] CLI tests for `--no-task-manager` flag (3 tests)
- [x] Integration test for full detection flow (2 tests)

---

## Dependencies

- **Depends On:** Story 12.1 (TaskManager Protocol)
- **Blocks:** None
- **Can Parallel With:** Story 12.2

### Dependency Rationale
- Requires resolve_task_id method from TaskManager Protocol
- Independent of Linear-specific implementation (can run in parallel)
- Does not block other stories

---

## Developer Context

### Technical Requirements

1. **Pattern Detection**
   - Delegate to TaskManager.resolve_task_id()
   - Support multiple task managers with different patterns
   - Handle case-insensitive matching

2. **CLI Integration**
   - Flags added to existing `adw run` command
   - Mutually exclusive flags
   - Clear help text explaining behavior

3. **Transparency**
   - Log which interpretation was chosen
   - User can override with explicit flags
   - Error messages suggest flags

### Architecture Compliance

**File Location:** `src/adw/task_managers/`

**New File:**
```
src/adw/task_managers/
└── resolver.py       # InputResolver
```

**Implementation Pattern:**
```python
# src/adw/task_managers/resolver.py
from enum import Enum
from dataclasses import dataclass
import logging
from adw.task_managers.base import TaskManager
from adw.models.task import TaskInfo

logger = logging.getLogger(__name__)

class InputType(Enum):
    TASK_ID = "task_id"
    FEATURE_STRING = "feature_string"

@dataclass
class ResolvedInput:
    type: InputType
    value: str
    task_id: str | None = None
    original: str = ""

class InputResolver:
    def __init__(self, task_manager: TaskManager) -> None:
        self._task_manager = task_manager

    def resolve(
        self,
        input_str: str,
        *,
        force_task_id: bool = False,
        force_feature: bool = False,
    ) -> ResolvedInput:
        """Resolve input string to either task ID or feature string."""
        if force_feature:
            logger.info("Input treated as feature (--no-task-manager)", input=input_str)
            return ResolvedInput(
                type=InputType.FEATURE_STRING,
                value=input_str,
                original=input_str,
            )

        task_id = self._task_manager.resolve_task_id(input_str)

        if task_id:
            logger.info("Input resolved as task ID", input=input_str, task_id=task_id)
            return ResolvedInput(
                type=InputType.TASK_ID,
                value=task_id,
                task_id=task_id,
                original=input_str,
            )

        if force_task_id:
            raise ValueError(f"Input '{input_str}' does not match task ID pattern")

        logger.info("Input treated as feature string", input=input_str)
        return ResolvedInput(
            type=InputType.FEATURE_STRING,
            value=input_str,
            original=input_str,
        )
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| enum | stdlib | Input type enum |
| dataclasses | stdlib | ResolvedInput dataclass |
| typer | 0.21.0 | CLI flags |

**No New Dependencies.**

### File Structure Requirements

**New Files:**
- `src/adw/task_managers/resolver.py`

**Modified Files:**
- `src/adw/cli/run.py` - Add `--task-id` and `--no-task-manager` flags
- `src/adw/task_managers/__init__.py` - Export InputResolver

**Test Files:**
- `tests/unit/task_managers/test_resolver.py`
- `tests/unit/cli/test_run_flags.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/task_managers/test_resolver.py
class TestInputResolver:
    def test_resolve_task_id_match(self, mock_task_manager):
        """Returns TASK_ID when pattern matches."""

    def test_resolve_feature_string(self, mock_task_manager):
        """Returns FEATURE_STRING when pattern doesn't match."""

    def test_resolve_force_task_id(self, mock_task_manager):
        """Raises error when force_task_id=True and no match."""

    def test_resolve_force_feature(self, mock_task_manager):
        """Returns FEATURE_STRING regardless of pattern when force_feature=True."""

    def test_resolve_logs_interpretation(self, mock_task_manager, caplog):
        """Logs which interpretation was chosen."""

    def test_resolve_preserves_original(self, mock_task_manager):
        """ResolvedInput includes original input string."""

class TestInputResolverEdgeCases:
    def test_empty_string(self, mock_task_manager):
        """Empty string treated as feature."""

    def test_whitespace_only(self, mock_task_manager):
        """Whitespace-only treated as feature."""

    def test_case_insensitive(self, mock_task_manager):
        """Pattern matching is case-insensitive."""

    def test_with_spaces(self, mock_task_manager):
        """Input with spaces treated as feature."""

    def test_numeric_only(self, mock_task_manager):
        """Numeric-only input (e.g., '123') treated as feature."""

# tests/unit/cli/test_run_flags.py
class TestRunCommandFlags:
    def test_task_id_flag(self, cli_runner):
        """--task-id forces task ID interpretation."""

    def test_no_task_manager_flag(self, cli_runner):
        """--no-task-manager forces feature interpretation."""

    def test_flags_mutually_exclusive(self, cli_runner):
        """Error when both flags provided."""
```

---

## Previous Story Intelligence

**From Story 12.1:**
- TaskManager.resolve_task_id(input_str) -> str | None
- Pattern matching delegated to task manager

**Patterns to Follow:**
- Use structured logging for transparency
- Include original input in resolved result
- Clear error messages with suggestions

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 12.1: TaskManager Protocol with resolve_task_id
- CLI command patterns from Epic 5

**Established Patterns:**
- CLI flags use Typer annotations
- Mutually exclusive flags via callbacks
- Resolver pattern for input handling

---

## Latest Technical Information

**CLI UX Best Practices (2025):**
- Auto-detection is user-friendly but should be transparent
- Provide override flags for explicit control
- Log which interpretation was chosen
- Error messages should suggest correct usage

**Typer Mutually Exclusive Flags:**
```python
import typer
from typing import Annotated

def run(
    feature: Annotated[str, typer.Argument(...)],
    task_id: Annotated[bool, typer.Option("--task-id", help="Force task ID")] = False,
    no_task_manager: Annotated[bool, typer.Option("--no-task-manager", help="Ignore task manager")] = False,
):
    if task_id and no_task_manager:
        raise typer.BadParameter("--task-id and --no-task-manager are mutually exclusive")
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **CLI command patterns**: kebab-case for flags (--task-id, --no-task-manager)
- **Structured logging**: Log interpretation choices
- **Type annotations required**: All functions fully typed

---

## Dev Notes

### Implementation Approach

1. Create ResolvedInput dataclass and InputType enum
2. Implement InputResolver with resolve method
3. Add CLI flags to run command
4. Integrate resolver in run flow
5. Add logging for transparency
6. Write comprehensive tests

### Key Design Decisions

1. **Delegate to TaskManager**: Pattern detection is task manager specific
2. **Dataclass Result**: ResolvedInput carries all needed context
3. **Transparent Logging**: User knows how input was interpreted
4. **Override Flags**: Explicit control when auto-detection fails

### CLI Usage Examples

```bash
# Auto-detect (RULE-123 detected as task ID)
adw run RULE-123

# Force task ID (error if pattern doesn't match)
adw run "RULE-123" --task-id

# Force feature string (ignore task manager)
adw run "RULE-123" --no-task-manager

# Feature string (auto-detected)
adw run "Add user authentication"
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.4]
- [Source: _bmad-output/architecture.md#Task Manager Integration]
- [Source: _bmad-output/project-context.md#CLI Command Patterns]

---

## Dev Agent Record

### Context Reference

Epic 12: Task Manager Integration - Story 12.4

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

- Task 1: Created InputResolver class with InputType enum and ResolvedInput dataclass. Implements pattern detection by delegating to TaskManager.resolve_task_id(). Supports force_task_id and force_feature flags for explicit control.
- Task 2: Pattern detection logic already implemented in Task 1's resolve() method. Verified by test_resolve_task_id_match, test_resolve_feature_string, and test_resolve_force_task_id_error.
- Task 3: Added --task-id and --no-task-manager flags to run command. Flags are mutually exclusive with error handling. Updated docstring examples. Added 5 CLI tests.
- Task 4: Integrated InputResolver into run command. Creates TaskManager via factory, resolves input with flags, handles ValueError for invalid --task-id. Logs task ID resolution for transparency.
- Task 5: Enhanced ambiguity handling with tip suggesting --no-task-manager when task ID is auto-detected. Error messages suggest removing --task-id flag. Added 2 ambiguity handling tests.
- Task 6: Comprehensive test suite complete with 26 tests total. Covers InputResolver.resolve (6), edge cases (5), --task-id CLI (3), --no-task-manager CLI (3), integration (2), plus additional coverage tests.

### File List

- src/adw/task_managers/resolver.py (new)
- src/adw/task_managers/__init__.py (modified - exported InputResolver, InputType, ResolvedInput)
- tests/unit/task_managers/test_resolver.py (new)
- src/adw/cli/app.py (modified - added --task-id and --no-task-manager flags)
- tests/unit/cli/test_run_flags.py (new)
