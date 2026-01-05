"""Validation models for the unified validation phase.

This module contains Pydantic models for validation results and issues.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ValidationSource(str, Enum):
    """Source of a validation issue.

    Identifies which validator produced the issue:
    - TEST: From test execution (pytest, npm test, etc.)
    - REVIEW: From LLM code review
    - EVIDENCE: From evidence gathering comparison
    """

    TEST = "test"
    REVIEW = "review"
    EVIDENCE = "evidence"


class ValidationIssue(BaseModel):
    """A single issue found during validation.

    Represents a problem discovered by one of the validators,
    including its source, severity, and location if applicable.

    Attributes:
        source: Which validator found this issue.
        message: Human-readable description of the issue.
        severity: Issue severity (critical, high, medium, low, info).
        file_path: Path to the file containing the issue (if applicable).
        line_number: Line number in the file (if applicable).
        suggestion: Optional suggestion for fixing the issue.
    """

    source: ValidationSource = Field(..., description="Which validator found this issue")
    message: str = Field(..., description="Human-readable description of the issue")
    severity: str = Field(
        ..., description="Issue severity: critical, high, medium, low, info"
    )
    file_path: str | None = Field(
        default=None, description="Path to the file containing the issue"
    )
    line_number: int | None = Field(
        default=None, description="Line number in the file"
    )
    suggestion: str | None = Field(
        default=None, description="Suggestion for fixing the issue"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "source": "test",
                "message": "Test failed: test_login_validation",
                "severity": "high",
                "file_path": "tests/test_auth.py",
                "line_number": 42,
                "suggestion": "Check assertion on line 42",
            }
        },
    }


class ValidationResult(BaseModel):
    """Result of the unified validation phase.

    Aggregates results from all enabled validators (evidence, review, tests)
    into a single result with pass/fail status and collected issues.

    Attributes:
        passed: Whether all validators passed with no issues.
        issues: List of issues found by validators.
        iteration: Current iteration number in the validation loop.
    """

    passed: bool = Field(..., description="Whether validation passed")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="Issues found during validation"
    )
    iteration: int = Field(
        default=1, description="Current iteration number in validation loop"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "passed": False,
                "issues": [
                    {
                        "source": "test",
                        "message": "Test failed",
                        "severity": "high",
                    }
                ],
                "iteration": 1,
            }
        },
    }


__all__ = ["ValidationSource", "ValidationIssue", "ValidationResult"]
