# Story 2.4: Validate LLM Output Against Schema

Status: done
Linear Issue: not-configured
Epic: 2 - Command Resolution & Templates
Created: 2025-12-31

---

## Story

As a developer,
I want LLM output validated against an optional JSON schema,
so that I can ensure structured output meets expectations.

## Acceptance Criteria

**Given** a command directory with `schema.json`
**When** LLM output matches the schema
**Then** validation passes and returns parsed data

**Given** a command directory with `schema.json`
**When** LLM output doesn't match the schema
**Then** ValidationError is raised with specific field errors

**Given** a command directory without `schema.json`
**When** LLM output is received
**Then** no validation is performed and raw content is returned

**Given** LLM output as markdown with JSON code block
**When** schema validation is enabled
**Then** JSON is extracted from the code block before validation

**Given** multiple JSON code blocks in output
**When** extraction is attempted
**Then** the first valid JSON block matching the schema is used

## Tasks / Subtasks

### Task 1: Create Schema Validator Module
- [x] Create `src/adw/commands/validator.py` with `SchemaValidator` class
- [x] Export `SchemaValidator` from `src/adw/commands/__init__.py`

### Task 2: Implement JSON Extraction from Markdown
- [x] Implement `extract_json_from_markdown(content: str) -> list[str]`
- [x] Detect JSON code blocks (```json ... ```)
- [x] Detect untagged code blocks that contain JSON
- [x] Return list of potential JSON strings

### Task 3: Implement JSON Schema Validation
- [x] Implement `validate(content: str, schema: dict) -> dict`
- [x] Parse JSON from content
- [x] Validate against schema using jsonschema library
- [x] Return parsed dict on success

### Task 4: Implement ValidationError with Field Details
- [x] Use existing `ValidationError` from exception hierarchy
- [x] Include specific field paths that failed validation
- [x] Include expected type vs actual type
- [x] Include helpful suggestion for fixing

### Task 5: Implement Smart JSON Extraction
- [x] Try raw content as JSON first (for pure JSON responses)
- [x] Fall back to markdown extraction if raw fails
- [x] For multiple JSON blocks, try each against schema
- [x] Return first valid match
- [x] Raise ValidationError if none match

### Task 6: Implement No-Schema Passthrough
- [x] When schema is None, return content as-is (string)
- [x] No parsing or validation attempted
- [x] Log that validation was skipped

### Task 7: Write Unit Tests
- [x] Test valid JSON against matching schema
- [x] Test invalid JSON against schema (field errors)
- [x] Test JSON extraction from markdown code block
- [x] Test multiple JSON blocks (first valid wins)
- [x] Test no-schema passthrough
- [x] Test malformed JSON handling

---

## Relevant Feature Documentation

_No conditional docs matched for this story context._

---

## Developer Context

### Technical Requirements

- **FR23:** System validates LLM output against schema when provided
- JSON Schema draft-07 is the target version (per architecture)
- LLMs often wrap JSON in markdown code blocks - must handle this
- Graceful handling when no schema is provided

### Architecture Compliance

**From architecture.md - JSON Schema Validation:**

> **External Dependencies:**
> - JSON Schema (draft-07) for validation

**Validation Flow:**
1. Check if schema exists (from LoadedCommand)
2. If no schema, return raw content
3. Try to parse content as JSON directly
4. If that fails, extract JSON from markdown
5. Validate against schema
6. Return parsed dict or raise ValidationError

**Exception Hierarchy:**
- Use `ValidationError` from `src/adw/exceptions.py`
- Include `code="SCHEMA_VALIDATION_FAILED"`
- Include field-level error details

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| jsonschema | latest | JSON Schema validation |
| json | stdlib | JSON parsing |
| re | stdlib | Markdown code block extraction |

**Add to pyproject.toml:**
```toml
[project.dependencies]
jsonschema = "^4.20"  # or latest
```

**jsonschema Usage Pattern:**
```python
from jsonschema import validate, ValidationError as JsonSchemaError

def validate_against_schema(data: dict, schema: dict) -> None:
    try:
        validate(instance=data, schema=schema)
    except JsonSchemaError as e:
        raise ValidationError(
            code="SCHEMA_VALIDATION_FAILED",
            message=f"Schema validation failed: {e.message}",
            suggestion="Check LLM output format matches schema requirements",
            field_path=list(e.absolute_path),
        )
```

### File Structure Requirements

**Files to Create:**
```
src/adw/
└── commands/
    └── validator.py    # SchemaValidator class

tests/
└── unit/
    └── commands/
        └── test_validator.py
```

**Files to Modify:**
- `src/adw/commands/__init__.py` - Export SchemaValidator
- `pyproject.toml` - Add jsonschema dependency

### Testing Requirements

**Test File:** `tests/unit/commands/test_validator.py`

**Test Cases (>80% coverage):**

1. **Valid JSON Validation:**
   ```python
   def test_valid_json_passes_schema():
       schema = {"type": "object", "properties": {"name": {"type": "string"}}}
       content = '{"name": "test"}'
       result = validator.validate(content, schema)
       assert result == {"name": "test"}
   ```

2. **Invalid JSON Validation:**
   ```python
   def test_invalid_json_raises_validation_error():
       schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
       content = '{"age": "not a number"}'
       with pytest.raises(ValidationError) as exc:
           validator.validate(content, schema)
       assert exc.value.code == "SCHEMA_VALIDATION_FAILED"
       assert "age" in str(exc.value)  # Field mentioned in error
   ```

3. **Markdown Extraction:**
   ```python
   def test_extracts_json_from_markdown_code_block():
       content = '''
       Here is the result:
       ```json
       {"result": "value"}
       ```
       '''
       result = validator.validate(content, {"type": "object"})
       assert result == {"result": "value"}

   def test_extracts_from_untagged_code_block():
       content = '''
       ```
       {"result": "value"}
       ```
       '''
       result = validator.validate(content, {"type": "object"})
       assert result == {"result": "value"}
   ```

4. **Multiple Blocks:**
   ```python
   def test_first_valid_json_block_used():
       content = '''
       First attempt:
       ```json
       {"wrong": "format"}
       ```
       Second attempt:
       ```json
       {"name": "correct", "count": 5}
       ```
       '''
       schema = {
           "type": "object",
           "required": ["name", "count"],
           "properties": {"name": {"type": "string"}, "count": {"type": "integer"}}
       }
       result = validator.validate(content, schema)
       assert result == {"name": "correct", "count": 5}
   ```

5. **No Schema:**
   ```python
   def test_no_schema_returns_raw_content():
       content = "This is just text, not JSON"
       result = validator.validate(content, schema=None)
       assert result == content
   ```

6. **Malformed JSON:**
   ```python
   def test_malformed_json_raises_validation_error():
       content = '{"unclosed": '
       schema = {"type": "object"}
       with pytest.raises(ValidationError) as exc:
           validator.validate(content, schema)
       assert "parse" in exc.value.message.lower()
   ```

**Fixtures Needed:**
- Sample JSON schemas for testing
- Sample LLM output with various formats

---

## Previous Story Intelligence

**From Story 2.1 (Command Resolution):**
- `ResolvedCommand` indicates if schema.json exists via `has_schema`

**From Story 2.3 (Prompt Loading):**
- `LoadedCommand.schema` contains parsed schema dict (or None)
- Validator receives schema from LoadedCommand

---

## Git Intelligence

**Recent Commits (Epic 1):**
- ValidationError in exception hierarchy
- Pattern for including field details in errors

**Expected Files from Epic 2:**
- `src/adw/commands/loader.py` provides schema via LoadedCommand

---

## Latest Technical Information

**jsonschema Library (v4.20+):**
```python
from jsonschema import validate, Draft7Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

# Use Draft 7 explicitly
validator = Draft7Validator(schema)
errors = list(validator.iter_errors(instance))
```

**Markdown Code Block Extraction Pattern:**
```python
import re

# Matches ```json ... ``` or ``` ... ```
CODE_BLOCK_RE = re.compile(
    r'```(?:json)?\s*\n([\s\S]*?)\n```',
    re.MULTILINE
)

def extract_json_blocks(content: str) -> list[str]:
    """Extract all code blocks that might contain JSON."""
    blocks = CODE_BLOCK_RE.findall(content)
    # Also try the raw content
    return [content] + blocks
```

**Smart Validation Pattern:**
```python
def validate(self, content: str, schema: dict | None) -> str | dict:
    """Validate content against schema, extracting JSON if needed."""
    if schema is None:
        return content  # No validation, passthrough

    candidates = self._extract_json_candidates(content)

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            jsonschema.validate(data, schema)
            return data  # First valid match
        except (json.JSONDecodeError, jsonschema.ValidationError):
            continue

    # None matched - raise with details about last attempt
    raise ValidationError(...)
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Use exception hierarchy with `ValidationError`
- Include actionable suggestions in error messages
- Full type annotations required
- Structured logging for validation failures

---

## Dev Notes

### Key Implementation Decisions:

1. **Try Raw First:** LLM might return pure JSON without markdown. Try parsing directly before extraction.

2. **First Valid Wins:** When multiple JSON blocks exist, validate each and use first match.

3. **Draft 7:** Use JSON Schema Draft 7 as per architecture decision.

4. **Passthrough for No Schema:** When schema is None, return content unchanged as string.

5. **Detailed Error Messages:** Include field path and expected vs actual type in ValidationError.

### Project Structure Notes

- `src/adw/commands/validator.py` - SchemaValidator class
- Used by phase runner after LLM execution
- Depends on jsonschema library (add to dependencies)

### References

- [Source: _bmad-output/architecture.md#External Dependencies]
- [Source: _bmad-output/prd.md#FR23 (Schema Validation)]
- [Source: _bmad-output/epics/epic-2-command-resolution-templates.md#Story 2.4]

---

## Dependencies

**Depends On:**
- Story 2.1: Implement Three-Tier Command Resolution (to locate schema.json)

**Blocks:** None within Epic 2

**Note:** This story is in Wave 2 but only depends on 2.1 (not 2.2). It could theoretically start after 2.1 completes, even if 2.2 is still in progress.

---

## Dev Agent Record

### Context Reference
- Architecture: JSON Schema (draft-07) validation requirement
- Exception hierarchy: ValidationError with field_errors support
- Project context: Structured logging for validation failures

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- Code review performed: 2025-12-31
- All 24 unit tests passing
- Module coverage: 97%

### Completion Notes List
- SchemaValidator class implements all validation logic
- Uses jsonschema library with Draft7Validator for explicit compliance
- Smart extraction tries raw JSON first, then markdown code blocks
- ValidationError includes field-level error details with path and type info
- Passthrough mode returns content unchanged when no schema provided
- Structured logging added for validation events

### File List
| File | Action | Description |
|------|--------|-------------|
| `src/adw/commands/validator.py` | Created | SchemaValidator class with validation logic |
| `src/adw/commands/__init__.py` | Modified | Export SchemaValidator |
| `tests/unit/commands/test_validator.py` | Created | 24 unit tests for all ACs |
| `pyproject.toml` | Modified | Added jsonschema>=4.20.0 dependency |

### Change Log
| Date | Change | Reason |
|------|--------|--------|
| 2025-12-31 | Initial implementation | Story development |
| 2025-12-31 | Code review fixes | Address unreachable code, add logging, use Draft7Validator |

