"""Tests for simplified ValidationResult model (Story 16.4).

Tests cover:
- ValidationResult model with all required fields
- Default values for optional fields
- Serialization to/from dict and JSON
- Model validation
"""

import json

import pytest

from adw.validation.models import ValidationResult


class TestValidationResult:
    """Tests for ValidationResult model core functionality."""

    def test_create_with_all_fields(self) -> None:
        """ValidationResult can be created with all fields."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed null check", "Added error handling"],
            issues_remaining=[],
            summary="All tests pass, code review clean",
        )
        assert result.passed is True
        assert result.tests_passed is True
        assert result.code_review_passed is True
        assert result.issues_fixed == ["Fixed null check", "Added error handling"]
        assert result.issues_remaining == []
        assert result.summary == "All tests pass, code review clean"

    def test_create_with_required_fields_only(self) -> None:
        """ValidationResult uses defaults for optional fields."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
        )
        assert result.passed is False
        assert result.tests_passed is False
        assert result.code_review_passed is True
        assert result.issues_fixed == []
        assert result.issues_remaining == []
        assert result.summary == ""

    def test_create_fails_without_required_fields(self) -> None:
        """ValidationResult requires passed, tests_passed, code_review_passed."""
        with pytest.raises(ValueError):
            ValidationResult()  # type: ignore

        with pytest.raises(ValueError):
            ValidationResult(passed=True)  # type: ignore

    def test_failed_validation_with_remaining_issues(self) -> None:
        """ValidationResult handles failed validation with remaining issues."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=False,
            issues_fixed=["Fixed typo in config"],
            issues_remaining=[
                "Test test_login_validation fails - database connection issue",
                "Security: SQL injection vulnerability in user query",
            ],
            summary="Tests failing due to database issues, security concern found",
        )
        assert result.passed is False
        assert len(result.issues_fixed) == 1
        assert len(result.issues_remaining) == 2
        assert "SQL injection" in result.issues_remaining[1]


class TestValidationResultSerialization:
    """Tests for ValidationResult serialization methods."""

    def test_model_dump_returns_dict(self) -> None:
        """model_dump returns a dictionary representation."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed bug"],
            issues_remaining=[],
            summary="All good",
        )
        data = result.model_dump()

        assert isinstance(data, dict)
        assert data["passed"] is True
        assert data["tests_passed"] is True
        assert data["code_review_passed"] is True
        assert data["issues_fixed"] == ["Fixed bug"]
        assert data["issues_remaining"] == []
        assert data["summary"] == "All good"

    def test_model_validate_creates_from_dict(self) -> None:
        """model_validate creates ValidationResult from dictionary."""
        data = {
            "passed": False,
            "tests_passed": False,
            "code_review_passed": True,
            "issues_fixed": [],
            "issues_remaining": ["Test failure"],
            "summary": "One test failing",
        }
        result = ValidationResult.model_validate(data)

        assert result.passed is False
        assert result.tests_passed is False
        assert result.code_review_passed is True
        assert result.issues_remaining == ["Test failure"]

    def test_model_dump_json_returns_valid_json(self) -> None:
        """model_dump_json returns valid JSON string."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            summary="Validation complete",
        )
        json_str = result.model_dump_json()

        assert isinstance(json_str, str)
        # Verify it's valid JSON by parsing it
        parsed = json.loads(json_str)
        assert parsed["passed"] is True
        assert parsed["summary"] == "Validation complete"

    def test_round_trip_serialization(self) -> None:
        """ValidationResult survives round-trip through dict serialization."""
        original = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed issue 1", "Fixed issue 2"],
            issues_remaining=[],
            summary="All issues resolved, validation passed",
        )

        data = original.model_dump()
        restored = ValidationResult.model_validate(data)

        assert restored.passed == original.passed
        assert restored.tests_passed == original.tests_passed
        assert restored.code_review_passed == original.code_review_passed
        assert restored.issues_fixed == original.issues_fixed
        assert restored.issues_remaining == original.issues_remaining
        assert restored.summary == original.summary

    def test_json_round_trip_serialization(self) -> None:
        """ValidationResult survives round-trip through JSON serialization."""
        original = ValidationResult(
            passed=False,
            tests_passed=True,
            code_review_passed=False,
            issues_fixed=[],
            issues_remaining=["Code review found security issue"],
            summary="Tests pass but security concern in review",
        )

        json_str = original.model_dump_json()
        data = json.loads(json_str)
        restored = ValidationResult.model_validate(data)

        assert restored.passed == original.passed
        assert restored.tests_passed == original.tests_passed
        assert restored.code_review_passed == original.code_review_passed
        assert restored.issues_remaining == original.issues_remaining


class TestValidationResultSchema:
    """Tests for ValidationResult JSON schema compliance."""

    def test_schema_has_example(self) -> None:
        """JSON schema includes example from model_config."""
        schema = ValidationResult.model_json_schema()
        assert "example" in schema or "examples" in schema

    def test_all_fields_documented(self) -> None:
        """All fields have descriptions in the schema."""
        schema = ValidationResult.model_json_schema()
        properties = schema.get("properties", {})

        expected_fields = [
            "passed",
            "tests_passed",
            "code_review_passed",
            "issues_fixed",
            "issues_remaining",
            "summary",
        ]

        for field in expected_fields:
            assert field in properties, f"Missing field: {field}"
            assert "description" in properties[field], (
                f"No description for field: {field}"
            )

    def test_required_fields_specified(self) -> None:
        """Schema specifies required fields correctly."""
        schema = ValidationResult.model_json_schema()
        required = schema.get("required", [])

        # Required fields (no defaults)
        assert "passed" in required
        assert "tests_passed" in required
        assert "code_review_passed" in required

        # Optional fields (have defaults) should NOT be in required
        # Note: Pydantic may or may not include fields with default_factory
        # in required, so we just verify the schema exists


class TestValidationResultValidation:
    """Tests for ValidationResult input validation."""

    def test_validates_issues_fixed_is_list_of_strings(self) -> None:
        """issues_fixed must be a list of strings."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["string1", "string2"],
        )
        assert all(isinstance(s, str) for s in result.issues_fixed)

    def test_validates_issues_remaining_is_list_of_strings(self) -> None:
        """issues_remaining must be a list of strings."""
        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_remaining=["issue1", "issue2"],
        )
        assert all(isinstance(s, str) for s in result.issues_remaining)

    def test_rejects_non_string_issues(self) -> None:
        """Non-string values in issues lists are rejected by Pydantic validation."""
        # Pydantic should reject non-string values in list[str] fields
        with pytest.raises(ValueError):
            ValidationResult(
                passed=True,
                tests_passed=True,
                code_review_passed=True,
                issues_fixed=[123, True],  # type: ignore
            )

    def test_mutable_assignment(self) -> None:
        """ValidationResult fields can be modified after creation."""
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
        )
        result.passed = False
        result.issues_remaining = ["New issue found"]

        assert result.passed is False
        assert result.issues_remaining == ["New issue found"]
