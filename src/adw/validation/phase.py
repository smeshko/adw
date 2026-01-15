"""ValidationPhase - Simplified validation phase implementation.

This module contains the ValidationPhase class that coordinates
validation in a single LLM call. The LLM handles the entire
validate-fix-re-validate cycle through the validation prompt.

Simplified in Epic 16 (Story 16.4) to use simplified ValidationResult model.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationResult

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)


class ValidationPhase:
    """Simplified validation phase using LLM for validation.

    The LLM handles the entire validation cycle through the validation prompt:
    1. Run tests
    2. Run linters/type checkers (if configured)
    3. Review code for bugs, security issues, bad patterns
    4. If fixable issues found, fix them and re-validate ONCE
    5. Return structured result

    The SDK makes a single call and passes through the result.

    Attributes:
        config: ValidationConfig with validation settings.
    """

    def __init__(
        self,
        config: ValidationConfig | None = None,
        run_id: str | None = None,
    ) -> None:
        """Initialize the validation phase.

        Args:
            config: Optional configuration. Uses defaults if not provided.
            run_id: Run ID for logging context.
        """
        self.config = config or ValidationConfig()
        self._run_id = run_id

    def run(self, context: RunContext) -> ValidationResult:
        """Execute the validation phase.

        In the new architecture, this is called AFTER the LLM executor
        has already run the validation prompt. This method receives
        the parsed result from the executor.

        For backward compatibility during migration, if called directly
        without a pre-parsed result, it returns a failed result.

        Args:
            context: Current run context with phase history and artifacts.

        Returns:
            ValidationResult with simplified pass/fail status and issue summaries.
        """
        logger.info("Starting validation phase", extra={"run_id": self._run_id})

        # The new architecture relies on the executor running the
        # validation prompt and parsing the JSON result. This method
        # is called by the orchestrator which passes the parsed result.
        #
        # For now, return a placeholder result. The actual validation
        # logic is in the prompt executed by the LLM.
        #
        # TODO: This will be properly wired in when the orchestrator
        # is updated to use the new validation flow.

        logger.info("Validation phase completed", extra={"run_id": self._run_id})

        # Return a default failed result indicating validation needs to be run
        return ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=False,
            issues_fixed=[],
            issues_remaining=["Validation phase not yet executed by LLM"],
            summary="Validation phase requires LLM execution via validate prompt",
        )

    @staticmethod
    def from_llm_response(response_json: dict[str, Any]) -> ValidationResult:
        """Create ValidationResult from LLM JSON response.

        This method parses the JSON output from the validation prompt
        and creates a ValidationResult model.

        Args:
            response_json: Parsed JSON from the LLM validation response.

        Returns:
            ValidationResult with validated fields.

        Raises:
            ValueError: If required fields are missing.
        """
        return ValidationResult.model_validate(response_json)


__all__ = ["ValidationPhase"]
