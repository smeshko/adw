# Story 11.2: Validation Issue Model

Status: draft
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want validation issues tracked with structured metadata,
so that triage and fix tracking work reliably.

## Acceptance Criteria

**Given** a validation issue
**When** captured
**Then** it includes: id, source, severity, description, location, context

**Given** issue sources
**When** categorized
**Then** options are: TEST, REVIEW, EVIDENCE

**Given** issue severity
**When** categorized
**Then** options are: ERROR (must fix), WARNING (should fix), INFO (optional)

**Given** issue tracking
**When** fix is attempted
**Then** issue records: fix_attempted, fix_attempt_count, last_fix_result

## Tasks / Subtasks

### Task 1: Create ValidationIssue Model
- [ ] Create `src/adw/validation/models.py` for validation-specific models
- [ ] Define `IssueSource` enum: TEST, REVIEW, EVIDENCE
- [ ] Define `IssueSeverity` enum: ERROR, WARNING, INFO
- [ ] Define `FixResult` enum: RESOLVED, PARTIAL, FAILED, NOT_ATTEMPTED
- [ ] Create `ValidationIssue` Pydantic model with all required fields

### Task 2: Implement Issue ID Generation
- [ ] Use ULID for unique issue IDs (reuse existing ULID utility)
- [ ] Format: `VI-{ulid}` for human-readable prefix
- [ ] Ensure IDs are stable across serialization/deserialization

### Task 3: Define Issue Location Model
- [ ] Create `IssueLocation` model with:
  - `file_path: str | None`
  - `line_start: int | None`
  - `line_end: int | None`
  - `function_name: str | None`
  - `test_name: str | None`
- [ ] Support multiple locations per issue (for cross-file issues)

### Task 4: Add Issue Context
- [ ] Create `IssueContext` model with:
  - `code_snippet: str | None`
  - `error_message: str | None`
  - `stack_trace: str | None`
  - `related_files: list[str]`
  - `suggestion: str | None`
- [ ] Limit context fields to prevent excessive storage

### Task 5: Implement Fix Tracking Fields
- [ ] Add to ValidationIssue:
  - `fix_attempted: bool = False`
  - `fix_attempt_count: int = 0`
  - `last_fix_result: FixResult = FixResult.NOT_ATTEMPTED`
  - `fix_history: list[FixAttempt]`
- [ ] Create `FixAttempt` model with timestamp, result, and notes

### Task 6: Add Issue Comparison and Hashing
- [ ] Implement `__eq__` for issue comparison
- [ ] Implement `__hash__` for set operations
- [ ] Create `is_same_issue(other: ValidationIssue)` for fuzzy matching
- [ ] Support detecting if an issue was fixed vs still present

### Task 7: Add Serialization Methods
- [ ] Implement `to_dict()` for JSON serialization
- [ ] Implement `from_dict()` class method for deserialization
- [ ] Implement `to_markdown()` for human-readable format
- [ ] Support YAML serialization for persistence

### Task 8: Write Tests
- [ ] Unit tests for ValidationIssue model (8 tests)
- [ ] Unit tests for IssueLocation model (4 tests)
- [ ] Unit tests for IssueContext model (4 tests)
- [ ] Unit tests for FixAttempt tracking (4 tests)
- [ ] Unit tests for issue comparison/hashing (4 tests)
- [ ] Unit tests for serialization (4 tests)

---

## Dependencies

- **Depends On:** Story 11.1
- **Blocks:** Story 11.3, Story 11.4, Story 11.6
- **Can Parallel With:** None

### Dependency Rationale
- Story 11.1: Issue model needs validators to understand issue sources
- Story 11.3: Triage system operates on ValidationIssue objects
- Story 11.4: Fix loop needs issue tracking metadata (fix_attempted, fix_attempt_count)
- Story 11.6: State persistence needs issue model schema for serialization

---

## Developer Context

### Technical Requirements

1. **Pydantic Model Design**
   - Use Pydantic v2 features (model_validator, computed_field)
   - Ensure all fields have sensible defaults
   - Support JSON Schema generation for documentation

2. **Issue Identification**
   - Each issue must have a unique, stable ID
   - Support detecting "same issue" across validation runs
   - Hash based on source + location + description (not ID)

3. **Storage Efficiency**
   - Limit string fields to reasonable lengths
   - Truncate code snippets and stack traces if too long
   - Use optional fields for non-essential context

### Architecture Compliance

**File Location:** `src/adw/validation/models.py`

**Model Definitions:**
```python
# src/adw/validation/models.py
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class IssueSource(str, Enum):
    TEST = "TEST"
    REVIEW = "REVIEW"
    EVIDENCE = "EVIDENCE"

class IssueSeverity(str, Enum):
    ERROR = "ERROR"      # Must fix - blocks pipeline
    WARNING = "WARNING"  # Should fix - can be deferred
    INFO = "INFO"        # Optional - can be dismissed

class FixResult(str, Enum):
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"

class IssueLocation(BaseModel):
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    function_name: str | None = None
    test_name: str | None = None

class IssueContext(BaseModel):
    code_snippet: str | None = Field(None, max_length=2000)
    error_message: str | None = Field(None, max_length=1000)
    stack_trace: str | None = Field(None, max_length=5000)
    related_files: list[str] = Field(default_factory=list)
    suggestion: str | None = Field(None, max_length=500)

class FixAttempt(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    result: FixResult
    notes: str | None = None
    changes_made: list[str] = Field(default_factory=list)

class ValidationIssue(BaseModel):
    id: str  # VI-{ulid}
    source: IssueSource
    severity: IssueSeverity
    description: str
    location: IssueLocation | None = None
    locations: list[IssueLocation] = Field(default_factory=list)
    context: IssueContext | None = None

    # Fix tracking
    fix_attempted: bool = False
    fix_attempt_count: int = 0
    last_fix_result: FixResult = FixResult.NOT_ATTEMPTED
    fix_history: list[FixAttempt] = Field(default_factory=list)

    # Triage fields (set in Story 11.3)
    triage_decision: str | None = None  # FIX, DISMISS, DEFER
    triage_reason: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Pydantic | 2.12+ | Model definition and validation |
| ulid-py | 2.7+ | Issue ID generation |
| datetime | stdlib | Timestamps |

### File Structure Requirements

**New Files:**
- `src/adw/validation/models.py`

**Modified Files:**
- `src/adw/validation/__init__.py` - Export models
- `src/adw/models/__init__.py` - Re-export validation models

**Test Files:**
- `tests/unit/validation/test_models.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_models.py
class TestValidationIssue:
    def test_create_with_required_fields(self):
        """Issue created with id, source, severity, description."""

    def test_create_with_location(self):
        """Issue includes file location details."""

    def test_create_with_multiple_locations(self):
        """Issue can have multiple affected locations."""

    def test_context_truncation(self):
        """Long context fields are truncated to limits."""

    def test_fix_attempt_tracking(self):
        """Fix attempts are recorded in history."""

    def test_issue_equality(self):
        """Same source/location/description equals same issue."""

    def test_issue_hashing(self):
        """Issues can be used in sets."""

    def test_is_same_issue_fuzzy_match(self):
        """Fuzzy matching detects similar issues."""

class TestIssueSerialization:
    def test_to_dict(self):
        """Issue serializes to dict correctly."""

    def test_from_dict(self):
        """Issue deserializes from dict correctly."""

    def test_to_markdown(self):
        """Issue renders to readable markdown."""

    def test_round_trip(self):
        """Serialize and deserialize preserves data."""
```

---

## Previous Story Intelligence

**Learnings from Story 11.1:**
- ValidationPhase creates issues during validator execution
- Each validator produces issues with their respective source type
- Issues are aggregated before triage

**Relevant Patterns from Other Epics:**
- Epic 4 established state persistence patterns (RunContext serialization)
- Pydantic models used throughout with consistent patterns
- ULID generation via existing utility

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 4 stories: RunContext model patterns
- Epic 7 stories: Log entry model patterns (similar structure)

**Established Patterns:**
- Models use Pydantic with Field() for defaults and constraints
- Enums use str base for JSON serialization
- Optional fields explicitly typed as `T | None`

---

## Latest Technical Information

**Pydantic v2 Best Practices (2025):**
- Use `model_validator` for cross-field validation
- Use `computed_field` for derived properties
- Use `ConfigDict` for model configuration
- Prefer `Field()` over class attributes for documentation

**Issue Tracking Patterns:**
- Unique IDs enable cross-reference in logs and reports
- Severity levels enable automated triage decisions
- Fix history enables learning from failed attempts

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: ValidationIssue models go in `validation/models.py`
- **Type annotations required**: All fields fully typed
- **Serialization support**: Models must support dict/JSON conversion
- **Enums as str**: Use `str, Enum` base for JSON compatibility

---

## Dev Notes

### Implementation Approach

1. Define enums first (IssueSource, IssueSeverity, FixResult)
2. Create IssueLocation and IssueContext helper models
3. Create FixAttempt model for tracking
4. Create ValidationIssue with all fields
5. Add comparison/hashing methods
6. Add serialization methods
7. Write comprehensive tests

### Key Design Decisions

1. **ULID for IDs**: Sortable, unique, URL-safe
2. **Multiple Locations**: Some issues span files (refactoring issues)
3. **Embedded Triage Fields**: Simplifies state management
4. **Fix History**: Enables learning from repeated failures

### Hash Implementation Note

```python
def __hash__(self) -> int:
    # Hash based on immutable identifying characteristics
    return hash((
        self.source,
        self.description[:100],  # First 100 chars
        self.location.file_path if self.location else None,
        self.location.line_start if self.location else None,
    ))
```

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.2]
- [Source: _bmad-output/architecture.md#Data Models]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.2

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

### Completion Notes List

### File List
