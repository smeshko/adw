"""Unified validation phase for ADW pipeline.

This package provides the ValidationPhase which combines:
- Evidence gathering validation
- LLM code review
- Test suite execution

All validators run in sequence and issues are aggregated into
a single ValidationResult. The LLM handles any iteration through prompts.
"""

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    FixAttempt,
    FixResult,
    IssueContext,
    IssueLocation,
    IssueSeverity,
    IssueSource,
    LoopState,
    ValidationIssue,
    ValidationResult,
    ValidationSource,
    ValidationState,
)
from adw.validation.phase import ValidationPhase
from adw.validation.report import (
    ConfidenceLevel,
    DeferredIssueSummary,
    ValidationReport,
    ValidationReportGenerator,
)
from adw.validation.state_manager import ValidationStateManager
from adw.validation.validators.base import Validator, ValidatorRegistry

__all__ = [
    "ConfidenceLevel",
    "DeferredIssueSummary",
    "FixAttempt",
    "FixResult",
    "IssueContext",
    "IssueLocation",
    "IssueSeverity",
    "IssueSource",
    "LoopState",
    "ValidationConfig",
    "ValidationIssue",
    "ValidationPhase",
    "ValidationReport",
    "ValidationReportGenerator",
    "ValidationResult",
    "ValidationSource",
    "ValidationState",
    "ValidationStateManager",
    "Validator",
    "ValidatorRegistry",
]
