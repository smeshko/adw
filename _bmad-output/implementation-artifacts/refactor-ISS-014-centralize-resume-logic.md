# Story: Centralize Resume Logic in ResumeManager

<!-- TEMPLATE SECTION: story_header -->
Status: ready-for-dev
Linear Issue: not-configured
Epic: Tech Debt - Core Architecture Refactoring
Created: 2026-01-05

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer maintaining ADW,
I want resume logic centralized in a single ResumeManager class,
so that I can modify resume behavior in one place without risking inconsistencies across multiple locations.

## Acceptance Criteria

- [ ] Create `ResumeManager` class with all resume logic
- [ ] Create `ResumeInfo` and `ResumeStatus` dataclasses
- [ ] Refactor `cli/resume.py` to use ResumeManager
- [ ] Refactor `orchestrator.py` to use ResumeManager
- [ ] Remove unused functions from `interruption.py`
- [ ] Wire up ResumeManager in `cli/bootstrap.py`
- [ ] All existing tests pass
- [ ] New unit tests for ResumeManager
- [ ] Dead code removed, no unused exports

## Tasks / Subtasks

### Task 1: Create ResumeManager Class
- [ ] Create `src/adw/core/resume_manager.py`
- [ ] Implement `can_resume()` method
- [ ] Implement `validate_resumable()` method
- [ ] Implement `find_run_to_resume()` method
- [ ] Implement `get_resume_phase()` method
- [ ] Implement `prepare_for_resume()` method
- [ ] Implement `get_resume_status()` method

### Task 2: Create Resume Models
- [ ] Create `src/adw/models/resume.py`
- [ ] Define `ResumeInfo` dataclass
- [ ] Define `ResumeStatus` dataclass
- [ ] Export from `src/adw/models/__init__.py`

### Task 3: Refactor CLI Resume Command
- [ ] Inject ResumeManager into resume command
- [ ] Replace `_find_run_to_resume()` with ResumeManager
- [ ] Remove duplicated validation logic
- [ ] Delete `_find_run_to_resume()` function

### Task 4: Refactor Orchestrator
- [ ] Inject ResumeManager via constructor
- [ ] Refactor `resume()` method to use ResumeManager
- [ ] Create `execute_resume(ResumeInfo)` for pre-prepared resumes
- [ ] Keep `_load_artifacts_for_resume()` (execution concern)

### Task 5: Clean Up Interruption Module
- [ ] Delete `can_resume()` - moves to ResumeManager
- [ ] Delete `prepare_resume()` - moves to ResumeManager
- [ ] Delete `get_resume_phase()` - moves to ResumeManager
- [ ] Refactor `get_run_status()` to use ResumeManager
- [ ] Keep `InterruptionHandler` and `ShutdownRequested`

### Task 6: Wire Up Dependencies
- [ ] Update `cli/bootstrap.py` to create ResumeManager
- [ ] Inject ResumeManager into Orchestrator
- [ ] Inject ResumeManager into resume command

### Task 7: Testing
- [ ] Unit tests for ResumeManager methods
- [ ] Integration tests for resume flow
- [ ] Verify no regressions in existing resume behavior

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Source:** `docs/development/tech-debt/resume-logic-centralization.md`

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
- Python 3.13+
- Pydantic 2.12+ for models
- Follow dependency injection pattern (constructor injection)
- Single source of truth for resume logic

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
**Current Duplication (4 Locations):**

| Location | What it does | Issue |
|----------|--------------|-------|
| `cli/resume.py` | Finds run, validates status, determines phase, calls orchestrator | Duplicates validation logic |
| `orchestrator.resume()` | Loads context, validates, executes phases | Duplicates status check, phase logic |
| `interruption.py` | `can_resume()`, `prepare_resume()`, `get_resume_phase()` | Exported but **UNUSED** |
| `validation/state_manager.py` | Separate resume system for validation loop | Different semantics (iteration-level) |

**Specific Duplications:**

1. **"Can resume" check - appears in 3 places:**
```python
# interruption.py:366
return context.status != "completed"

# orchestrator.py:723
if context.status == "completed": raise ConfigError

# resume.py:164
if context.status == "completed": raise ConfigError
```

2. **Resume phase determination - appears in 2 places:**
```python
# resume.py:75
resume_phase = from_phase or context.current_phase

# orchestrator.py:732
resume_phase = from_phase or context.current_phase
```

3. **Status transition to "running" - appears in 2 places:**
```python
# interruption.py:396-401 -> prepare_resume() sets status="running" (UNUSED)
# orchestrator.py:743 -> context.model_copy(update={"status": "running"})
```

**Target Architecture:**

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

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
- **Pydantic**: Use for ResumeInfo/ResumeStatus models (or dataclasses)
- **No new dependencies required**
- Follow existing patterns from ContextManager, RunLookup

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
**Files to Create:**
- `src/adw/core/resume_manager.py` - Centralized handler
- `src/adw/models/resume.py` - ResumeInfo, ResumeStatus models

**Files to Modify:**
- `src/adw/core/__init__.py` - Export ResumeManager
- `src/adw/core/interruption.py` - Remove unused functions
- `src/adw/core/orchestrator.py` - Inject ResumeManager, refactor `resume()`
- `src/adw/cli/resume.py` - Use ResumeManager, delete `_find_run_to_resume()`
- `src/adw/cli/bootstrap.py` - Wire up ResumeManager
- `src/adw/models/__init__.py` - Export new models

**Test Files:**
- `tests/unit/core/test_resume_manager.py` - New tests
- `tests/unit/models/test_resume.py` - Model tests
- Update existing resume-related tests

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
- Unit tests for all ResumeManager methods
- Test `can_resume()` with various context states
- Test `validate_resumable()` error cases
- Test `find_run_to_resume()` lookup logic
- Test `prepare_for_resume()` returns correct ResumeInfo
- Integration tests verifying CLI resume still works
- Coverage requirement: >80%

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
**Related patterns from recent commits:**
- `b7141c0` - "remove set_phase_runner in favor of constructor injection"
  - Use constructor injection for ResumeManager
  - Follow this exact pattern

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
Recent commits show:
- `b7141c0` - Refactoring: constructor injection over setters
- This story should follow the same pattern

**Key insight:** Constructor injection is the preferred DI pattern in this codebase.

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
N/A - No external dependencies or API changes.

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models MUST be in `src/adw/models/`
- Full type annotations required
- Use Pydantic for structured data (or dataclasses for simple DTOs)
- Follow exception hierarchy
- Immutable state updates with `model_copy(update=...)`

---

## Dev Notes

- Effort: Medium
- This is a significant refactoring but improves maintainability
- Keep `validation/state_manager.py` separate - different semantics (iteration-level)
- Potential future: Create `ValidationResumeManager` following same pattern

### Project Structure Notes

- New manager class in `src/adw/core/`
- New models in `src/adw/models/`
- Wire up in `cli/bootstrap.py`

### References

- [Source: docs/development/tech-debt/resume-logic-centralization.md]
- [Source: ISS-014-resume-logic-scattered-across-codebase.md]

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Story created from ISS-014 tech debt documentation.

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Story created: 2026-01-05
- Ultimate context engine analysis completed - comprehensive developer guide created

### File List

Files to create:
- `src/adw/core/resume_manager.py`
- `src/adw/models/resume.py`
- `tests/unit/core/test_resume_manager.py`
- `tests/unit/models/test_resume.py`

Files to modify:
- `src/adw/core/__init__.py`
- `src/adw/core/interruption.py`
- `src/adw/core/orchestrator.py`
- `src/adw/cli/resume.py`
- `src/adw/cli/bootstrap.py`
- `src/adw/models/__init__.py`
