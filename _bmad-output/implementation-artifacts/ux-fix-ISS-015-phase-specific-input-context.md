# Story: Phase-Specific Input Context Injection

<!-- TEMPLATE SECTION: story_header -->
Status: done
Linear Issue: not-configured
Epic: 12 - Task Manager Integration / Tech Debt
Created: 2026-01-06

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer configuring ADW phases,
I want to specify input files in PhaseConfig that get loaded and made available as template variables,
so that I can inject PRD, architecture, or other documentation into specific phases without abusing pre_hook.

## Acceptance Criteria

- [x] PhaseConfig model supports optional `input_files: dict[str, str]` field
- [x] PhaseRunner loads files specified in `input_files` at phase start
- [x] Loaded file contents are available as `{{ inputs.name }}` in prompt templates
- [x] File paths are resolved relative to project root
- [x] Missing files raise `ConfigError` with helpful suggestion
- [x] Empty `input_files` (default) preserves existing behavior
- [x] Configuration works in both `adw.yaml` project config and command-level config
- [x] All existing tests pass
- [x] New tests cover input file loading, error handling, and template access

## Tasks / Subtasks

### Task 1: Extend PhaseConfig Model
- [x] Add `input_files: dict[str, str] | None = None` field to `PhaseConfig` in `src/adw/models/config.py`
- [x] Add field validator for path validation (non-empty keys, relative paths)
- [x] Update model docstring with usage example

### Task 2: Implement Input File Loading in PhaseRunner
- [x] Add `_load_input_files()` method to `PhaseRunner` in `src/adw/core/phase_runner.py`
- [x] Load files relative to project root (use `context.worktree_path` if in worktree)
- [x] Return `dict[str, str]` mapping name to content
- [x] Raise `ConfigError` with code `INPUT_FILE_NOT_FOUND` for missing files
- [x] Handle encoding errors gracefully

### Task 3: Integrate with Template Rendering
- [x] Pass loaded input files to `_load_and_render_prompt()`
- [x] Add `inputs` key to template variables dict
- [x] Ensure inputs are available alongside existing `artifacts` map

### Task 4: Update adw.yaml Schema Documentation
- [x] Add `input_files` to phase config examples
- [x] Document file path resolution behavior
- [x] Add example showing PRD/architecture injection

### Task 5: Testing
- [x] Unit tests for PhaseConfig.input_files validation
- [x] Unit tests for _load_input_files() method
- [x] Integration tests for template variable access
- [x] Error handling tests for missing files
- [x] Regression tests ensuring existing behavior unchanged

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Architecture Docs:** `_bmad-output/architecture.md`
- PhaseConfig defined in "Project Configuration" section
- Template engine uses simple regex patterns: `{{variable.path}}`
- Three-tier config resolution (project -> user -> bundled)

**PRD:** `_bmad-output/prd.md`
- FR22: System renders prompt templates with variable substitution
- FR24: System executes pre-hooks and captures stdout for prompt context

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
- Python 3.13+
- Pydantic 2.12+ for model validation
- Maintain backward compatibility - existing configs without `input_files` must work
- Follow existing patterns in PhaseRunner for file operations
- Use Path operations consistent with worktree support (Story 10.5)

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->

**Current PhaseConfig Implementation:**
File: `src/adw/models/config.py:102-122`

```python
class PhaseConfig(BaseModel):
    """Configuration for a specific phase.

    Attributes:
        enabled: Whether this phase is enabled
        timeout_seconds: Phase-specific timeout override
        pre_hook: Shell command to run before phase
        post_hook: Shell command to run after phase
    """

    enabled: bool = Field(default=True, description="Whether this phase is enabled")
    timeout_seconds: int | None = Field(
        default=None, description="Phase-specific timeout override"
    )
    pre_hook: str | None = Field(
        default=None, description="Shell command to run before phase"
    )
    post_hook: str | None = Field(
        default=None, description="Shell command to run after phase"
    )
```

**Target Implementation:**

```python
class PhaseConfig(BaseModel):
    """Configuration for a specific phase.

    Attributes:
        enabled: Whether this phase is enabled
        timeout_seconds: Phase-specific timeout override
        pre_hook: Shell command to run before phase
        post_hook: Shell command to run after phase
        input_files: Optional mapping of names to file paths for template injection
    """

    enabled: bool = Field(default=True, description="Whether this phase is enabled")
    timeout_seconds: int | None = Field(
        default=None, description="Phase-specific timeout override"
    )
    pre_hook: str | None = Field(
        default=None, description="Shell command to run before phase"
    )
    post_hook: str | None = Field(
        default=None, description="Shell command to run after phase"
    )
    input_files: dict[str, str] | None = Field(
        default=None,
        description="Mapping of variable names to file paths for template injection",
    )
```

**PhaseRunner._load_and_render_prompt() Integration:**
File: `src/adw/core/phase_runner.py:267-364`

Current template variables (line 322-352):
```python
variables = {
    "context": context,
    "pre_hook_output": pre_hook_output,
    "artifacts": artifacts_map,
    "run_id": context.run_id,
    "phase": phase,
    "feature": context.feature_description,
    "worktree_path": str(context.worktree_path) if context.worktree_path else "",
}
```

Target: Add `"inputs": loaded_input_files` to this dict.

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->

**Pydantic 2.12+:**
- Use `Field()` with description for new field
- Optional field with `| None = None` default
- Field validator if needed for path validation

**Path Operations:**
- Use `pathlib.Path` for all file operations
- Resolve paths relative to project root (or `context.worktree_path`)
- Check file existence before reading
- Handle UTF-8 encoding with explicit `encoding="utf-8"`

**Exception Handling:**
- Use `ConfigError` from `adw.exceptions`
- Include `code`, `message`, `suggestion` fields
- Code: `INPUT_FILE_NOT_FOUND` for missing files

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->

**Files to Modify:**

| File | Changes |
|------|---------|
| `src/adw/models/config.py` | Add `input_files` field to `PhaseConfig` (lines 102-122) |
| `src/adw/core/phase_runner.py` | Add `_load_input_files()` method, update `_load_and_render_prompt()` |

**Test Files:**

| File | Tests to Add |
|------|-------------|
| `tests/unit/models/test_config.py` | PhaseConfig.input_files validation |
| `tests/unit/core/test_phase_runner.py` | _load_input_files(), template integration |

**No New Files Required** - This is a targeted enhancement to existing modules.

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->

**Unit Tests (test_config.py):**
```python
def test_phase_config_input_files_none_by_default():
    """PhaseConfig.input_files should be None by default."""
    config = PhaseConfig()
    assert config.input_files is None

def test_phase_config_input_files_valid():
    """PhaseConfig accepts valid input_files mapping."""
    config = PhaseConfig(input_files={"prd": "docs/prd.md"})
    assert config.input_files == {"prd": "docs/prd.md"}

def test_phase_config_input_files_empty_dict():
    """PhaseConfig accepts empty input_files dict."""
    config = PhaseConfig(input_files={})
    assert config.input_files == {}
```

**Unit Tests (test_phase_runner.py):**
```python
def test_load_input_files_success(tmp_path: Path):
    """_load_input_files reads and returns file contents."""
    # Create test file
    prd_file = tmp_path / "docs" / "prd.md"
    prd_file.parent.mkdir(parents=True)
    prd_file.write_text("# PRD Content")

    # Test loading
    runner = PhaseRunner(...)
    result = runner._load_input_files(
        {"prd": "docs/prd.md"},
        project_root=tmp_path
    )
    assert result == {"prd": "# PRD Content"}

def test_load_input_files_missing_file():
    """_load_input_files raises ConfigError for missing files."""
    runner = PhaseRunner(...)
    with pytest.raises(ConfigError) as exc_info:
        runner._load_input_files({"prd": "nonexistent.md"}, project_root=Path("/tmp"))
    assert exc_info.value.code == "INPUT_FILE_NOT_FOUND"

def test_template_access_inputs_variable():
    """Template can access {{ inputs.prd }} variable."""
    # Integration test showing full flow
    ...
```

**Coverage Requirement:** >80% for new code paths

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->

**Related Refactoring Story:** `refactor-ISS-012-config-driven-artifact-capture.md`
- Similar pattern: moving hardcoded behavior to configuration
- Uses `command.yaml` for artifact config - we use `adw.yaml` for input files
- Demonstrates config-driven extension approach

**Key Learning:**
- Config-driven approaches enable extensibility without core code changes
- Maintain backward compatibility with default values
- Include validation with helpful error messages

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->

**Recent Commits:**
- `3906c6c` - Remove (cleanup)
- `8b21010` - [adw] Plan: Add user authentication with OAuth2
- `83d43ff` - feat(story-11-7): Validation Report Generation
- `ecb3eed` - feat(epic-12): create all Task Manager Integration stories

**Patterns to Follow:**
- Commit message format: `feat(component): description`
- Reference issue IDs: Include ISS-015 reference
- Include tests with implementation
- Small, focused commits

**Suggested Commit Sequence:**
1. `feat(models): add input_files field to PhaseConfig (ISS-015)`
2. `feat(phase-runner): implement input file loading (ISS-015)`
3. `feat(phase-runner): integrate inputs with template rendering (ISS-015)`
4. `test(phase-runner): add input file loading tests (ISS-015)`

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->

**Pydantic 2.12+ Field Patterns:**
```python
# Optional dict field with None default
input_files: dict[str, str] | None = Field(
    default=None,
    description="...",
)

# Validation handled by model_validator if needed
@model_validator(mode="after")
def validate_input_files(self) -> Self:
    if self.input_files:
        for name, path in self.input_files.items():
            if not name or not path:
                raise ValueError("input_files keys and values must not be empty")
    return self
```

**Path Resolution Best Practice:**
```python
# Resolve relative to project root, respecting worktree
def _resolve_input_path(
    self,
    relative_path: str,
    project_root: Path | None,
    worktree_path: Path | None,
) -> Path:
    base = worktree_path or project_root or Path.cwd()
    return base / relative_path
```

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

**CRITICAL - Must Follow:**
1. All models in `src/adw/models/` - PhaseConfig is already there
2. Full type annotations required - use `dict[str, str] | None`
3. Use Pydantic for all structured data - already using
4. Exception hierarchy - use `ConfigError` from `adw.exceptions`
5. Context managers for file operations - use `with open(...)`

**Naming Conventions:**
- Method: `_load_input_files` (snake_case, private prefix)
- Field: `input_files` (snake_case)
- Error code: `INPUT_FILE_NOT_FOUND` (SCREAMING_SNAKE_CASE)

---

## Dev Notes

- **Effort:** Small-Medium (localized change to 2 files)
- **Risk:** Low - additive change with backward compatibility
- **Alternative Considered:** Putting this in `command.yaml` per-command instead of `adw.yaml` per-phase
  - Chose `adw.yaml` because input files are project-specific, not command-specific
  - Commands should be reusable across projects; input files are project configuration

### Implementation Tips

1. **Start with the model change** - easiest to verify
2. **Add the helper method** - `_load_input_files()` isolated for testing
3. **Wire it up** - single line change in `_load_and_render_prompt()`
4. **Test incrementally** - verify each step before proceeding

### Edge Cases to Handle

- Empty `input_files` dict (`{}`) - should work, returns empty dict
- `None` input_files (default) - should work, returns empty dict
- File not found - raise `ConfigError` with helpful message
- File encoding issues - handle with explicit UTF-8, raise on decode error
- Relative path escaping project root - consider security validation
- Worktree vs main repo - use `context.worktree_path` when present

### Project Structure Notes

- Models go in `src/adw/models/` (PhaseConfig already there)
- Core logic in `src/adw/core/phase_runner.py`
- Tests mirror source: `tests/unit/models/test_config.py`, `tests/unit/core/test_phase_runner.py`

### References

- [Source: ISS-015-no-mechanism-to-inject-phase-specific-input-context.md]
- [Source: src/adw/models/config.py:102-122]
- [Source: src/adw/core/phase_runner.py:267-364]
- [Source: _bmad-output/architecture.md - PhaseConfig section]

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Story created from ISS-015 UX issue analysis and conversation context.

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Story created: 2026-01-06
- Ultimate context engine analysis completed - comprehensive developer guide created
- Related to refactor-ISS-012 pattern for config-driven extensions

### File List

Files to touch:
- `src/adw/models/config.py` (PhaseConfig model)
- `src/adw/core/phase_runner.py` (_load_input_files, _load_and_render_prompt)
- `tests/unit/models/test_config.py` (PhaseConfig tests)
- `tests/unit/core/test_phase_runner.py` (input file loading tests)
