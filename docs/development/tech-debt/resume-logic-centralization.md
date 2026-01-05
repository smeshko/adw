# Tech Debt: Centralize Scattered Resume Logic

**Priority:** Medium
**Effort:** Medium
**Category:** Code Organization / DRY Violation
**Related Issues:** None

---

## Problem Statement

Resume logic is scattered across 4 different locations, resulting in duplicated validation, inconsistent behavior, and unused code.

## Current State Analysis

| Location | What it does | Issue |
|----------|--------------|-------|
| `cli/resume.py` | Finds run, validates status, determines phase, calls orchestrator | Duplicates validation logic |
| `orchestrator.resume()` | Loads context, validates, executes phases | Duplicates status check, phase logic |
| `interruption.py` | `can_resume()`, `prepare_resume()`, `get_resume_phase()` | Exported but **UNUSED** |
| `validation/state_manager.py` | Separate resume system for validation loop | Different semantics (iteration-level) |

## Specific Duplications

### 1. "Can resume" check - appears in 3 places

```python
# interruption.py:366
return context.status != "completed"

# orchestrator.py:723
if context.status == "completed": raise ConfigError

# resume.py:164
if context.status == "completed": raise ConfigError
```

### 2. Resume phase determination - appears in 2 places

```python
# resume.py:75
resume_phase = from_phase or context.current_phase

# orchestrator.py:732
resume_phase = from_phase or context.current_phase
```

### 3. Status transition to "running" - appears in 2 places

```python
# interruption.py:396-401 → prepare_resume() sets status="running" (UNUSED)
# orchestrator.py:743 → context.model_copy(update={"status": "running"})
```

---

## Proposed Solution: Centralized ResumeManager

### New File: `src/adw/core/resume_manager.py`

```python
class ResumeManager:
    """Centralized handler for all resume operations."""

    def __init__(
        self,
        context_manager: ContextManager,
        run_lookup: RunLookup,
    ) -> None: ...

    # --- Validation ---
    def can_resume(self, context: RunContext) -> bool: ...
    def validate_resumable(self, context: RunContext) -> None: ...  # raises if not

    # --- Resolution ---
    def find_run_to_resume(self, run_id: str | None) -> RunContext: ...
    def get_resume_phase(self, context: RunContext, from_phase: str | None = None) -> str: ...

    # --- Preparation ---
    def prepare_for_resume(self, context: RunContext, from_phase: str | None = None) -> ResumeInfo: ...

    # --- Status ---
    def get_resume_status(self, context: RunContext) -> ResumeStatus: ...
```

### New Models: `src/adw/models/resume.py`

```python
@dataclass
class ResumeInfo:
    """All information needed to execute a resume."""
    context: RunContext          # Updated context (status=running)
    resume_phase: str            # Phase to start from
    start_index: int             # Index in PHASE_SEQUENCE
    completed_phases: list[str]  # Phases already done


@dataclass
class ResumeStatus:
    """Status information for display."""
    run_id: str
    can_resume: bool
    resume_phase: str | None
    completed_phases: list[str]
    interrupted_phase: str | None
```

---

## Affected Components

### 1. `cli/resume.py` - Simplifies significantly

**Before:**
```python
def resume(...):
    context = _find_run_to_resume(run_id)  # 60 lines of logic
    resume_phase = from_phase or context.current_phase  # duplicated
    # validation duplicated
    orchestrator.resume(context.run_id, from_phase=from_phase)
```

**After:**
```python
def resume(...):
    resume_info = resume_manager.prepare_for_resume(run_id, from_phase)
    run_display.show_resume_header(resume_info)
    orchestrator.execute_resume(resume_info)
```

- `_find_run_to_resume()` → **DELETE** (moves to ResumeManager)
- Phase determination → **DELETE** (moves to ResumeManager)

### 2. `orchestrator.py` - Refactors `resume()` method

**Before:**
```python
def resume(self, run_id: str, from_phase: str | None = None) -> RunContext:
    context = self.context_manager.load(run_id)
    if context.status == "completed":  # duplicated check
        raise ConfigError(...)
    resume_phase = from_phase or context.current_phase  # duplicated
    # ... validation, artifact loading, execution
```

**After:**
```python
def resume(self, run_id: str, from_phase: str | None = None) -> RunContext:
    resume_info = self.resume_manager.prepare_for_resume(run_id, from_phase)
    return self._execute_resume(resume_info)

def execute_resume(self, resume_info: ResumeInfo) -> RunContext:
    """Execute a pre-prepared resume (for CLI direct calls)."""
    return self._execute_resume(resume_info)
```

- Validation logic → **MOVES** to ResumeManager
- Phase resolution → **MOVES** to ResumeManager
- `_load_artifacts_for_resume()` → **STAYS** (execution concern)

### 3. `interruption.py` - Remove unused functions

| Function | Action |
|----------|--------|
| `can_resume()` | **DELETE** → moves to ResumeManager |
| `prepare_resume()` | **DELETE** → moves to ResumeManager |
| `get_resume_phase()` | **DELETE** → moves to ResumeManager |
| `get_run_status()` | **REFACTOR** → use `ResumeManager.get_resume_status()` |
| `InterruptionHandler` | **KEEP** (signal handling is separate concern) |
| `ShutdownRequested` | **KEEP** |

### 4. `run_lookup.py` - No changes needed

RunLookup remains a pure data access layer. ResumeManager will use it internally.

### 5. `validation/state_manager.py` - Keep separate

The validation phase has different resume semantics (iteration-level within a phase, not phase-level). This should remain separate but could follow a similar pattern:

```python
class ValidationResumeManager:  # Future consideration
    """Handles resume within validation phase."""
```

---

## Dependency Graph

```
                  ┌─────────────────┐
                  │  ResumeManager  │
                  └────────┬────────┘
                           │ uses
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      ┌──────────┐  ┌──────────────┐  ┌─────────┐
      │RunLookup │  │ContextManager│  │ (models)│
      └──────────┘  └──────────────┘  └─────────┘

      ┌────────────────────────────────────────┐
      │              Consumers                  │
      ├────────────┬─────────────┬─────────────┤
      │ cli/resume │ Orchestrator│ (future)    │
      └────────────┴─────────────┴─────────────┘
```

---

## Implementation Checklist

| File | Changes |
|------|---------|
| **NEW** `src/adw/core/resume_manager.py` | Create centralized handler |
| **NEW** `src/adw/models/resume.py` | ResumeInfo, ResumeStatus models |
| `src/adw/core/__init__.py` | Export ResumeManager |
| `src/adw/core/interruption.py` | Remove `can_resume`, `prepare_resume`, `get_resume_phase` |
| `src/adw/core/orchestrator.py` | Inject ResumeManager, refactor `resume()` |
| `src/adw/cli/resume.py` | Use ResumeManager, delete `_find_run_to_resume()` |
| `src/adw/cli/bootstrap.py` | Wire up ResumeManager |
| Tests | Update/add tests for ResumeManager |

---

## Benefits

1. **Single source of truth** for resume logic
2. **Testable in isolation** - ResumeManager can be unit tested without orchestrator
3. **Reusable** - CLI, orchestrator, future API can all use it
4. **Clear separation** - data access (RunLookup) vs business logic (ResumeManager) vs execution (Orchestrator)
5. **Removes dead code** - unused functions in interruption.py
