"""Unified validation phase for ADW pipeline.

This package provides the ValidationPhase which combines:
- Evidence gathering validation
- LLM code review
- Test suite execution

All validators run in sequence and issues are aggregated into
a single ValidationResult for triage and fix iteration.
"""

from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationIssue, ValidationResult, ValidationSource
from adw.validation.phase import ValidationPhase, Validator

__all__ = [
    "ValidationConfig",
    "ValidationIssue",
    "ValidationPhase",
    "ValidationResult",
    "ValidationSource",
    "Validator",
]
