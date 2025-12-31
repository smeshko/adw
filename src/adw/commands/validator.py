"""Schema validation for LLM output.

This module provides JSON schema validation for LLM output, including
extraction of JSON from markdown code blocks.
"""

import json
import re

import jsonschema
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from adw.exceptions import ValidationError

# Regex to match JSON code blocks (```json ... ``` or ``` ... ```)
CODE_BLOCK_RE = re.compile(
    r"```(?:json)?\s*\n([\s\S]*?)\n```",
    re.MULTILINE,
)


class SchemaValidator:
    """Validates LLM output against JSON schemas.

    This class provides methods to:
    - Extract JSON from markdown code blocks
    - Validate JSON against Draft 7 schemas
    - Return parsed data or raise ValidationError with field details

    Example:
        >>> validator = SchemaValidator()
        >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        >>> result = validator.validate('{"name": "test"}', schema)
        >>> assert result == {"name": "test"}
    """

    def extract_json_from_markdown(self, content: str) -> list[str]:
        """Extract potential JSON strings from markdown content.

        Detects JSON code blocks (```json ... ```) and untagged code blocks
        that may contain JSON.

        Args:
            content: The markdown content to extract JSON from.

        Returns:
            List of potential JSON strings extracted from code blocks.
        """
        return CODE_BLOCK_RE.findall(content)

    def validate(
        self,
        content: str,
        schema: dict[str, object] | None,
    ) -> str | dict[str, object]:
        """Validate content against a JSON schema.

        When schema is None, returns the content as-is (passthrough mode).
        When schema is provided, attempts to parse and validate content as JSON.

        The validation process:
        1. If no schema, return raw content (passthrough)
        2. Try to parse content as raw JSON
        3. If that fails, extract JSON from markdown code blocks
        4. Validate against schema using Draft 7
        5. Return parsed dict on success

        Args:
            content: The content to validate (may be raw JSON or markdown).
            schema: JSON schema dict to validate against, or None for passthrough.

        Returns:
            The original content string if no schema, or parsed dict if valid JSON.

        Raises:
            ValidationError: If content cannot be parsed as JSON or fails schema
                validation.
        """
        # No-schema passthrough
        if schema is None:
            return content

        # Collect all JSON candidates
        candidates = self._extract_json_candidates(content)

        # Try each candidate against the schema
        last_json_error: str | None = None
        last_schema_error: str | None = None
        last_field_errors: list[dict[str, str]] = []

        for candidate in candidates:
            try:
                data: dict[str, object] = json.loads(candidate)
                # Validate against schema
                jsonschema.validate(instance=data, schema=schema)
                return data  # First valid match wins
            except json.JSONDecodeError as e:
                last_json_error = str(e)
                continue
            except JsonSchemaValidationError as e:
                last_schema_error = e.message
                last_field_errors = self._extract_field_errors(e)
                continue

        # None matched - raise with details about the failure
        if last_schema_error:
            raise ValidationError(
                code="SCHEMA_VALIDATION_FAILED",
                message=f"Schema validation failed: {last_schema_error}",
                field_errors=last_field_errors,
                suggestion="Check LLM output format matches schema requirements",
            )
        elif last_json_error:
            raise ValidationError(
                code="JSON_PARSE_ERROR",
                message=f"Failed to parse JSON: {last_json_error}",
                suggestion="Ensure output contains valid JSON",
            )
        else:
            raise ValidationError(
                code="NO_JSON_FOUND",
                message="No JSON content found in output",
                suggestion="Ensure LLM output contains JSON or a markdown code block",
            )

    def _extract_json_candidates(self, content: str) -> list[str]:
        """Extract all potential JSON strings from content.

        Tries the raw content first, then extracts from markdown code blocks.

        Args:
            content: The content to extract JSON from.

        Returns:
            List of potential JSON strings to try.
        """
        # Try raw content first (for pure JSON responses)
        candidates = [content.strip()]

        # Then try markdown extraction
        markdown_blocks = self.extract_json_from_markdown(content)
        candidates.extend(block.strip() for block in markdown_blocks)

        return candidates

    def _extract_field_errors(
        self,
        error: JsonSchemaValidationError,
    ) -> list[dict[str, str]]:
        """Extract field-level error details from a jsonschema ValidationError.

        Args:
            error: The jsonschema validation error.

        Returns:
            List of field error dicts with 'field' and 'error' keys.
        """
        if error.absolute_path:
            field_path = ".".join(str(p) for p in error.absolute_path)
        else:
            field_path = "root"

        errors = [
            {
                "field": field_path,
                "error": error.message,
            }
        ]

        # Include context about expected vs actual type if available
        if str(error.validator) == "type":
            expected = error.validator_value
            actual = type(error.instance).__name__
            errors[0]["error"] = f"Expected {expected}, got {actual}"

        return errors
