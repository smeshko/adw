"""Issue triage system for the validation loop.

This module provides the TriageSystem class that categorizes
validation issues into FIX, DISMISS, or DEFER decisions.

Supports three triage modes:
- auto: LLM makes all decisions based on severity/context
- manual: User prompted for each issue interactively
- hybrid: Auto for low severity, manual for errors
"""

import json
import logging
from typing import TYPE_CHECKING, Literal

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

logger = logging.getLogger(__name__)


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

            # Try LLM triage if executor available
            if self.llm_executor is not None:
                triaged = self._llm_triage(issue)
                results.append(triaged)
                continue

            # Default to FIX when no LLM available
            results.append(
                TriagedIssue(
                    issue=issue,
                    decision=TriageDecision.FIX,
                    reason="Default: issue requires fix (no LLM available)",
                    auto_decided=True,
                )
            )

        return results

    def _llm_triage(self, issue: ValidationIssue) -> TriagedIssue:
        """Use LLM to triage a single issue.

        Args:
            issue: The issue to triage.

        Returns:
            TriagedIssue with LLM's decision.
        """
        prompt = self._build_triage_prompt(issue)

        try:
            result = self.llm_executor.execute(prompt)  # type: ignore[union-attr]

            if result.success:
                decision, reason = self._parse_triage_response(result.content)
                return TriagedIssue(
                    issue=issue,
                    decision=decision,
                    reason=reason,
                    auto_decided=True,
                )
        except Exception as e:
            logger.warning("LLM triage failed: %s", e)

        # Fallback to FIX on any error
        return TriagedIssue(
            issue=issue,
            decision=TriageDecision.FIX,
            reason="LLM triage failed, defaulting to FIX",
            auto_decided=True,
        )

    def _build_triage_prompt(self, issue: ValidationIssue) -> str:
        """Build the LLM prompt for triage decision.

        Args:
            issue: The issue to include in the prompt.

        Returns:
            Formatted prompt string.
        """
        location_str = ""
        if issue.location:
            location_str = f"- Location: {issue.location.file_path}"
            if issue.location.line_start:
                location_str += f" (line {issue.location.line_start})"

        context_str = ""
        if issue.context:
            if issue.context.code_snippet:
                context_str += f"\n- Code snippet:\n```\n{issue.context.code_snippet[:500]}\n```"
            if issue.context.error_message:
                context_str += f"\n- Error message: {issue.context.error_message}"
            if issue.context.suggestion:
                context_str += f"\n- Suggestion: {issue.context.suggestion}"

        return f"""You are triaging a validation issue. Based on the severity and context,
decide whether to FIX, DISMISS, or DEFER this issue.

Issue:
- Source: {issue.source.value}
- Severity: {issue.severity.value}
- Description: {issue.description}
{location_str}
{context_str}

Guidelines:
- FIX: Issues that block functionality or indicate bugs
- DISMISS: Issues that are false positives or not relevant
- DEFER: Issues that are valid but can be addressed later

Respond with JSON only:
{{"decision": "FIX|DISMISS|DEFER", "reason": "Brief explanation"}}
"""

    def _parse_triage_response(
        self, content: str
    ) -> tuple[TriageDecision, str]:
        """Parse LLM response to extract decision and reason.

        Args:
            content: The LLM response content.

        Returns:
            Tuple of (TriageDecision, reason string).

        Raises:
            ValueError: If response cannot be parsed.
        """
        try:
            # Try to find JSON in response
            content = content.strip()

            # Handle case where content has extra text before/after JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]

            data = json.loads(content)

            decision_str = data.get("decision", "").upper()
            reason = data.get("reason", "No reason provided")

            # Map to enum
            decision_map = {
                "FIX": TriageDecision.FIX,
                "DISMISS": TriageDecision.DISMISS,
                "DEFER": TriageDecision.DEFER,
            }

            if decision_str not in decision_map:
                raise ValueError(f"Unknown decision: {decision_str}")

            return decision_map[decision_str], reason

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse triage response: %s", e)
            raise ValueError(f"Invalid triage response: {e}") from e

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
