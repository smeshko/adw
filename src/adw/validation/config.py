"""Configuration for the validation phase.

This module contains the ValidationConfig model that controls
which validators are enabled and their settings.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ValidationConfig(BaseModel):
    """Configuration for the unified validation phase.

    Controls which validators are enabled and their settings.
    All validators are enabled by default.

    Attributes:
        enable_evidence: Whether to run evidence validator.
        enable_review: Whether to run code review validator.
        enable_tests: Whether to run test validator.
        test_command: Custom test command (auto-detect if None).
        test_timeout_seconds: Timeout for test execution.
        review_prompt: Path to custom review prompt (optional).
        review_focus: Areas to focus code review on.
        max_iterations: Maximum validation loop iterations.
        max_fix_attempts_per_issue: Max attempts to fix a single issue.
        stall_threshold: Consecutive iterations without progress before stall.
        triage_mode: How to handle issue triage (auto, manual, hybrid).
        auto_dismiss_info: Automatically dismiss info-level issues.
    """

    enable_evidence: bool = Field(
        default=True, description="Whether to run evidence validator"
    )
    enable_review: bool = Field(
        default=True, description="Whether to run code review validator"
    )
    enable_tests: bool = Field(
        default=True, description="Whether to run test validator"
    )
    test_command: str | None = Field(
        default=None, description="Custom test command (auto-detect if None)"
    )
    test_timeout_seconds: int = Field(
        default=300, description="Timeout for test execution in seconds"
    )
    review_prompt: str | None = Field(
        default=None, description="Path to custom review prompt"
    )
    review_focus: list[str] = Field(
        default_factory=lambda: ["security", "error_handling", "edge_cases"],
        description="Areas to focus code review on",
    )
    max_iterations: int = Field(
        default=5, description="Maximum validation loop iterations"
    )
    max_fix_attempts_per_issue: int = Field(
        default=2, description="Max attempts to fix a single issue"
    )
    stall_threshold: int = Field(
        default=2, description="Consecutive iterations without progress before stall"
    )
    triage_mode: Literal["auto", "manual", "hybrid"] = Field(
        default="auto", description="How to handle issue triage"
    )
    auto_dismiss_info: bool = Field(
        default=True, description="Automatically dismiss info-level issues"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "enable_evidence": True,
                "enable_review": True,
                "enable_tests": True,
                "test_command": "pytest",
                "test_timeout_seconds": 300,
                "max_iterations": 5,
                "triage_mode": "auto",
            }
        },
    }


__all__ = ["ValidationConfig"]
