"""ValidationPhase - Unified validation phase implementation.

This module contains the ValidationPhase class that coordinates
evidence gathering, code review, and test execution into a single
validation phase.

State persistence is handled via ValidationStateManager for resume support.
Report generation via ValidationReportGenerator produces summary reports.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from adw.validation.config import ValidationConfig
from adw.validation.loop_controller import ExitReason, ValidationLoopController
from adw.validation.models import (
    LoopState,
    ValidationIssue,
    ValidationResult,
    ValidationSource,
    ValidationState,
)
from adw.validation.report import ValidationReport, ValidationReportGenerator
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
    """Unified validation phase combining evidence, review, and tests.

    This phase runs all enabled validators in sequence:
    1. Evidence Gathering - Compare gathered evidence against plan requirements
    2. Code Review - LLM-based code review for quality issues
    3. Test Suite - Execute configured test command

    All validators run regardless of individual failures (no short-circuit).
    Issues from all validators are aggregated into a single ValidationResult.

    State is persisted after each iteration for resume capability.

    Attributes:
        config: ValidationConfig controlling which validators are enabled.
        _registry: ValidatorRegistry managing validator instances.
        _state_manager: Optional state manager for persistence.
        _state: Current validation state (if state manager is set).
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
        self._iteration = 1
        self._state_manager: ValidationStateManager | None = None
        self._state: ValidationState | None = None
        self._loop_controller = ValidationLoopController(self.config)
        self._report_generator: ValidationReportGenerator | None = None
        self._start_time: datetime = datetime.now(UTC)
        self._last_report: ValidationReport | None = None

        # Initialize state manager and report generator if run_id is provided
        if run_id and runs_dir:
            base_path = runs_dir / run_id
            self._state_manager = ValidationStateManager(run_id, base_path)
            self._report_generator = ValidationReportGenerator(
                self._state_manager, self.config
            )
            self._check_resume()

    def _check_resume(self) -> None:
        """Check for resumable state at phase start.

        If state can be resumed, loads the saved state and sets iteration.
        """
        if self._state_manager and self._state_manager.can_resume():
            logger.info("Resumable validation state found, loading...")
            self._state = self._state_manager.resume()
            self._iteration = self._state.current_iteration
            logger.info(
                "Resumed validation from saved state",
                extra={
                    "iteration": self._iteration,
                    "issues_remaining": self._state.loop_state.issues_remaining,
                },
            )

    def _save_state(self, issues: list[ValidationIssue]) -> None:
        """Save state after each iteration.

        Args:
            issues: Current list of issues to persist.
        """
        if not self._state_manager:
            return

        if self._state:
            # Preserve existing loop_state counters, update issues_remaining
            existing_loop = self._state.loop_state
            loop_state = LoopState(
                issues_resolved=existing_loop.issues_resolved,
                issues_dismissed=existing_loop.issues_dismissed,
                issues_deferred=existing_loop.issues_deferred,
                issues_remaining=len(issues),
                stall_count=existing_loop.stall_count,
            )
            # Update existing state
            self._state = ValidationState(
                run_id=self._state.run_id,
                current_iteration=self._iteration,
                total_iterations=self._state.total_iterations,
                loop_state=loop_state,
                started_at=self._state.started_at,
            )
        else:
            # Create new state with fresh loop_state
            loop_state = LoopState(
                issues_remaining=len(issues),
            )
            self._state = ValidationState(
                run_id=self._state_manager.run_id,
                current_iteration=self._iteration,
                total_iterations=self.config.max_iterations,
                loop_state=loop_state,
            )

        # Save state and issues
        self._state_manager.save_state(self._state)
        self._state_manager.save_issues(issues)

        logger.debug(
            "Validation state saved",
            extra={"iteration": self._iteration, "issue_count": len(issues)},
        )

    def _clear_state(self) -> None:
        """Clear state on successful completion."""
        if self._state_manager:
            self._state_manager.clear()
            self._state = None
            logger.info("Validation state cleared on successful completion")

    def run(self, context: RunContext) -> ValidationResult:
        """Execute the unified validation phase.

        Runs all enabled validators in sequence (Evidence → Review → Tests),
        collects all issues, and returns an aggregated result.

        Uses ValidationLoopController for iteration tracking and updates
        issue counts for exit condition evaluation.

        State is saved after each iteration for resume capability.
        State is cleared on successful completion (no issues).

        Args:
            context: Current run context with phase history and artifacts.

        Returns:
            ValidationResult with pass/fail status and collected issues.
        """
        # Use loop controller to track iterations
        iteration = self._loop_controller.start_iteration()
        self._iteration = iteration  # Keep in sync for backward compatibility

        logger.info(
            "Starting validation phase",
            extra={
                "iteration": iteration,
                "max_iterations": self.config.max_iterations,
                "evidence_enabled": self.config.enable_evidence,
                "review_enabled": self.config.enable_review,
                "tests_enabled": self.config.enable_tests,
            },
        )

        # Run all validators and collect issues
        all_issues = self._run_validators(context)

        # Update loop controller counts from issues
        self._loop_controller.update_counts(all_issues)

        # Determine pass/fail based on issues
        passed = len(all_issues) == 0

        result = ValidationResult(
            passed=passed,
            issues=all_issues,
            iteration=iteration,
        )

        # Save state after each iteration
        self._save_state(all_issues)

        logger.info(
            "Validation phase completed",
            extra={
                "passed": passed,
                "issue_count": len(all_issues),
                "iteration": iteration,
                "issues_remaining": self._loop_controller.state.issues_remaining,
            },
        )

        # Clear state on successful completion
        if passed:
            self._clear_state()

        return result

    @property
    def state_manager(self) -> ValidationStateManager | None:
        """Get the state manager (for testing/integration)."""
        return self._state_manager

    @property
    def loop_controller(self) -> ValidationLoopController:
        """Get the loop controller for exit condition checking.

        The loop controller provides:
        - Iteration tracking
        - Exit condition evaluation (max iterations, stall, all resolved)
        - Progress detection
        - Auto-defer functionality

        Returns:
            ValidationLoopController instance managing loop state.
        """
        return self._loop_controller

    def get_summary(self) -> dict:
        """Get summary of loop execution from the controller.

        Returns:
            Dictionary with iteration stats, issue counts, and stall info.
        """
        return self._loop_controller.get_summary()

    @property
    def last_report(self) -> ValidationReport | None:
        """Get the most recent validation report.

        Returns:
            ValidationReport if generated, None otherwise.
        """
        return self._last_report

    def generate_report(
        self,
        issues: list[ValidationIssue],
        exit_reason: ExitReason | str | None = None,
    ) -> ValidationReport | None:
        """Generate validation report from loop results.

        Creates a ValidationReport with all metrics and deferred issues,
        and saves both markdown and JSON versions to artifacts.

        Args:
            issues: All validation issues from the loop.
            exit_reason: Why the loop exited. If None, will be inferred.

        Returns:
            ValidationReport if generator is available, None otherwise.
        """
        if not self._report_generator:
            logger.warning("No report generator available (run_id not set)")
            return None

        loop_summary = self._loop_controller.get_summary()

        # Add exit reason to summary if provided
        if exit_reason:
            if isinstance(exit_reason, ExitReason):
                loop_summary["exit_reason"] = exit_reason.value
            else:
                loop_summary["exit_reason"] = exit_reason
        elif "exit_reason" not in loop_summary:
            loop_summary["exit_reason"] = "COMPLETED"

        report = self._report_generator.generate(
            loop_summary, issues, self._start_time
        )

        # Save the report to artifacts
        report_path = self._report_generator.save(report)
        logger.info("Validation report saved", extra={"path": str(report_path)})

        self._last_report = report
        return report

    def get_pr_section(self) -> str:
        """Get PR description section for known issues.

        Returns:
            Markdown string for PR description, or empty if no report.
        """
        if self._last_report:
            return self._last_report.to_pr_section()
        return ""

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
                # and the error is surfaced for triage
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
