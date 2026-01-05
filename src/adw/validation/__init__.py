"""Unified validation phase for ADW pipeline.

This package provides the ValidationPhase which combines:
- Evidence gathering validation
- LLM code review
- Test suite execution

All validators run in sequence and issues are aggregated into
a single ValidationResult for triage and fix iteration.
"""

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    FixAttempt,
    FixResult,
    IssueContext,
    IssueLocation,
    IssueSeverity,
    IssueSource,
    ValidationIssue,
    ValidationResult,
    ValidationSource,
)
from adw.validation.phase import ValidationPhase
from adw.validation.state_manager import ValidationStateManager
from adw.validation.validators.base import Validator, ValidatorRegistry

__all__ = [
    "FixAttempt",
    "FixResult",
    "IssueContext",
    "IssueLocation",
    "IssueSeverity",
    "IssueSource",
    "ValidationConfig",
    "ValidationIssue",
    "ValidationPhase",
    "ValidationResult",
    "ValidationSource",
    "ValidationStateManager",
    "Validator",
    "ValidatorRegistry",
]
