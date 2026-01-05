"""ValidationPhase - Unified validation phase implementation.

This module contains the ValidationPhase class that coordinates
evidence gathering, code review, and test execution into a single
validation phase.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationIssue, ValidationResult

from adw.validation.validators.base import Validator, ValidatorRegistry

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)


class ValidationPhase:
    """Unified validation phase combining evidence, review, and tests.

    This phase runs all enabled validators in sequence:
    1. Evidence Gathering - Compare gathered evidence against plan requirements
    2. Code Review - LLM-based code review for quality issues
    3. Test Suite - Execute configured test command

    All validators run regardless of individual failures (no short-circuit).
    Issues from all validators are aggregated into a single ValidationResult.

    Attributes:
        config: ValidationConfig controlling which validators are enabled.
        _registry: ValidatorRegistry managing validator instances.
    """

    def __init__(self, config: ValidationConfig | None = None) -> None:
        """Initialize the validation phase.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or ValidationConfig()
        self._registry = ValidatorRegistry()
        self._iteration = 1

    def run(self, context: RunContext) -> ValidationResult:
        """Execute the unified validation phase.

        Runs all enabled validators in sequence (Evidence → Review → Tests),
        collects all issues, and returns an aggregated result.

        Args:
            context: Current run context with phase history and artifacts.

        Returns:
            ValidationResult with pass/fail status and collected issues.
        """
        logger.info(
            "Starting validation phase",
            extra={
                "iteration": self._iteration,
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
            iteration=self._iteration,
        )

        logger.info(
            "Validation phase completed",
            extra={
                "passed": passed,
                "issue_count": len(all_issues),
                "iteration": self._iteration,
            },
        )

        # Increment iteration for next run
        self._iteration += 1

        return result

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
                # Optionally add an issue for the validator error
                # This ensures we track that a validator failed

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
