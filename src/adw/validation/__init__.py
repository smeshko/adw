"""Unified validation phase for ADW pipeline.

This package provides the ValidationPhase which combines:
- Evidence gathering validation
- LLM code review
- Test suite execution

All validators run in sequence and issues are aggregated into
a single ValidationResult for triage and fix iteration.
"""

from adw.validation.config import ValidationConfig
from adw.validation.fix_engine import FileChange, FixEngine, FixIterationResult
from adw.validation.loop_controller import (
    ExitReason,
    ValidationLoopController,
)
from adw.validation.models import (
    FixAttempt,
    FixResult,
    IssueContext,
    IssueLocation,
    IssueSeverity,
    IssueSource,
    LoopState,
    TriageDecision,
    TriagedIssue,
    ValidationIssue,
    ValidationResult,
    ValidationSource,
    ValidationState,
)
from adw.validation.phase import ValidationPhase
from adw.validation.state_manager import ValidationStateManager
from adw.validation.triage import TriageSystem
from adw.validation.validators.base import Validator, ValidatorRegistry

__all__ = [
    "ExitReason",
    "FileChange",
    "FixAttempt",
    "FixEngine",
    "FixIterationResult",
    "FixResult",
    "IssueContext",
    "IssueLocation",
    "IssueSeverity",
    "IssueSource",
    "LoopState",
    "TriageDecision",
    "TriagedIssue",
    "TriageSystem",
    "ValidationConfig",
    "ValidationIssue",
    "ValidationLoopController",
    "ValidationPhase",
    "ValidationResult",
    "ValidationSource",
    "ValidationState",
    "ValidationStateManager",
    "Validator",
    "ValidatorRegistry",
]
