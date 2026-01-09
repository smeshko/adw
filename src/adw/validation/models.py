"""Validation models for the unified validation phase.

This module contains Pydantic models for validation results.
Simplified in Story 16.4 to match the unified validation prompt output schema.
"""

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of the unified validation phase.

    This simplified model captures the outcome of validation where the LLM
    handles the entire validate-fix-re-validate cycle internally.

    Attributes:
        passed: True if all tests pass and code review is clean.
        tests_passed: True if all tests passed.
        code_review_passed: True if code review found no issues.
        issues_fixed: One-line summaries of issues that were fixed.
        issues_remaining: One-line summaries of issues that couldn't be fixed.
        summary: Human-readable summary of validation results.
    """

    passed: bool = Field(..., description="True if all validation passed")
    tests_passed: bool = Field(..., description="True if all tests passed")
    code_review_passed: bool = Field(
        ..., description="True if code review found no issues"
    )
    issues_fixed: list[str] = Field(
        default_factory=list, description="One-line summaries of fixed issues"
    )
    issues_remaining: list[str] = Field(
        default_factory=list, description="One-line summaries of remaining issues"
    )
    summary: str = Field(default="", description="Human-readable validation summary")

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "passed": True,
                "tests_passed": True,
                "code_review_passed": True,
                "issues_fixed": ["Fixed missing null check in auth handler"],
                "issues_remaining": [],
                "summary": "All tests pass, code review clean",
            }
        },
    }


__all__ = [
    "ValidationResult",
]
