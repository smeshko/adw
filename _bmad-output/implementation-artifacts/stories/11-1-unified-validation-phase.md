# Story 11.1: Unified Validation Phase

Status: in-progress
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want a single "Validation" phase that combines evidence, code review, and tests,
so that all quality checks happen in one coordinated loop.

## Acceptance Criteria

**Given** pipeline reaches validation
**When** the phase starts
**Then** it runs: Evidence Gathering → Code Review → Test Suite

**Given** all validators pass
**When** iteration completes
**Then** phase completes successfully, moves to Document

**Given** any validator finds issues
**When** iteration completes
**Then** issues are collected for triage

**Given** the unified validation phase
**When** configured in project.yaml
**Then** individual validators can be enabled/disabled:
```yaml
validation:
  enable_evidence: true
  enable_review: true
  enable_tests: true
```

## Tasks / Subtasks

### Task 1: Create ValidationPhase Class
- [x] Create `src/adw/validation/__init__.py` package
- [x] Create `src/adw/validation/phase.py` with `ValidationPhase` class
- [x] Implement `run(context: RunContext) -> ValidationResult` method
- [x] Define `ValidationResult` model with `passed: bool`, `issues: list[ValidationIssue]`, `iteration: int`
- [x] Add phase to PHASE_SEQUENCE in pipeline orchestrator (validate already exists)

### Task 2: Create Validator Protocol
- [ ] Define `Validator` Protocol in `src/adw/validation/validators/base.py`
- [ ] Protocol methods: `validate(context: RunContext) -> list[ValidationIssue]`, `name: str`
- [ ] Create `ValidatorRegistry` to manage enabled validators
- [ ] Support dynamic validator loading based on configuration

### Task 3: Implement TestValidator
- [ ] Create `src/adw/validation/validators/test_validator.py`
- [ ] Execute configured test command (default: `pytest` or `npm test` based on platform)
- [ ] Parse test output for failures using regex patterns
- [ ] Convert each failing test to a `ValidationIssue` with source=TEST
- [ ] Handle test timeout and test command not found errors

### Task 4: Implement ReviewValidator
- [ ] Create `src/adw/validation/validators/review_validator.py`
- [ ] Use LLM executor to run code review prompt against changes
- [ ] Parse LLM response for structured issues
- [ ] Convert review findings to `ValidationIssue` with source=REVIEW
- [ ] Support configurable review focus areas (security, error_handling, edge_cases)

### Task 5: Implement EvidenceValidator
- [ ] Create `src/adw/validation/validators/evidence_validator.py`
- [ ] Call evidence gathering system (Epic 8 integration)
- [ ] Compare gathered evidence against plan requirements
- [ ] Convert missing evidence to `ValidationIssue` with source=EVIDENCE
- [ ] Handle platform detection for evidence type requirements

### Task 6: Add Validation Configuration
- [ ] Add `validation` section to `ProjectConfig` model
- [ ] Configuration fields:
  - `enable_evidence: bool = True`
  - `enable_review: bool = True`
  - `enable_tests: bool = True`
  - `test_command: str | None = None` (auto-detect if None)
  - `test_timeout_seconds: int = 300`
  - `review_prompt: str | None = None` (custom review prompt path)
  - `review_focus: list[str] = ["security", "error_handling", "edge_cases"]`

### Task 7: Write Tests
- [ ] Unit tests for `ValidationPhase.run()` (5 tests)
- [ ] Unit tests for each Validator implementation (4 tests each = 12 tests)
- [ ] Unit tests for `ValidatorRegistry` (4 tests)
- [ ] Integration test for full validation phase with all validators (3 tests)
- [ ] Test configuration-based validator enabling/disabling (3 tests)

---

## Dependencies

- **Depends On:** None
- **Blocks:** Story 11.2
- **Can Parallel With:** None

### Dependency Rationale
- Story 11.2: Issue model needs to know what validators exist to categorize sources

---

## Developer Context

### Technical Requirements

1. **Phase Integration**
   - ValidationPhase must implement the existing Phase Protocol
   - Integrate into PHASE_SEQUENCE between Build and Document phases
   - Return PhaseResult compatible with existing pipeline flow

2. **Validator Execution**
   - Validators run sequentially: Evidence → Review → Tests
   - Each validator collects issues independently
   - All issues aggregated after all validators complete
   - No short-circuit on first failure (run all validators)

3. **Test Command Detection**
   - Detect project type from existing platform detection (Epic 8)
   - Python projects: `pytest`
   - Node projects: `npm test`
   - Custom command overrides via config

### Architecture Compliance

**File Location:** `src/adw/validation/`

**New Package Structure:**
```
src/adw/
├── validation/
│   ├── __init__.py           # Re-exports ValidationPhase, Validator
│   ├── phase.py              # ValidationPhase class
│   ├── config.py             # ValidationConfig model
│   └── validators/
│       ├── __init__.py       # Re-exports all validators
│       ├── base.py           # Validator Protocol, ValidatorRegistry
│       ├── test_validator.py # TestValidator implementation
│       ├── review_validator.py # ReviewValidator implementation
│       └── evidence_validator.py # EvidenceValidator implementation
```

**Model Additions:**
```python
# src/adw/models/config.py
class ValidationConfig(BaseModel):
    enable_evidence: bool = True
    enable_review: bool = True
    enable_tests: bool = True
    test_command: str | None = None
    test_timeout_seconds: int = 300
    review_prompt: str | None = None
    review_focus: list[str] = Field(default=["security", "error_handling", "edge_cases"])
    max_iterations: int = 5
    max_fix_attempts_per_issue: int = 2
    stall_threshold: int = 2
    triage_mode: Literal["auto", "manual", "hybrid"] = "auto"
    auto_dismiss_info: bool = True

class ProjectConfig(BaseModel):
    # ... existing fields ...
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| subprocess | stdlib | Test command execution |
| asyncio | stdlib | Async test execution |
| Pydantic | 2.12+ | Config/model validation |
| re | stdlib | Test output parsing |

**Integration Points:**
- Epic 3: Hook execution for test command
- Epic 5: Pipeline phase integration
- Epic 8: Evidence gathering system

### File Structure Requirements

**New Files:**
- `src/adw/validation/__init__.py`
- `src/adw/validation/phase.py`
- `src/adw/validation/config.py`
- `src/adw/validation/validators/__init__.py`
- `src/adw/validation/validators/base.py`
- `src/adw/validation/validators/test_validator.py`
- `src/adw/validation/validators/review_validator.py`
- `src/adw/validation/validators/evidence_validator.py`

**Modified Files:**
- `src/adw/models/config.py` - Add ValidationConfig
- `src/adw/models/__init__.py` - Export ValidationConfig
- `src/adw/core/orchestrator.py` - Add validation phase to sequence

**Test Files:**
- `tests/unit/validation/__init__.py`
- `tests/unit/validation/test_phase.py`
- `tests/unit/validation/validators/__init__.py`
- `tests/unit/validation/validators/test_base.py`
- `tests/unit/validation/validators/test_test_validator.py`
- `tests/unit/validation/validators/test_review_validator.py`
- `tests/unit/validation/validators/test_evidence_validator.py`
- `tests/integration/test_validation_phase.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_phase.py
class TestValidationPhase:
    def test_run_all_validators_pass(self, mock_validators):
        """Phase completes successfully when all validators pass."""

    def test_run_collects_all_issues(self, mock_validators_with_issues):
        """Phase aggregates issues from all validators."""

    def test_run_respects_config_disabled(self, mock_config):
        """Disabled validators are not executed."""

    def test_run_continues_after_validator_error(self, failing_validator):
        """Phase continues to next validator on error."""

    def test_run_returns_validation_result(self, mock_validators):
        """Phase returns proper ValidationResult structure."""
```

**Validator Tests:**
```python
# tests/unit/validation/validators/test_test_validator.py
class TestTestValidator:
    def test_validate_pytest_success(self, mock_subprocess):
        """Returns empty issues list on test success."""

    def test_validate_pytest_failures(self, mock_subprocess):
        """Parses pytest output and returns issues for failures."""

    def test_validate_npm_test(self, mock_subprocess, node_project):
        """Uses npm test for Node.js projects."""

    def test_validate_timeout(self, mock_subprocess):
        """Returns timeout issue when tests exceed limit."""
```

---

## Previous Story Intelligence

This is the first story in Epic 11 (Validation Loop). No previous story learnings available.

**Relevant Patterns from Other Epics:**
- Epic 3 established hook execution patterns (subprocess handling)
- Epic 5 established phase runner and pipeline orchestration patterns
- Epic 8 established evidence gathering patterns

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 8 stories: Evidence gathering implementation
- Epic 5 stories: Phase sequence and runner implementation
- Epic 3 stories: Hook execution with capture

**Established Patterns:**
- Phases return structured results with success/failure status
- Configuration models use Pydantic with sensible defaults
- Subprocess execution uses asyncio for streaming output
- Errors wrapped in typed exceptions with context

---

## Latest Technical Information

**Validation Best Practices (2025):**
- Run all validators rather than fail-fast for comprehensive feedback
- Aggregate issues with severity levels for triage
- Support both automated and manual triage modes
- Persist validation state for resume capability

**Test Output Parsing:**
- pytest: Parse `=== FAILURES ===` section, extract test names and messages
- npm test: Parse for `FAIL` and `Error:` patterns
- Generic: Look for non-zero exit code as fallback

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: ValidationConfig goes in `models/config.py`
- **Exception hierarchy**: Create `ValidationError` (may already exist)
- **Type annotations required**: All functions fully typed
- **Structured logging**: Use `logger.info("Validation started", validators=enabled_validators)`
- **Phase Protocol**: Must implement `run(context) -> PhaseResult`

---

## Dev Notes

### Implementation Approach

1. Start with ValidationConfig and ValidationPhase skeleton
2. Implement Validator Protocol and registry
3. Add TestValidator (most straightforward)
4. Add ReviewValidator (requires LLM integration)
5. Add EvidenceValidator (requires Epic 8 integration)
6. Integrate into pipeline orchestrator
7. Write comprehensive tests

### Key Design Decisions

1. **Sequential Validator Execution**: Run validators in order to avoid race conditions
2. **No Fail-Fast**: Collect all issues for comprehensive triage
3. **Config-Driven**: All validators can be disabled via configuration
4. **Platform Detection**: Reuse Epic 8's platform detection for test command

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.1]
- [Source: _bmad-output/architecture.md#Phase Execution]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.1

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created ValidationPhase class with run() method, ValidationResult and ValidationIssue models, ValidationConfig. The "validate" phase already exists in PHASE_SEQUENCE so no modification needed. Implemented Validator Protocol in phase.py for future validator implementations.

### File List

**New Files:**
- `src/adw/validation/__init__.py` - Package exports
- `src/adw/validation/config.py` - ValidationConfig model
- `src/adw/validation/models.py` - ValidationResult, ValidationIssue, ValidationSource
- `src/adw/validation/phase.py` - ValidationPhase class with Validator Protocol
- `src/adw/validation/validators/__init__.py` - Validators package (empty, for Tasks 3-5)
- `tests/unit/validation/__init__.py` - Test package
- `tests/unit/validation/test_phase.py` - 12 unit tests for ValidationPhase and models
