"""Issue triage system for the validation loop.

This module provides the TriageSystem class that categorizes
validation issues into FIX, DISMISS, or DEFER decisions.

Supports three triage modes:
- auto: LLM makes all decisions based on severity/context
- manual: User prompted for each issue interactively
- hybrid: Auto for low severity, manual for errors
"""

from typing import TYPE_CHECKING, Any, Literal

from rich.console import Console

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    IssueSeverity,
    TriageDecision,
    TriagedIssue,
    ValidationIssue,
)

if TYPE_CHECKING:
    from adw.executors.base import LLMExecutor


class TriageSystem:
    """System for triaging validation issues.

    Categorizes issues into FIX, DISMISS, or DEFER decisions based on
    the configured triage mode.

    Attributes:
        config: Validation configuration with triage settings.
        llm_executor: Optional LLM executor for auto triage mode.
        console: Rich console for user interaction.
    """

    def __init__(
        self,
        config: ValidationConfig,
        llm_executor: "LLMExecutor | None" = None,
        console: Console | None = None,
    ) -> None:
        """Initialize the triage system.

        Args:
            config: Validation configuration with triage settings.
            llm_executor: Optional LLM executor for auto triage decisions.
            console: Optional Rich console for user interaction.
        """
        self.config = config
        self.llm_executor = llm_executor
        self.console = console or Console()

    def triage(
        self,
        issues: list[ValidationIssue],
        mode: Literal["auto", "manual", "hybrid"] | None = None,
    ) -> list[TriagedIssue]:
        """Triage all issues according to the specified mode.

        Args:
            issues: List of validation issues to triage.
            mode: Triage mode override. If None, uses config.triage_mode.

        Returns:
            List of TriagedIssue with decisions for each issue.
        """
        if not issues:
            return []

        mode = mode or self.config.triage_mode

        if mode == "auto":
            return self._auto_triage_all(issues)
        elif mode == "manual":
            return self._manual_triage_all(issues)
        else:  # hybrid
            return self._hybrid_triage_all(issues)

    def _auto_triage_all(
        self,
        issues: list[ValidationIssue],
    ) -> list[TriagedIssue]:
        """Use rules and LLM to triage all issues automatically.

        Args:
            issues: List of issues to triage.

        Returns:
            List of triaged issues with auto-made decisions.
        """
        results: list[TriagedIssue] = []

        for issue in issues:
            # Auto-dismiss INFO severity if configured
            if (
                self.config.auto_dismiss_info
                and issue.severity == IssueSeverity.INFO
            ):
                results.append(
                    TriagedIssue(
                        issue=issue,
                        decision=TriageDecision.DISMISS,
                        reason="Auto-dismissed INFO severity",
                        auto_decided=True,
                    )
                )
                continue

            # TODO: Check triage rules (Task 6)
            # TODO: LLM triage (Task 3)

            # Default to FIX for now (will be replaced with LLM in Task 3)
            results.append(
                TriagedIssue(
                    issue=issue,
                    decision=TriageDecision.FIX,
                    reason="Default: issue requires fix",
                    auto_decided=True,
                )
            )

        return results

    def _manual_triage_all(
        self,
        issues: list[ValidationIssue],
    ) -> list[TriagedIssue]:
        """Prompt user to triage each issue manually.

        Args:
            issues: List of issues to triage.

        Returns:
            List of triaged issues with user decisions.
        """
        results: list[TriagedIssue] = []

        for issue in issues:
            # TODO: Implement user prompts (Task 4)
            # For now, default to FIX
            results.append(
                TriagedIssue(
                    issue=issue,
                    decision=TriageDecision.FIX,
                    reason="Pending manual triage implementation",
                    auto_decided=False,
                )
            )

        return results

    def _hybrid_triage_all(
        self,
        issues: list[ValidationIssue],
    ) -> list[TriagedIssue]:
        """Auto-triage low severity, manual for errors.

        Args:
            issues: List of issues to triage.

        Returns:
            List of triaged issues with mixed decisions.
        """
        results: list[TriagedIssue] = []

        for issue in issues:
            # TODO: Implement hybrid logic (Task 5)
            # For now, use auto triage for all
            if issue.severity == IssueSeverity.ERROR:
                # Will be manual in Task 5
                results.append(
                    TriagedIssue(
                        issue=issue,
                        decision=TriageDecision.FIX,
                        reason="Error severity requires fix",
                        auto_decided=False,
                    )
                )
            else:
                # Auto-triage for non-errors
                auto_result = self._auto_triage_all([issue])
                results.extend(auto_result)

        return results


__all__ = ["TriageSystem"]
