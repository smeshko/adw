# Story 16.4: Update Phase Result Model

<!-- TEMPLATE SECTION: story_header -->
Status: done
Linear Issue: not-configured
Epic: 16 - Validation Phase Simplification
Created: 2026-01-08

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer,
I want the validation phase result model simplified,
so that it matches the new single-call approach.

## Acceptance Criteria

**Given** validation phase completes
**When** result is captured
**Then** it includes only:
```python
class ValidationResult(BaseModel):
    passed: bool
    tests_passed: bool
    code_review_passed: bool
    issues_fixed: list[str]       # one-line summaries
    issues_remaining: list[str]   # one-line summaries
    summary: str
```

## Tasks / Subtasks

- [x] **Task 1: Simplify ValidationResult model**
  - Update `src/adw/validation/models.py`
  - Replace complex model with simplified version
  - Remove all iteration/triage tracking fields

- [x] **Task 2: Remove ValidationIssue model**
  - Delete the detailed `ValidationIssue` model
  - Replace with simple string summaries
  - Update any code that creates ValidationIssue objects

- [x] **Task 3: Remove iteration/triage tracking models**
  - Remove `TriageDecision` enum
  - Remove `TriagedIssue` model
  - Remove `FixAttempt` model
  - Remove `FixResult` model
  - Remove `LoopState` model
  - Remove `ValidationState` model (iteration tracking)

- [x] **Task 4: Update serialization**
  - Ensure ValidationResult serializes correctly to JSON
  - Update any JSON schema files
  - Test round-trip serialization

- [x] **Task 5: Update all usages**
  - Update ValidationPhase to use new model
  - Update report generation
  - Update any CLI display code

- [x] **Task 6: Update tests**
  - Update model tests for new structure
  - Remove tests for deleted models

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->

**Current models in `src/adw/validation/models.py`:**

```python
# Currently exported (from __init__.py):
- FixAttempt           # TO DELETE
- FixResult            # TO DELETE
- IssueContext         # TO DELETE
- IssueLocation        # TO DELETE
- IssueSeverity        # TO DELETE
- IssueSource          # TO DELETE
- LoopState            # TO DELETE
- TriageDecision       # TO DELETE
- TriagedIssue         # TO DELETE
- ValidationIssue      # TO DELETE
- ValidationResult     # TO SIMPLIFY
- ValidationSource     # KEEP (for validators)
- ValidationState      # TO DELETE (iteration state)
```

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->

1. **Simple model:** Only 6 fields in ValidationResult
2. **String-based issues:** Issues are one-line summaries, not complex objects
3. **Backward compatibility:** Old serialized results won't load (acceptable - runs restart fresh)

**New model:**
```python
from pydantic import BaseModel

class ValidationResult(BaseModel):
    """Result of the unified validation phase."""

    passed: bool
    """True if all tests pass and code review is clean."""

    tests_passed: bool
    """True if all tests passed."""

    code_review_passed: bool
    """True if code review found no issues."""

    issues_fixed: list[str]
    """One-line summaries of issues that were fixed."""

    issues_remaining: list[str]
    """One-line summaries of issues that couldn't be fixed."""

    summary: str
    """Human-readable summary of validation results."""
```

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
<!-- Constraints the developer MUST follow from architecture docs -->

**From project-context.md:**
- All models in `src/adw/models/` - Consider moving ValidationResult there
- Full type annotations required
- Use Pydantic BaseModel

**Current location:** `src/adw/validation/models.py`
**Consider:** Moving to `src/adw/models/validation.py` for consistency

**Naming conventions:**
- Class: `ValidationResult` (PascalCase)
- Fields: `tests_passed` (snake_case)
- No `Optional[X]` - use `X | None` or `list[str]` (not None)

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
<!-- Specific versions, APIs, and usage patterns -->

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | Model definition and validation |

**Serialization:**
```python
# To JSON
result.model_dump_json()

# From JSON
ValidationResult.model_validate_json(json_str)
```

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
<!-- Where files should be created/modified, naming conventions -->

**Files to MODIFY:**
- `src/adw/validation/models.py` - Simplify models
- `src/adw/validation/__init__.py` - Update exports (remove deleted models)
- `src/adw/validation/phase.py` - Use new model
- `src/adw/validation/report.py` - Simplify report generation

**Files to potentially UPDATE:**
- `src/adw/models/__init__.py` - If moving ValidationResult there
- `tests/unit/validation/test_models.py` - Update tests

**Exports to REMOVE from `__init__.py`:**
```python
# DELETE these exports:
- FixAttempt
- FixResult
- IssueContext
- IssueLocation
- IssueSeverity
- IssueSource
- LoopState
- TriageDecision
- TriagedIssue
- ValidationIssue
- ValidationState
```

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
<!-- Testing standards, frameworks, coverage expectations -->

1. **Model tests:**
   ```python
   def test_validation_result_creation():
       """Test creating a simple ValidationResult."""
       result = ValidationResult(
           passed=True,
           tests_passed=True,
           code_review_passed=True,
           issues_fixed=["Fixed null check in handler"],
           issues_remaining=[],
           summary="All checks passed"
       )
       assert result.passed is True
       assert len(result.issues_fixed) == 1

   def test_validation_result_failed():
       """Test failed validation result."""
       result = ValidationResult(
           passed=False,
           tests_passed=True,
           code_review_passed=False,
           issues_fixed=[],
           issues_remaining=["Security vulnerability in auth.py"],
           summary="Code review found issues"
       )
       assert result.passed is False
       assert len(result.issues_remaining) == 1
   ```

2. **Serialization tests:**
   ```python
   def test_validation_result_json_roundtrip():
       """Test JSON serialization round-trip."""
       original = ValidationResult(
           passed=True,
           tests_passed=True,
           code_review_passed=True,
           issues_fixed=[],
           issues_remaining=[],
           summary="Clean"
       )
       json_str = original.model_dump_json()
       restored = ValidationResult.model_validate_json(json_str)
       assert original == restored
   ```

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
<!-- Learnings from previous story implementation (if story_num > 1) -->

**Dependencies:**
- Story 16.1 removes code that creates complex issue objects
- Story 16.2 defines the output schema that this model must match
- This story should wait for 16.1 and 16.2 to complete

**From Epic 11 implementation:**
- `ValidationIssue` had 8+ fields for tracking
- `TriagedIssue` added triage decision tracking
- `FixAttempt` tracked multiple fix attempts per issue
- All this complexity is being replaced with string lists

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
<!-- Recent commit patterns, files modified, conventions observed -->

**Commit pattern:**
```
refactor(epic-16): Simplify ValidationResult model (Story 16.4)

- Reduce ValidationResult to 6 fields
- Remove ValidationIssue, TriagedIssue, FixAttempt models
- Replace complex issue objects with string summaries
- Update exports and usages

Models removed: 10
Fields reduced: ~50 → 6
```

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
<!-- Web research results for current library versions, API changes, best practices -->

**Pydantic v2 best practices:**
```python
from pydantic import BaseModel, Field

class ValidationResult(BaseModel):
    passed: bool
    tests_passed: bool
    code_review_passed: bool
    issues_fixed: list[str] = Field(default_factory=list)
    issues_remaining: list[str] = Field(default_factory=list)
    summary: str = ""
```

Using `Field(default_factory=list)` ensures each instance gets its own list.

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Models in `src/adw/models/` (consider moving ValidationResult)
- Use Pydantic BaseModel
- Full type annotations
- snake_case for field names

---

## Dev Notes

### Models Comparison

**Old models (being deleted):**
| Model | Fields | Purpose |
|-------|--------|---------|
| ValidationIssue | ~8 | Detailed issue tracking |
| TriagedIssue | ~5 | Issue + triage decision |
| TriageDecision | enum | FIX/DISMISS/DEFER |
| FixAttempt | ~4 | Track fix attempts |
| FixResult | ~3 | Result of fix attempt |
| LoopState | ~6 | Loop iteration state |
| ValidationState | ~8 | Full validation state |
| IssueContext | ~3 | Issue context |
| IssueLocation | ~4 | File/line location |
| IssueSeverity | enum | ERROR/WARNING/INFO |
| IssueSource | enum | TEST/REVIEW/EVIDENCE |

**New model (keeping):**
| Model | Fields | Purpose |
|-------|--------|---------|
| ValidationResult | 6 | Simple pass/fail with summaries |

### JSON Schema

The ValidationResult must match this JSON schema (from Story 16.2 prompt):
```json
{
  "type": "object",
  "required": ["passed", "tests_passed", "code_review_passed", "issues_fixed", "issues_remaining", "summary"],
  "properties": {
    "passed": {"type": "boolean"},
    "tests_passed": {"type": "boolean"},
    "code_review_passed": {"type": "boolean"},
    "issues_fixed": {"type": "array", "items": {"type": "string"}},
    "issues_remaining": {"type": "array", "items": {"type": "string"}},
    "summary": {"type": "string"}
  }
}
```

### Project Structure Notes

- This is the final story in Epic 16
- Depends on 16.1 and 16.2 completing first
- Can run in parallel with 16.3

### References

- [Source: _bmad-output/epics/epic-16-validation-simplification.md#Story 16.4]
- [Source: src/adw/validation/models.py] (current models)
- [Source: src/adw/validation/__init__.py] (current exports)

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used



### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 16.1, Story 16.2
- **Blocks:** None
- **Can Parallel With:** Story 16.3

### Dependency Rationale
- Story 16.1: Must know what iteration/triage tracking to remove from models
- Story 16.2: Must match the output schema defined in the prompt
