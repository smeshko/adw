"""ValidationPhase - Simplified validation phase implementation.

This module contains the ValidationPhase class that coordinates
evidence gathering, code review, and test execution into a single
validation phase. The LLM handles any iteration through prompts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSource,
)
from adw.validation.state_manager import ValidationStateManager
from adw.validation.validators.base import Validator, ValidatorRegistry

# Mapping from validator names to ValidationSource
_VALIDATOR_SOURCE_MAP: dict[str, ValidationSource] = {
    "test": ValidationSource.TEST,
    "review": ValidationSource.REVIEW,
    "evidence": ValidationSource.EVIDENCE,
}

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)


class ValidationPhase:
    """Simplified validation phase combining evidence, review, and tests.

    This phase runs all enabled validators in sequence:
    1. Evidence Gathering - Compare gathered evidence against plan requirements
    2. Code Review - LLM-based code review for quality issues
    3. Test Suite - Execute configured test command

    All validators run regardless of individual failures (no short-circuit).
    Issues from all validators are aggregated into a single ValidationResult.

    The LLM handles any iteration logic through the validation prompt.
    The SDK makes a single call and passes through the result.

    Attributes:
        config: ValidationConfig controlling which validators are enabled.
        _registry: ValidatorRegistry managing validator instances.
        _state_manager: Optional state manager for persistence.
    """

    def __init__(
        self,
        config: ValidationConfig | None = None,
        run_id: str | None = None,
        runs_dir: Path | None = None,
    ) -> None:
        """Initialize the validation phase.

        Args:
            config: Optional configuration. Uses defaults if not provided.
            run_id: Run ID for state persistence. If None, state is not persisted.
            runs_dir: Path to .adw/runs directory. Required if run_id is provided.
        """
        self.config = config or ValidationConfig()
        self._registry = ValidatorRegistry()
        self._state_manager: ValidationStateManager | None = None

        # Initialize state manager if run_id is provided
        if run_id and runs_dir:
            base_path = runs_dir / run_id
            self._state_manager = ValidationStateManager(run_id, base_path)

    def run(self, context: RunContext) -> ValidationResult:
        """Execute the validation phase.

        Runs all enabled validators in sequence (Evidence → Review → Tests),
        collects all issues, and returns an aggregated result.

        The LLM handles any iteration through the validation prompt.
        This method makes a single pass and returns the result.

        Args:
            context: Current run context with phase history and artifacts.

        Returns:
            ValidationResult with pass/fail status and collected issues.
        """
        logger.info(
            "Starting validation phase",
            extra={
                "evidence_enabled": self.config.enable_evidence,
                "review_enabled": self.config.enable_review,
                "tests_enabled": self.config.enable_tests,
            },
        )

        # Run all validators and collect issues
        all_issues = self._run_validators(context)

        # Determine pass/fail based on issues
        passed = len(all_issues) == 0

        result = ValidationResult(
            passed=passed,
            issues=all_issues,
        )

        # Save issues if state manager is available
        if self._state_manager:
            self._state_manager.save_issues(all_issues)

        logger.info(
            "Validation phase completed",
            extra={
                "passed": passed,
                "issue_count": len(all_issues),
            },
        )

        # Clear state on successful completion
        if passed and self._state_manager:
            self._state_manager.clear()

        return result

    @property
    def state_manager(self) -> ValidationStateManager | None:
        """Get the state manager (for testing/integration)."""
        return self._state_manager

    def _run_validators(self, context: RunContext) -> list[ValidationIssue]:
        """Run all enabled validators and collect issues.

        Validators run in order: Evidence → Review → Tests.
        All validators run regardless of individual failures.

        Args:
            context: Current run context.

        Returns:
            Aggregated list of issues from all validators.
        """
        all_issues: list[ValidationIssue] = []
        enabled_validators = self._get_enabled_validators()

        for validator in enabled_validators:
            try:
                logger.debug(f"Running validator: {validator.name}")
                issues = validator.validate(context)
                all_issues.extend(issues)
                logger.debug(
                    f"Validator {validator.name} found {len(issues)} issues"
                )
            except Exception as e:
                # Log error but continue to next validator
                logger.warning(
                    f"Validator {validator.name} failed with error: {e}",
                    exc_info=True,
                )
                # Create an issue for the validator error so the phase fails
                # and the error is surfaced
                source = _VALIDATOR_SOURCE_MAP.get(
                    validator.name, ValidationSource.TEST
                )
                all_issues.append(
                    ValidationIssue(
                        source=source,
                        message=f"Validator '{validator.name}' crashed: {e}",
                        severity="critical",
                    )
                )

        return all_issues

    def _get_enabled_validators(self) -> list[Validator]:
        """Get list of validators that are enabled in config.

        Returns:
            List of enabled validator instances.
        """
        return self._registry.get_enabled(self.config)

    def register_validator(self, validator: Validator) -> None:
        """Register a validator to be run during validation.

        Args:
            validator: Validator instance implementing the Validator protocol.
        """
        self._registry.register(validator)


__all__ = ["ValidationPhase"]
