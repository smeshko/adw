# Story 1.2: Create Core Pydantic Models

Status: done
Linear Issue: not-configured
Epic: 1 - Project Scaffolding & Test Infrastructure
Created: 2025-12-31

---

## Story

As a developer,
I want centralized Pydantic models for RunContext, PhaseResult, and ProjectConfig,
so that all state management uses validated, type-safe data structures.

## Acceptance Criteria

**Given** the models module at `src/adw/models/`
**When** I import RunContext
**Then** it includes: run_id (ULID), feature_description (str), current_phase (str), phase_history (list), started_at (datetime), artifacts (dict)
**And** it serializes to JSON with snake_case keys

**Given** a RunContext instance
**When** I call `model_copy(update={"current_phase": "build"})`
**Then** a new instance is returned with the updated phase
**And** the original instance is unchanged (immutability)

**Given** a PhaseResult model
**When** I create an instance
**Then** it includes: phase (str), status (enum: pending|running|completed|failed), started_at, completed_at, artifacts (list[str]), error (optional)

**Given** a ProjectConfig model
**When** I load from valid YAML
**Then** it includes: name, language, framework, platform, test_command, build_command, llm config section

**Given** invalid data for any model
**When** I attempt to create an instance
**Then** Pydantic raises ValidationError with clear field-level messages

## Tasks / Subtasks

### Task 1: Create Models Package Structure
- [x] Create `src/adw/models/__init__.py` with exports
- [x] Create `src/adw/models/context.py` for context models
- [x] Create `src/adw/models/phase.py` for phase-related models
- [x] Create `src/adw/models/config.py` for configuration models

### Task 2: Implement RunContext Model
- [x] Define RunContext with all required fields
- [x] Add ULID validation for run_id field
- [x] Add datetime handling for started_at
- [x] Implement proper JSON serialization with snake_case

### Task 3: Implement PhaseResult Model
- [x] Define PhaseStatus enum (pending, running, completed, failed)
- [x] Define PhaseResult with status, timing, and artifacts
- [x] Add optional error field for failure cases

### Task 4: Implement ProjectConfig Model
- [x] Define LLMConfig nested model
- [x] Define ProjectConfig with project metadata
- [x] Add YAML loading classmethod
- [x] Add validation for required fields

### Task 5: Add Additional Context Models
- [x] Define SessionContext for current session state
- [x] Define ProjectContext for resolved project info
- [x] Define Artifact model for artifact metadata

### Task 6: Write Unit Tests
- [x] Test RunContext creation and serialization
- [x] Test PhaseResult with all status values
- [x] Test ProjectConfig YAML loading
- [x] Test model_copy immutability
- [x] Test validation error messages

---

## Developer Context

### Technical Requirements

**From Architecture Document (ARCH-5, ARCH-11):**
- All Pydantic models MUST be in `src/adw/models/`
- Use Pydantic 2.12+ with native features
- State persistence uses `model_dump_json()` / `model_validate_json()`
- Run IDs use ULID format via python-ulid

**From Architecture Patterns:**
- snake_case for all JSON keys (Pydantic default)
- Immutable updates via `model_copy(update={...})`
- No camelCase aliases

### Architecture Compliance

**Model Location Rules:**
```python
# CORRECT - models in models/
from adw.models import RunContext, PhaseResult

# WRONG - never define models elsewhere
class RunContext(BaseModel):  # NO - not in models/
    pass
```

**JSON Serialization:**
```python
# Output: {"run_id": "01HQ...", "current_phase": "plan"}
context.model_dump_json()  # snake_case preserved
```

**Immutable State Updates:**
```python
# CORRECT
new_context = context.model_copy(update={"current_phase": "build"})

# WRONG - direct mutation
context.current_phase = "build"  # NO
```

### Library & Framework Requirements

**Pydantic 2.12+ Patterns:**
```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum

class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class RunContext(BaseModel):
    run_id: str = Field(..., description="ULID run identifier")
    feature_description: str
    current_phase: str
    phase_history: list[str] = Field(default_factory=list)
    started_at: datetime
    artifacts: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        # Validate ULID format
        if len(v) != 26:
            raise ValueError("Invalid ULID format")
        return v
```

### File Structure Requirements

**Files to Create:**

```
src/adw/models/
├── __init__.py        # Re-exports all models
├── context.py         # RunContext, SessionContext, ProjectContext
├── phase.py           # PhaseStatus, PhaseResult, Artifact
└── config.py          # ProjectConfig, LLMConfig, PhaseConfig
```

**Model Definitions:**

**context.py:**
- `RunContext` - Full run state
- `SessionContext` - Current session (derived from RunContext)
- `ProjectContext` - Resolved project configuration
- `StateSnapshot` - Point-in-time state for debugging

**phase.py:**
- `PhaseStatus` - Enum for phase states
- `PhaseResult` - Result of a single phase execution
- `Artifact` - Artifact metadata
- `ArtifactType` - Enum for artifact types

**config.py:**
- `ProjectConfig` - Main project configuration
- `LLMConfig` - LLM-specific settings
- `PhaseConfig` - Per-phase configuration
- `HookConfig` - Hook configuration

### Testing Requirements

**Test File:** `tests/unit/models/test_context.py`

**Tests to Write:**

```python
def test_run_context_creation():
    """RunContext creates with valid data."""
    context = RunContext(
        run_id="01HQX...",
        feature_description="Add login",
        current_phase="plan",
        started_at=datetime.now()
    )
    assert context.current_phase == "plan"

def test_run_context_serialization():
    """RunContext serializes to snake_case JSON."""
    context = RunContext(...)
    json_str = context.model_dump_json()
    data = json.loads(json_str)
    assert "run_id" in data  # snake_case
    assert "runId" not in data  # no camelCase

def test_run_context_immutability():
    """model_copy creates new instance."""
    original = RunContext(...)
    updated = original.model_copy(update={"current_phase": "build"})
    assert original.current_phase == "plan"
    assert updated.current_phase == "build"
    assert original is not updated

def test_run_context_invalid_ulid():
    """Invalid ULID raises ValidationError."""
    with pytest.raises(ValidationError):
        RunContext(run_id="invalid", ...)

def test_phase_result_status_enum():
    """PhaseResult accepts all status values."""
    for status in PhaseStatus:
        result = PhaseResult(phase="plan", status=status)
        assert result.status == status

def test_project_config_from_yaml():
    """ProjectConfig loads from YAML string."""
    yaml_content = '''
    name: my-project
    language: python
    framework: fastapi
    '''
    config = ProjectConfig.from_yaml(yaml_content)
    assert config.name == "my-project"
```

---

## Previous Story Intelligence

**Depends on Story 1.1:**
- Project structure must exist (`src/adw/models/` directory)
- Dependencies must be installed (Pydantic, python-ulid)
- pyproject.toml must have correct configuration

**What Story 1.1 Created:**
- Basic project structure with uv
- Dependencies installed
- `src/adw/` package exists

---

## Git Intelligence

**Expected Prior Commits:**
- Story 1.1: Project scaffolding with uv and Typer

**Recommended Commit Pattern:**
```
feat(models): add core Pydantic models

- Add RunContext for run state management
- Add PhaseResult and PhaseStatus for phase tracking
- Add ProjectConfig for project configuration
- Implement ULID validation for run_id
- Add unit tests for all models
```

---

## Latest Technical Information

**Pydantic 2.12+ Features:**
- `model_copy()` replaces deprecated `.copy()`
- `model_dump_json()` for serialization
- `model_validate_json()` for deserialization
- `Field()` for field metadata
- `field_validator` decorator for validation

**Python 3.13+ Type Syntax:**
```python
# Use these (Python 3.13+)
list[str]           # not List[str]
dict[str, Any]      # not Dict[str, Any]
str | None          # not Optional[str]
```

**ULID Format:**
- 26 characters
- Lexicographically sortable
- Timestamp-prefixed
- Example: `01HQX5P3Z7V8R2M4N6T9W1Y3C`

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- All models MUST be in src/adw/models/
- Use `model_copy()` for immutable updates
- snake_case for all JSON keys
- Type annotations required on all fields

---

## Dev Notes

### Critical Success Factors

1. **Centralized Models:** All models in `src/adw/models/` - no exceptions
2. **ULID Validation:** run_id must be validated as proper ULID format
3. **Immutability Pattern:** Use model_copy() for all state updates
4. **snake_case JSON:** No camelCase aliases

### Model Hierarchy

```
RunContext
├── run_id: str (ULID)
├── feature_description: str
├── current_phase: str
├── phase_history: list[str]
├── started_at: datetime
├── completed_at: datetime | None
├── status: str
└── artifacts: dict[str, list[str]]

PhaseResult
├── phase: str
├── status: PhaseStatus
├── started_at: datetime
├── completed_at: datetime | None
├── artifacts: list[str]
├── error: str | None
└── duration_ms: int | None

ProjectConfig
├── name: str
├── language: str
├── framework: str | None
├── platform: str
├── test_command: str | None
├── build_command: str | None
└── llm: LLMConfig
```

### References

- [Source: _bmad-output/architecture.md#State-Persistence]
- [Source: _bmad-output/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: _bmad-output/architecture.md#Naming-Patterns]
- [Source: _bmad-output/project-context.md#Critical-Implementation-Rules]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Completion Notes List

- All 12 Pydantic models implemented per architecture spec
- ULID validation uses Crockford Base32 character set validation
- All models use `frozen=False` with `validate_assignment=True` for flexibility with validation
- `computed_field` decorator used for PhaseResult.duration_ms
- 46 unit tests passing with comprehensive coverage
- All acceptance criteria verified through tests

### File List

**Source Files:**
- `src/adw/models/__init__.py` - Package exports for all 12 models
- `src/adw/models/context.py` - RunContext, SessionContext, ProjectContext, StateSnapshot
- `src/adw/models/phase.py` - PhaseStatus, PhaseResult, ArtifactType, Artifact
- `src/adw/models/config.py` - ProjectConfig, LLMConfig, PhaseConfig, HookConfig

**Test Files:**
- `tests/unit/models/__init__.py` - Test package init
- `tests/unit/models/test_context.py` - 13 tests for context models
- `tests/unit/models/test_phase.py` - 17 tests for phase models
- `tests/unit/models/test_config.py` - 16 tests for config models

---

## Dependencies

- **Depends On:** Story 1.1
- **Blocks:** Story 1.4, Story 1.5
- **Can Parallel With:** Story 1.3

### Dependency Rationale
- Story 1.1: Requires project structure with src/adw/models/ directory and dependencies installed
- Story 1.4: LLMResult model needed by executor, RunContext for testing
- Story 1.5: Models needed for sample_run_context and sample_project_config fixtures
