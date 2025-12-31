# Story 2.2: Create Template Engine with Variable Substitution

Status: ready-for-dev
Linear Issue: not-configured
Epic: 2 - Command Resolution & Templates
Created: 2025-12-31

---

## Story

As a developer,
I want templates rendered with {{variable}} substitution,
so that prompts can include dynamic content from the run context.

## Acceptance Criteria

**Given** a template string with `{{feature_description}}`
**When** rendered with context containing feature_description="Add login"
**Then** the output contains "Add login"

**Given** a template with `{{file:path/to/file.txt}}`
**When** the file exists and contains "file content"
**Then** the output contains "file content"

**Given** a template with `{{file:nonexistent.txt}}`
**When** rendering is attempted
**Then** ConfigError is raised with code "TEMPLATE_FILE_NOT_FOUND"

**Given** a template with nested variables `{{phase_{{index}}}}`
**When** rendering is attempted
**Then** only single-level substitution occurs (no recursive expansion)

**Given** a template with `{{unknown_var}}`
**When** rendering is attempted with strict mode
**Then** ConfigError is raised with code "UNKNOWN_VARIABLE"

**Given** a template with `{{unknown_var}}`
**When** rendering is attempted with lenient mode
**Then** the variable is left as-is in output

## Tasks / Subtasks

### Task 1: Create Template Engine Module Structure
- [x] Create `src/adw/commands/template.py` with `TemplateEngine` class
- [x] Export `TemplateEngine` from `src/adw/commands/__init__.py`

### Task 2: Implement Variable Substitution Pattern
- [x] Define regex pattern for `{{variable.path}}` syntax
- [x] Support dot notation for nested access (e.g., `{{context.run_id}}`)
- [x] Implement `render(template: str, context: dict) -> str`

### Task 3: Implement File Inclusion Pattern
- [x] Define regex pattern for `{{file:relative/path}}` syntax
- [x] Resolve paths relative to project root
- [x] Read and include file content
- [x] Raise `ConfigError(code="TEMPLATE_FILE_NOT_FOUND")` for missing files

### Task 4: Implement Strict vs Lenient Mode
- [ ] Add `strict: bool = True` parameter to render method
- [ ] In strict mode: raise `ConfigError(code="UNKNOWN_VARIABLE")` for unmatched variables
- [ ] In lenient mode: leave `{{unknown}}` as-is in output
- [ ] Log warning in lenient mode for unmatched variables

### Task 5: Implement Single-Level Substitution Guard
- [ ] Ensure no recursive expansion of variables
- [ ] Process template in single pass
- [ ] Document limitation clearly in docstring

### Task 6: Support Context Object Rendering
- [ ] Accept Pydantic models (RunContext, etc.) as context
- [ ] Use `model_dump()` to convert to dict for variable lookup
- [ ] Support nested attribute access via dot notation

### Task 7: Write Unit Tests
- [ ] Test basic variable substitution
- [ ] Test dot notation for nested access
- [ ] Test file inclusion with existing file
- [ ] Test file inclusion with missing file (ConfigError)
- [ ] Test strict mode with unknown variable (ConfigError)
- [ ] Test lenient mode with unknown variable (left as-is)
- [ ] Test no recursive expansion
- [ ] Test with Pydantic model context

---

## Relevant Feature Documentation

_No conditional docs matched for this story context._

---

## Developer Context

### Technical Requirements

- **FR22:** System renders prompt templates with variable substitution
- Architecture decision: Simple regex-based parser (no Jinja2)
- Two pattern types only: `{{variable}}` and `{{file:path}}`
- No recursive expansion (security and simplicity)

### Architecture Compliance

**From architecture.md - Template Engine Decision:**

> **Decision:** Simple regex-based parser
>
> Handles two patterns:
> - `{{variable.path}}` - Variable substitution from context
> - `{{file:relative/path}}` - File content inclusion
>
> **Rationale:** Jinja2 is overkill. Simple patterns cover all use cases.

**Implementation Pattern from architecture.md:**
```python
VARIABLE_PATTERN = r'\{\{([a-z_][a-z0-9_.]*)\}\}'
FILE_PATTERN = r'\{\{file:([^}]+)\}\}'
```

**Module Location:**
- `src/adw/commands/template.py` - Template engine lives here

**Exception Handling:**
- Use `ConfigError` with codes:
  - `TEMPLATE_FILE_NOT_FOUND` - File inclusion target missing
  - `UNKNOWN_VARIABLE` - Variable not in context (strict mode)

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| re | stdlib | Regex pattern matching |
| pathlib | stdlib | File path handling |
| Pydantic | 2.12+ | Context conversion via model_dump() |

**Regex Pattern Notes:**
- `{{variable}}` matches valid Python identifiers with optional dots
- `{{file:path}}` allows any non-brace characters in path
- Use `re.sub` with replacement function for processing

### File Structure Requirements

**Files to Create:**
```
src/adw/
└── commands/
    └── template.py    # TemplateEngine class

tests/
└── unit/
    └── commands/
        └── test_template.py
```

**Files to Modify:**
- `src/adw/commands/__init__.py` - Export TemplateEngine

### Testing Requirements

**Test File:** `tests/unit/commands/test_template.py`

**Test Cases (>80% coverage):**

1. **Variable Substitution:**
   ```python
   def test_simple_variable_substitution():
       template = "Hello, {{name}}!"
       context = {"name": "World"}
       assert engine.render(template, context) == "Hello, World!"

   def test_dot_notation_nested_access():
       template = "Run ID: {{context.run_id}}"
       context = {"context": {"run_id": "abc123"}}
       assert "abc123" in engine.render(template, context)
   ```

2. **File Inclusion:**
   ```python
   def test_file_inclusion(tmp_path):
       # Create test file
       test_file = tmp_path / "data.txt"
       test_file.write_text("file content")

       template = "Content: {{file:data.txt}}"
       # Assert file content included

   def test_file_not_found_raises_config_error():
       template = "{{file:nonexistent.txt}}"
       with pytest.raises(ConfigError) as exc:
           engine.render(template, {})
       assert exc.value.code == "TEMPLATE_FILE_NOT_FOUND"
   ```

3. **Strict vs Lenient Mode:**
   ```python
   def test_strict_mode_unknown_variable_raises():
       template = "{{unknown_var}}"
       with pytest.raises(ConfigError) as exc:
           engine.render(template, {}, strict=True)
       assert exc.value.code == "UNKNOWN_VARIABLE"

   def test_lenient_mode_preserves_unknown_variable():
       template = "{{unknown_var}}"
       result = engine.render(template, {}, strict=False)
       assert result == "{{unknown_var}}"
   ```

4. **Edge Cases:**
   ```python
   def test_no_recursive_expansion():
       # Context value contains template syntax
       context = {"value": "{{nested}}"}
       template = "{{value}}"
       result = engine.render(template, context)
       assert result == "{{nested}}"  # Not expanded

   def test_pydantic_model_context():
       from adw.models import RunContext
       context = RunContext(run_id="123", ...)
       template = "{{run_id}}"
       # Assert works with Pydantic model
   ```

**Fixtures Needed:**
- Temporary directory with test files for file inclusion
- Mock RunContext for Pydantic model testing

---

## Previous Story Intelligence

_This is the second story in Epic 2 but runs in parallel with 2.1._

**Relevant Context from Epic 1:**
- Exception hierarchy with `ConfigError` is implemented
- Pydantic models use `model_dump()` for serialization
- Logging patterns established for warnings

---

## Git Intelligence

**Recent Commits (Epic 1):**
- Exception hierarchy in `src/adw/exceptions.py`
- ConfigError includes `code`, `message`, `suggestion` fields

**Conventions Observed:**
- Type hints on all methods
- Docstrings with Args/Returns/Raises
- Test functions prefixed with `test_`

---

## Latest Technical Information

**Python re Module Best Practices:**
```python
import re
from typing import Callable

# Compile patterns once at module level
VARIABLE_RE = re.compile(r'\{\{([a-z_][a-z0-9_.]*)\}\}')
FILE_RE = re.compile(r'\{\{file:([^}]+)\}\}')

def render(template: str, context: dict) -> str:
    def replace_variable(match: re.Match) -> str:
        var_path = match.group(1)
        return resolve_variable(var_path, context)

    result = VARIABLE_RE.sub(replace_variable, template)
    # Then process file patterns...
    return result
```

**Dot Notation Access Pattern:**
```python
def resolve_variable(path: str, context: dict) -> str:
    """Resolve 'context.nested.value' to actual value."""
    parts = path.split('.')
    value = context
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
        if value is None:
            raise KeyError(path)
    return str(value)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All Pydantic models in `src/adw/models/`
- Use exception hierarchy, never bare Exception
- Full type annotations required
- Structured logging with context fields

---

## Dev Notes

### Key Implementation Decisions:

1. **No Jinja2:** Architecture explicitly chose simple regex over Jinja2 for simplicity.

2. **Order of Processing:** Variables first, then file inclusions. This ensures file paths can't be dynamically generated via variables (security).

3. **File Paths:** Relative to project root, not template location. Use `project_root` parameter or current working directory.

4. **Empty Values:** Treat `None` as empty string in substitution.

5. **Type Coercion:** Convert all values to `str()` when substituting.

### Project Structure Notes

- `src/adw/commands/template.py` - TemplateEngine class
- Independent of resolver.py - can be tested in isolation
- Will be used by loader.py in Story 2.3

### References

- [Source: _bmad-output/architecture.md#Template Engine]
- [Source: _bmad-output/prd.md#FR22 (Template Rendering)]
- [Source: _bmad-output/project-context.md#Exception Hierarchy]

---

## Dependencies

**Depends On:** None (Wave 1 - can start immediately)

**Blocks:**
- Story 2.3: Load and Render Phase Prompts (needs template rendering capability)

---

## Dev Agent Record

### Context Reference

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

