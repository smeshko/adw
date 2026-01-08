# Story 16.3: Simplify Configuration

<!-- TEMPLATE SECTION: story_header -->
Status: ready-for-dev
Linear Issue: not-configured
Epic: 16 - Validation Phase Simplification
Created: 2026-01-08

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer,
I want validation configuration simplified,
so that there are fewer options to manage.

## Acceptance Criteria

**Given** validation configuration
**When** defined in project.yaml
**Then** only these options exist:
```yaml
validation:
  enabled: true
  test_command: "pytest"  # or auto-detect
  timeout_seconds: 600    # generous for LLM to do full cycle
```

**Given** removed options
**When** configuration is loaded
**Then** these are gone:
- `max_iterations`
- `max_fix_attempts_per_issue`
- `stall_threshold`
- `triage_mode`
- `auto_dismiss_info`
- `enable_evidence`
- `enable_review`
- `review_focus`

## Tasks / Subtasks

- [ ] **Task 1: Update ValidationConfig model**
  - Modify `src/adw/validation/config.py`
  - Remove all iteration-related fields
  - Remove all triage-related fields
  - Keep only: `enabled`, `test_command`, `timeout_seconds`

- [ ] **Task 2: Remove unused config handling**
  - Remove config parsing for deleted fields
  - Remove config validation for deleted fields
  - Update any code that reads deleted config values

- [ ] **Task 3: Update project.yaml schema**
  - Simplify the validation section in schema
  - Remove deprecated fields from documentation

- [ ] **Task 4: Update default project template**
  - Simplify `.adw/project.yaml` template
  - Use new minimal configuration

- [ ] **Task 5: Update documentation**
  - Update any docs referencing old config options
  - Document the simplified configuration

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->

**Current validation configuration (Epic 11):**
```yaml
validation:
  # Validators to run
  enable_evidence: true
  enable_review: true
  enable_tests: true

  # Iteration limits
  max_iterations: 5
  max_fix_attempts_per_issue: 2
  stall_threshold: 2

  # Triage mode
  triage_mode: auto           # auto | manual | hybrid
  auto_dismiss_info: true     # Auto-dismiss INFO severity

  # Test configuration
  test_command: "pytest"
  test_timeout_seconds: 300

  # Review configuration
  review_prompt: null         # Custom review prompt path
  review_focus:               # Focus areas for review
    - security
    - error_handling
    - edge_cases
```

**New simplified configuration:**
```yaml
validation:
  enabled: true
  test_command: "pytest"
  timeout_seconds: 600
```

That's a reduction from 13+ fields to 3 fields.

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->

1. **Backward compatibility:** Old configs with removed fields should not error - just ignore them with a deprecation warning
2. **Auto-detection:** If `test_command` is not specified, auto-detect based on project files (package.json -> npm test, pyproject.toml -> pytest)
3. **Reasonable defaults:** `enabled: true`, `timeout_seconds: 600`

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
<!-- Constraints the developer MUST follow from architecture docs -->

**From project-context.md:**
- All models in `src/adw/models/` - ValidationConfig should be in models
- Use Pydantic for config validation
- Type annotations required
- Use structured logging when warning about deprecated fields

**Config file location:** `src/adw/validation/config.py`

**Current ValidationConfig structure:**
```python
class ValidationConfig(BaseModel):
    enable_evidence: bool = True
    enable_review: bool = True
    enable_tests: bool = True
    max_iterations: int = 5
    max_fix_attempts_per_issue: int = 2
    stall_threshold: int = 2
    triage_mode: Literal["auto", "manual", "hybrid"] = "auto"
    auto_dismiss_info: bool = True
    test_command: str | None = None
    test_timeout_seconds: int = 300
    review_prompt: str | None = None
    review_focus: list[str] = Field(default_factory=list)
```

**Simplified ValidationConfig:**
```python
class ValidationConfig(BaseModel):
    enabled: bool = True
    test_command: str | None = None  # Auto-detect if not specified
    timeout_seconds: int = 600

    model_config = ConfigDict(extra="ignore")  # Ignore deprecated fields
```

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
<!-- Specific versions, APIs, and usage patterns -->

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | Config model with `extra="ignore"` |
| PyYAML | 6.0+ | Config file parsing |

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
<!-- Where files should be created/modified, naming conventions -->

**Files to MODIFY:**
- `src/adw/validation/config.py` - Simplify ValidationConfig
- `src/adw/validation/__init__.py` - Update exports if needed
- `.adw/project.yaml` (template) - Simplify validation section
- `tests/unit/validation/test_config.py` - Update tests

**Schema/Documentation to UPDATE:**
- Any JSON schema files for project.yaml
- README or docs referencing validation config

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
<!-- Testing standards, frameworks, coverage expectations -->

1. **Config loading tests:**
   ```python
   def test_simple_config_loads():
       """Test new minimal config loads correctly."""
       config = ValidationConfig(
           enabled=True,
           test_command="pytest",
           timeout_seconds=600
       )
       assert config.enabled is True
       assert config.test_command == "pytest"
       assert config.timeout_seconds == 600

   def test_old_config_ignored():
       """Test old fields are silently ignored."""
       config = ValidationConfig(
           enabled=True,
           max_iterations=5,  # Old field - should be ignored
           triage_mode="auto"  # Old field - should be ignored
       )
       assert config.enabled is True
       assert not hasattr(config, 'max_iterations')
   ```

2. **Auto-detection tests:**
   ```python
   def test_test_command_autodetect_python():
       """Test pytest detected for Python projects."""
       # Given a project with pyproject.toml
       # When test_command is None
       # Then "pytest" should be detected

   def test_test_command_autodetect_node():
       """Test npm test detected for Node projects."""
       # Given a project with package.json
       # When test_command is None
       # Then "npm test" should be detected
   ```

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
<!-- Learnings from previous story implementation (if story_num > 1) -->

**Dependencies:**
- Story 16.1 removes the loop logic that uses these config fields
- Story 16.2 creates the prompt that replaces the need for these fields
- This story should wait for 16.1 and 16.2 to complete

**From Epic 11 implementation:**
- Config grew complex to support triage modes, iteration limits, etc.
- Much of the complexity was in handling edge cases
- Simplification removes all those edge cases

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
<!-- Recent commit patterns, files modified, conventions observed -->

**Commit pattern:**
```
refactor(epic-16): Simplify validation configuration (Story 16.3)

- Reduce ValidationConfig from 13 fields to 3
- Add extra="ignore" for backward compatibility
- Update project.yaml template
- Remove deprecated config documentation

BREAKING: Old config fields are ignored (not error)
```

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
<!-- Web research results for current library versions, API changes, best practices -->

**Pydantic v2 ConfigDict:**
```python
from pydantic import BaseModel, ConfigDict

class ValidationConfig(BaseModel):
    model_config = ConfigDict(
        extra="ignore",  # Ignore unknown fields
        validate_default=True,
    )
```

This allows old configs to continue working without errors.

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Config keys use `snake_case` in YAML
- Pydantic for all config models
- Use `Field(default=...)` for defaults with metadata

---

## Dev Notes

### Configuration Comparison

| Old Field | Kept? | Reason |
|-----------|-------|--------|
| `enable_evidence` | NO | LLM decides what to run |
| `enable_review` | NO | LLM decides what to run |
| `enable_tests` | NO | Always run tests |
| `max_iterations` | NO | LLM handles iteration |
| `max_fix_attempts_per_issue` | NO | LLM handles iteration |
| `stall_threshold` | NO | LLM handles iteration |
| `triage_mode` | NO | No triage system |
| `auto_dismiss_info` | NO | No triage system |
| `test_command` | YES | Need to know how to run tests |
| `test_timeout_seconds` | Renamed to `timeout_seconds` | Still need timeout |
| `review_prompt` | NO | Single unified prompt |
| `review_focus` | NO | Prompt includes all review aspects |
| `enabled` | NEW | Global enable/disable |

### Project Structure Notes

- This is a simplification story - removing complexity
- Backward compatibility via `extra="ignore"` is critical
- Consider logging a deprecation warning for old fields

### References

- [Source: _bmad-output/epics/epic-16-validation-simplification.md#Story 16.3]
- [Source: _bmad-output/epics/epic-11-validation-loop.md#Configuration]
- [Source: src/adw/validation/config.py] (current config)

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
- **Can Parallel With:** Story 16.4

### Dependency Rationale
- Story 16.1: Must know what SDK loop configs are being removed
- Story 16.2: Must know what the prompt expects (timeout, test_command)
