"""Unified validation phase for ADW pipeline.

This package provides the ValidationPhase which coordinates
validation in a single LLM call. The LLM handles the entire
validate-fix-re-validate cycle internally, returning a simplified result.

Simplified in Epic 16 to remove SDK-side iteration logic.
"""

from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationResult
from adw.validation.phase import ValidationPhase

__all__ = [
    "ValidationConfig",
    "ValidationPhase",
    "ValidationResult",
]
