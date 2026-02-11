# Tech-Spec: Phase Extensions System

**Created:** 2026-01-21
**Status:** Ready for Development

## Overview

### Problem Statement

Phase-specific logic is scattered across `orchestrator.py` and `phase_runner.py`, making it difficult to:
- Add new phases with custom behavior without modifying core files
- Understand where phase-specific logic lives
- Test phase behaviors in isolation
- Maintain clean separation of concerns

Current violations:
- PR creation after document phase (orchestrator.py:395-406, 1698-1764)
- Ship phase skip logic (orchestrator.py:371-389, 1018-1036)
- Git diff capture for build phase (phase_runner.py:1193-1195, 1202-1331)
- `pr_description.md` artifact for document phase (phase_runner.py:1167-1179)

### Solution

Introduce a **Phase Extensions** system that allows phases to define custom behavior through a `PhaseExtension` protocol with lifecycle hooks:
- `should_skip()` - Skip phase based on conditions
- `on_complete()` - Post-phase processing (e.g., PR creation)
- `extra_artifacts()` - Capture additional artifacts

Extensions are:
- **Stateless** - Run-specific data flows through `RunContext`
- **Singletons** - One instance per registry lifetime
- **Non-blocking** - Failures log warnings, signal via context
- **Built-in only** - No project-level extensions for now

### Scope

**In Scope:**
- `PhaseExtension` protocol definition
- `ExtensionRegistry` class
- Built-in extensions: `BuildExtension`, `DocumentExtension`, `ShipExtension`
- Migration of existing scattered logic to extensions
- `RunContext` fields for cross-phase state

**Out of Scope:**
- Project-level custom extensions
- Prompt modification hooks
- Custom validators
- Extension configuration via config.yaml

## Context for Development

### Codebase Patterns

**Protocol Pattern:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMExecutor(Protocol):
    def execute(self, prompt: str, ...) -> LLMResult: ...
```

**Pydantic Model Pattern:**
```python
from pydantic import BaseModel, Field

class RunContext(BaseModel):
    pr_url: str | None = Field(default=None, description="...")

    model_config = {"frozen": False, "validate_assignment": True}
```

**Dependency Injection Pattern:**
- Services created at CLI entry point
- Passed via constructor to orchestrator/phase_runner
- Singletons reused across runs

**Error Handling Pattern (non-blocking):**
```python
try:
    result = self._do_something()
except Exception as e:
    logger.warning("Failed (non-blocking)", extra={"error": str(e)})
    return None
```

### Files to Reference

| File | Relevance |
|------|-----------|
| `src/adw/core/orchestrator.py` | Remove phase-specific logic, add registry |
| `src/adw/core/phase_runner.py` | Accept registry, call lifecycle hooks |
| `src/adw/models/context.py` | Add PR state fields to RunContext |
| `src/adw/executors/base.py` | Protocol pattern reference |
| `src/adw/core/constants.py` | PHASE_SEQUENCE definition |
| `src/adw/hooks/git_diff.py` | Git diff utilities (used by BuildExtension) |
| `src/adw/cli/pr.py` | PR creation logic (used by DocumentExtension) |

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Extension instantiation | Singletons | Matches existing service patterns, extensions should be stateless |
| Error handling | Non-blocking | PR/artifact failures shouldn't fail phases, matches current behavior |
| Cross-phase state | Via RunContext | Clean data flow, testable, serializable |
| Protocol vs ABC | Protocol | Structural subtyping, matches existing patterns |
| Registry location | `PhaseRunner` | Extensions are phase execution concerns, not orchestration |

## Implementation Plan

### Tasks

- [ ] **Task 1: Create extension foundation**
  - Create `src/adw/core/extensions/` directory
  - Create `base.py` with `PhaseExtension` protocol
  - Create `registry.py` with `ExtensionRegistry` class
  - Create `__init__.py` with exports

- [ ] **Task 2: Add RunContext fields**
  - Add `pr_creation_attempted: bool = False`
  - Add `pr_creation_failed: bool = False`
  - Add `pr_failure_reason: str | None = None`

- [ ] **Task 3: Integrate registry into PhaseRunner**
  - Add `extension_registry` parameter to `__init__`
  - Add `_call_extra_artifacts()` in `_capture_artifacts()`
  - Add `_call_on_complete()` at end of `run()`
  - No behavior change yet (registry empty)

- [ ] **Task 4: Integrate registry into Orchestrator**
  - Create `ExtensionRegistry` in `__init__`
  - Pass to `PhaseRunner`
  - Add `should_skip_phase()` check before `_execute_phase_with_transitions()`
  - No behavior change yet (registry empty)

- [ ] **Task 5: Implement BuildExtension**
  - Move `_capture_git_diff_artifacts()` logic to `extra_artifacts()`
  - Register in default registry
  - Remove old code from `phase_runner.py`
  - Test: build phase still captures diffs

- [ ] **Task 6: Implement DocumentExtension**
  - Move `pr_description.md` logic to `extra_artifacts()`
  - Move `_maybe_create_pr_after_document()` logic to `on_complete()`
  - Update context with PR state fields
  - Register in default registry
  - Remove old code from `orchestrator.py` and `phase_runner.py`
  - Test: document phase creates PR, sets context fields

- [ ] **Task 7: Implement ShipExtension**
  - Implement `should_skip()` checking `pr_creation_attempted` and `pr_creation_failed`
  - Register in default registry
  - Remove skip logic from `orchestrator.py`
  - Test: ship skipped when PR fails, runs when PR succeeds

- [ ] **Task 8: Cleanup and documentation**
  - Remove dead code
  - Update docstrings
  - Add `docs/architecture/extensions.md`

### Acceptance Criteria

- [ ] **AC 1:** PhaseExtension protocol exists with `should_skip()`, `on_complete()`, `extra_artifacts()` methods
- [ ] **AC 2:** ExtensionRegistry can register extensions and query by phase
- [ ] **AC 3:** Build phase captures `diff.txt` and `diff_stats.json` via BuildExtension
- [ ] **AC 4:** Document phase saves `pr_description.md` and creates PR via DocumentExtension
- [ ] **AC 5:** Ship phase is skipped when `pr_creation_failed=True` via ShipExtension
- [ ] **AC 6:** RunContext has `pr_creation_attempted`, `pr_creation_failed`, `pr_failure_reason` fields
- [ ] **AC 7:** No phase-specific logic remains in `orchestrator.py` (except phase sequencing)
- [ ] **AC 8:** All existing tests pass
- [ ] **AC 9:** Extension failures are non-blocking (log warning, continue)

## Additional Context

### Dependencies

Extensions need access to these services (via constructor injection):

| Extension | Dependencies |
|-----------|-------------|
| `BuildExtension` | `ArtifactManager` |
| `DocumentExtension` | `ArtifactManager`, `GitConfig`, `ProgressDisplay`, `runs_dir: Path` |
| `ShipExtension` | None |

### Testing Strategy

**Unit Tests:**
- `test_extension_registry.py` - Registry registration and lookup
- `test_build_extension.py` - Git diff capture
- `test_document_extension.py` - PR creation, artifact saving
- `test_ship_extension.py` - Skip logic conditions

**Integration Tests:**
- Full pipeline with extensions enabled
- Resume with PR state preserved
- Single-phase execution

**Mock Strategy:**
- Mock `ArtifactManager` for artifact tests
- Mock `ProgressDisplay.try_auto_create_pr()` for PR tests
- Use `MockExecutor` for full pipeline tests

### Notes

**Migration Safety:**
- Each task is independently deployable
- Tasks 1-4 add infrastructure with no behavior change
- Tasks 5-7 migrate one extension at a time
- Rollback: revert to old code paths if issues found

**Future Considerations (out of scope):**
- Config-driven extension registration via `config.yaml`
- Project-level custom extensions
- Extension ordering/priority
- Async extension hooks

### File Structure After Implementation

```
src/adw/core/
├── extensions/
│   ├── __init__.py          # Exports: PhaseExtension, ExtensionRegistry, create_default_registry
│   ├── base.py              # PhaseExtension protocol
│   ├── registry.py          # ExtensionRegistry class
│   ├── build.py             # BuildExtension
│   ├── document.py          # DocumentExtension
│   └── ship.py              # ShipExtension
├── orchestrator.py          # Creates registry, passes to PhaseRunner
├── phase_runner.py          # Calls extension lifecycle hooks
└── ...
```

### API Design

```python
# base.py
from typing import ClassVar, Protocol
from adw.models import RunContext, LLMResult, PhaseResult

class PhaseExtension(Protocol):
    """Extension point for phase-specific behavior."""

    phase: ClassVar[str]

    def should_skip(self, context: RunContext) -> tuple[bool, str | None]:
        """Return (should_skip, reason). Called before phase execution."""
        ...

    def on_complete(self, context: RunContext, result: PhaseResult) -> RunContext:
        """Called after phase completes. Returns updated context."""
        ...

    def extra_artifacts(
        self, context: RunContext, llm_result: LLMResult
    ) -> list[tuple[str, str]]:
        """Return [(artifact_name, content)] for additional artifacts."""
        ...


# registry.py
class ExtensionRegistry:
    def __init__(self) -> None:
        self._extensions: dict[str, list[PhaseExtension]] = {}

    def register(self, extension: PhaseExtension) -> None: ...
    def get_extensions(self, phase: str) -> list[PhaseExtension]: ...
    def should_skip_phase(self, phase: str, context: RunContext) -> tuple[bool, str | None]: ...
    def call_on_complete(self, phase: str, context: RunContext, result: PhaseResult) -> RunContext: ...
    def call_extra_artifacts(self, phase: str, context: RunContext, llm_result: LLMResult) -> list[tuple[str, str]]: ...


# Factory function
def create_default_registry(
    artifact_manager: ArtifactManager,
    git_config: GitConfig,
    progress_display: ProgressDisplay | None,
    runs_dir: Path,
) -> ExtensionRegistry:
    """Create registry with all built-in extensions."""
    registry = ExtensionRegistry()
    registry.register(BuildExtension(artifact_manager))
    registry.register(DocumentExtension(artifact_manager, git_config, progress_display, runs_dir))
    registry.register(ShipExtension())
    return registry
```
