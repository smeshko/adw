"""Unit tests for SchemaValidator.

Tests cover:
- Valid JSON against matching schema
- Invalid JSON against schema (field errors)
- JSON extraction from markdown code blocks
- Multiple JSON blocks (first valid wins)
- No-schema passthrough
- Malformed JSON handling
"""

import pytest

from adw.commands.validator import SchemaValidator
from adw.exceptions import ValidationError


@pytest.fixture
def validator() -> SchemaValidator:
    """Create a SchemaValidator instance for testing."""
    return SchemaValidator()


class TestValidJSONValidation:
    """Tests for valid JSON passing schema validation."""

    def test_valid_json_passes_schema(self, validator: SchemaValidator) -> None:
        """Valid JSON matching schema should return parsed dict."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        content = '{"name": "test"}'
        result = validator.validate(content, schema)
        assert result == {"name": "test"}

    def test_valid_json_with_multiple_properties(
        self, validator: SchemaValidator
    ) -> None:
        """Valid JSON with multiple properties should validate correctly."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            },
        }
        content = '{"name": "Alice", "age": 30, "active": true}'
        result = validator.validate(content, schema)
        assert result == {"name": "Alice", "age": 30, "active": True}

    def test_valid_json_with_required_fields(
        self, validator: SchemaValidator
    ) -> None:
        """Valid JSON with required fields should validate correctly."""
        schema = {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        }
        content = '{"id": 123, "name": "Test"}'
        result = validator.validate(content, schema)
        assert result == {"id": 123, "name": "Test"}


class TestInvalidJSONValidation:
    """Tests for invalid JSON failing schema validation."""

    def test_invalid_json_raises_validation_error(
        self, validator: SchemaValidator
    ) -> None:
        """Invalid JSON should raise ValidationError with field details."""
        schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
        content = '{"age": "not a number"}'
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert exc.value.code == "SCHEMA_VALIDATION_FAILED"
        # Field should be mentioned in error details
        assert len(exc.value.field_errors) > 0
        assert exc.value.field_errors[0]["field"] == "age"

    def test_missing_required_field_raises_validation_error(
        self, validator: SchemaValidator
    ) -> None:
        """Missing required field should raise ValidationError."""
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        content = '{"other": "value"}'
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert exc.value.code == "SCHEMA_VALIDATION_FAILED"
        assert "name" in exc.value.message.lower() or "required" in exc.value.message.lower()

    def test_wrong_type_shows_expected_vs_actual(
        self, validator: SchemaValidator
    ) -> None:
        """Type mismatch should show expected vs actual type."""
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        content = '{"count": "five"}'
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert exc.value.code == "SCHEMA_VALIDATION_FAILED"
        # Check field error contains type information
        assert len(exc.value.field_errors) > 0
        error_info = exc.value.field_errors[0]["error"]
        assert "integer" in error_info.lower() or "str" in error_info.lower()


class TestMarkdownExtraction:
    """Tests for JSON extraction from markdown code blocks."""

    def test_extracts_json_from_markdown_code_block(
        self, validator: SchemaValidator
    ) -> None:
        """JSON in markdown code block should be extracted and validated."""
        content = '''
Here is the result:
```json
{"result": "value"}
```
        '''
        result = validator.validate(content, {"type": "object"})
        assert result == {"result": "value"}

    def test_extracts_from_untagged_code_block(
        self, validator: SchemaValidator
    ) -> None:
        """JSON in untagged code block should be extracted."""
        content = '''
```
{"result": "value"}
```
        '''
        result = validator.validate(content, {"type": "object"})
        assert result == {"result": "value"}

    def test_extracts_json_with_surrounding_text(
        self, validator: SchemaValidator
    ) -> None:
        """JSON should be extracted even with surrounding markdown text."""
        content = '''
# Response

Here is my analysis:

```json
{"analysis": "complete", "score": 95}
```

Thank you for your patience.
        '''
        schema = {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "score": {"type": "integer"},
            },
        }
        result = validator.validate(content, schema)
        assert result == {"analysis": "complete", "score": 95}

    def test_extract_json_from_markdown_method(
        self, validator: SchemaValidator
    ) -> None:
        """extract_json_from_markdown should return list of code blocks."""
        content = '''
```json
{"first": 1}
```
Some text
```
{"second": 2}
```
        '''
        blocks = validator.extract_json_from_markdown(content)
        assert len(blocks) == 2
        assert '{"first": 1}' in blocks
        assert '{"second": 2}' in blocks


class TestMultipleBlocks:
    """Tests for handling multiple JSON blocks."""

    def test_first_valid_json_block_used(self, validator: SchemaValidator) -> None:
        """First JSON block matching schema should be used."""
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
            "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
        }
        result = validator.validate(content, schema)
        assert result == {"name": "correct", "count": 5}

    def test_skips_invalid_blocks_uses_valid(
        self, validator: SchemaValidator
    ) -> None:
        """Invalid blocks should be skipped, valid one used."""
        content = '''
```json
not valid json at all
```
```json
{"valid": true}
```
        '''
        schema = {"type": "object", "properties": {"valid": {"type": "boolean"}}}
        result = validator.validate(content, schema)
        assert result == {"valid": True}

    def test_all_blocks_invalid_raises_error(
        self, validator: SchemaValidator
    ) -> None:
        """If no block matches schema, should raise ValidationError."""
        content = '''
```json
{"wrong": "type"}
```
```json
{"also": "wrong"}
```
        '''
        schema = {
            "type": "object",
            "required": ["required_field"],
            "properties": {"required_field": {"type": "integer"}},
        }
        with pytest.raises(ValidationError):
            validator.validate(content, schema)


class TestNoSchemaPassthrough:
    """Tests for no-schema passthrough mode."""

    def test_no_schema_returns_raw_content(
        self, validator: SchemaValidator
    ) -> None:
        """When schema is None, raw content should be returned."""
        content = "This is just text, not JSON"
        result = validator.validate(content, schema=None)
        assert result == content

    def test_no_schema_returns_json_string_unchanged(
        self, validator: SchemaValidator
    ) -> None:
        """Even JSON content should be returned as string when no schema."""
        content = '{"key": "value"}'
        result = validator.validate(content, schema=None)
        assert result == '{"key": "value"}'
        assert isinstance(result, str)

    def test_no_schema_with_markdown_returns_unchanged(
        self, validator: SchemaValidator
    ) -> None:
        """Markdown content should be returned unchanged when no schema."""
        content = '''
# Title
```json
{"data": 123}
```
        '''
        result = validator.validate(content, schema=None)
        assert result == content


class TestMalformedJSON:
    """Tests for handling malformed JSON."""

    def test_malformed_json_raises_validation_error(
        self, validator: SchemaValidator
    ) -> None:
        """Malformed JSON should raise ValidationError with parse message."""
        content = '{"unclosed": '
        schema = {"type": "object"}
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert "parse" in exc.value.message.lower() or "json" in exc.value.message.lower()

    def test_empty_content_raises_no_json_found(
        self, validator: SchemaValidator
    ) -> None:
        """Empty content should raise NO_JSON_FOUND ValidationError."""
        content = ""
        schema = {"type": "object"}
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert exc.value.code == "NO_JSON_FOUND"
        assert "No JSON content found" in exc.value.message

    def test_whitespace_only_raises_no_json_found(
        self, validator: SchemaValidator
    ) -> None:
        """Whitespace-only content should raise NO_JSON_FOUND ValidationError."""
        content = "   \n\t  "
        schema = {"type": "object"}
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert exc.value.code == "NO_JSON_FOUND"
        assert "No JSON content found" in exc.value.message

    def test_partial_json_in_markdown_raises_error(
        self, validator: SchemaValidator
    ) -> None:
        """Partial JSON in code block should raise ValidationError."""
        content = '''
```json
{"incomplete":
```
        '''
        schema = {"type": "object"}
        with pytest.raises(ValidationError):
            validator.validate(content, schema)


class TestRawContentFirst:
    """Tests for trying raw content before markdown extraction."""

    def test_raw_json_used_when_valid(self, validator: SchemaValidator) -> None:
        """Pure JSON response should be parsed directly."""
        content = '{"direct": "json"}'
        schema = {"type": "object", "properties": {"direct": {"type": "string"}}}
        result = validator.validate(content, schema)
        assert result == {"direct": "json"}

    def test_raw_json_preferred_over_markdown(
        self, validator: SchemaValidator
    ) -> None:
        """Raw JSON matching schema should be preferred even if content has markdown."""
        # This is a special case where the entire content is valid JSON
        content = '{"valid": true}'
        schema = {"type": "object", "properties": {"valid": {"type": "boolean"}}}
        result = validator.validate(content, schema)
        assert result == {"valid": True}


class TestErrorDetails:
    """Tests for error message details."""

    def test_validation_error_has_suggestion(
        self, validator: SchemaValidator
    ) -> None:
        """ValidationError should include helpful suggestion."""
        schema = {"type": "object", "required": ["name"]}
        content = '{"other": "field"}'
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert exc.value.suggestion is not None
        assert len(exc.value.suggestion) > 0

    def test_field_error_includes_path(self, validator: SchemaValidator) -> None:
        """Field errors should include the field path."""
        schema = {
            "type": "object",
            "properties": {"nested": {"type": "object", "properties": {"value": {"type": "integer"}}}},
        }
        content = '{"nested": {"value": "not an int"}}'
        with pytest.raises(ValidationError) as exc:
            validator.validate(content, schema)
        assert len(exc.value.field_errors) > 0
        # Should have field path
        field_path = exc.value.field_errors[0]["field"]
        assert "nested" in field_path or "value" in field_path
