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
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    IssueSeverity,
    IssueSource,
    TriageDecision,
    TriagedIssue,
    ValidationIssue,
)

if TYPE_CHECKING:
    from adw.executors.base import LLMExecutor

logger = logging.getLogger(__name__)


@dataclass
class TriageStats:
    """Statistics about triage decisions.

    Attributes:
        fix_count: Number of issues marked for fixing.
        dismiss_count: Number of issues dismissed.
        defer_count: Number of issues deferred.
        auto_decided_count: Number of auto-decided issues.
        manual_decided_count: Number of manually decided issues.
    """

    fix_count: int = 0
    dismiss_count: int = 0
    defer_count: int = 0
    auto_decided_count: int = 0
    manual_decided_count: int = 0

    @property
    def total(self) -> int:
        """Total number of triaged issues."""
        return self.fix_count + self.dismiss_count + self.defer_count

    def to_dict(self) -> dict[str, int]:
        """Convert stats to dictionary for serialization."""
        return {
            "fix_count": self.fix_count,
            "dismiss_count": self.dismiss_count,
            "defer_count": self.defer_count,
            "auto_decided_count": self.auto_decided_count,
            "manual_decided_count": self.manual_decided_count,
            "total": self.total,
        }


@dataclass
class TriageResult:
    """Result of a triage operation with statistics.

    Attributes:
        triaged_issues: List of triaged issues with decisions.
        stats: Statistics about the decisions made.
    """

    triaged_issues: list["TriagedIssue"]
    stats: TriageStats

    def summary(self) -> str:
        """Generate a human-readable summary of triage results."""
        parts = []
        if self.stats.fix_count:
            parts.append(f"{self.stats.fix_count} FIX")
        if self.stats.dismiss_count:
            parts.append(f"{self.stats.dismiss_count} DISMISS")
        if self.stats.defer_count:
            parts.append(f"{self.stats.defer_count} DEFER")

        if not parts:
            return "No issues triaged"

        return f"Triage: {', '.join(parts)} ({self.stats.total} total)"

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for logging/serialization."""
        return {
            "triaged_issues": [
                {
                    "issue_id": ti.issue.id,
                    "decision": ti.decision.value,
                    "reason": ti.reason,
                    "auto_decided": ti.auto_decided,
                }
                for ti in self.triaged_issues
            ],
            "stats": self.stats.to_dict(),
        }

    def get_issues_to_fix(self) -> list["TriagedIssue"]:
        """Return only issues marked for fixing."""
        return [ti for ti in self.triaged_issues if ti.decision == TriageDecision.FIX]


@dataclass
class TriageRule:
    """A configurable rule for automatic triage decisions.

    Rules can match on source, severity, and/or description pattern.
    All specified criteria must match for the rule to apply.

    Attributes:
        action: The TriageDecision to apply when rule matches.
        reason: Explanation for the triage decision.
        source: Match issues from this source (optional).
        severity: Match issues with this severity (optional).
        description_pattern: Regex pattern to match description (optional).
    """

    action: TriageDecision
    reason: str
    source: IssueSource | None = None
    severity: IssueSeverity | None = None
    description_pattern: str | None = None

    def matches(self, issue: ValidationIssue) -> bool:
        """Check if this rule matches the given issue.

        Args:
            issue: The issue to check against.

        Returns:
            True if all specified criteria match.
        """
        # Check source if specified
        if self.source is not None and issue.source != self.source:
            return False

        # Check severity if specified
        if self.severity is not None and issue.severity != self.severity:
            return False

        # Check description pattern if specified
        if self.description_pattern is None:
            return True
        return bool(
            re.search(self.description_pattern, issue.description, re.IGNORECASE)
        )


class TriageSystem:
    """System for triaging validation issues.

    Categorizes issues into FIX, DISMISS, or DEFER decisions based on
    the configured triage mode.

    Attributes:
        config: Validation configuration with triage settings.
        llm_executor: Optional LLM executor for auto triage mode.
        console: Rich console for user interaction.
        rules: List of triage rules to apply before LLM.
    """

    def __init__(
        self,
        config: ValidationConfig,
        llm_executor: "LLMExecutor | None" = None,
        console: Console | None = None,
        rules: list[TriageRule] | None = None,
    ) -> None:
        """Initialize the triage system.

        Args:
            config: Validation configuration with triage settings.
            llm_executor: Optional LLM executor for auto triage decisions.
            console: Optional Rich console for user interaction.
            rules: Optional list of rules to apply before LLM fallback.
        """
        self.config = config
        self.llm_executor = llm_executor
        self.console = console or Console()
        self.rules = rules or []

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

    def triage_with_result(
        self,
        issues: list[ValidationIssue],
        mode: Literal["auto", "manual", "hybrid"] | None = None,
    ) -> TriageResult:
        """Triage all issues and return structured result with statistics.

        Like triage(), but returns a TriageResult with statistics for logging
        and audit trail purposes.

        Args:
            issues: List of validation issues to triage.
            mode: Triage mode override. If None, uses config.triage_mode.

        Returns:
            TriageResult with triaged issues and statistics.
        """
        triaged_issues = self.triage(issues, mode)

        # Compute statistics
        stats = TriageStats()
        for ti in triaged_issues:
            if ti.decision == TriageDecision.FIX:
                stats.fix_count += 1
            elif ti.decision == TriageDecision.DISMISS:
                stats.dismiss_count += 1
            else:
                stats.defer_count += 1

            if ti.auto_decided:
                stats.auto_decided_count += 1
            else:
                stats.manual_decided_count += 1

        logger.info(
            "Triage complete: %d FIX, %d DISMISS, %d DEFER",
            stats.fix_count,
            stats.dismiss_count,
            stats.defer_count,
        )

        return TriageResult(triaged_issues=triaged_issues, stats=stats)

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

            # Check triage rules (first match wins)
            rule_result = self._apply_rules(issue)
            if rule_result is not None:
                results.append(rule_result)
                continue

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
            else:
                logger.warning("LLM triage returned unsuccessful result")
        except Exception as e:
            logger.warning("LLM triage failed: %s", e)

        # Fallback to FIX on any error or unsuccessful result
        return TriagedIssue(
            issue=issue,
            decision=TriageDecision.FIX,
            reason="LLM triage failed, defaulting to FIX",
            auto_decided=True,
        )

    def _apply_rules(self, issue: ValidationIssue) -> TriagedIssue | None:
        """Apply triage rules to an issue.

        Checks each rule in order; first matching rule wins.

        Args:
            issue: The issue to check against rules.

        Returns:
            TriagedIssue if a rule matched, None otherwise.
        """
        for rule in self.rules:
            if rule.matches(issue):
                return TriagedIssue(
                    issue=issue,
                    decision=rule.action,
                    reason=rule.reason,
                    auto_decided=True,
                )
        return None

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
                snippet = issue.context.code_snippet[:500]
                is_truncated = len(issue.context.code_snippet) > 500
                truncated = " (truncated)" if is_truncated else ""
                context_str += f"\n- Code snippet{truncated}:\n```\n{snippet}\n```"
            if issue.context.error_message:
                context_str += f"\n- Error message: {issue.context.error_message}"
            if issue.context.suggestion:
                context_str += f"\n- Suggestion: {issue.context.suggestion}"

        return f"""You are triaging a validation issue. Based on the severity and \
context, decide whether to FIX, DISMISS, or DEFER this issue.

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

        for i, issue in enumerate(issues):
            triaged = self._prompt_triage_decision(issue, i + 1, len(issues))
            results.append(triaged)

        return results

    def _prompt_triage_decision(
        self,
        issue: ValidationIssue,
        current: int,
        total: int,
    ) -> TriagedIssue:
        """Prompt user for triage decision on a single issue.

        Args:
            issue: The issue to triage.
            current: Current issue number (1-indexed).
            total: Total number of issues.

        Returns:
            TriagedIssue with user's decision.
        """
        # Display issue details
        self._display_issue(issue, current, total)

        # Prompt for decision
        decision_str = Prompt.ask(
            "[F]ix, [D]ismiss, d[E]fer",
            choices=["f", "d", "e", "F", "D", "E"],
            default="f",
        ).lower()

        decision_map = {
            "f": TriageDecision.FIX,
            "d": TriageDecision.DISMISS,
            "e": TriageDecision.DEFER,
        }
        decision = decision_map[decision_str]

        # Prompt for reason
        reason = Prompt.ask("Reason (optional)", default="")
        if not reason:
            reason = f"User selected {decision.value}"

        return TriagedIssue(
            issue=issue,
            decision=decision,
            reason=reason,
            auto_decided=False,
        )

    def _display_issue(
        self,
        issue: ValidationIssue,
        current: int,
        total: int,
    ) -> None:
        """Display issue details in a Rich panel.

        Args:
            issue: The issue to display.
            current: Current issue number.
            total: Total number of issues.
        """
        # Create severity color mapping
        severity_colors = {
            IssueSeverity.ERROR: "red",
            IssueSeverity.WARNING: "yellow",
            IssueSeverity.INFO: "blue",
        }
        color = severity_colors.get(issue.severity, "white")

        # Build content
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="dim")
        table.add_column("Value")

        table.add_row("Source", issue.source.value)
        table.add_row("Severity", f"[{color}]{issue.severity.value}[/]")
        table.add_row("Description", issue.description)

        if issue.location:
            loc = issue.location.file_path or ""
            if issue.location.line_start:
                loc += f":{issue.location.line_start}"
            table.add_row("Location", loc)

        if issue.context and issue.context.error_message:
            table.add_row("Error", issue.context.error_message[:100])

        if issue.context and issue.context.suggestion:
            table.add_row("Suggestion", issue.context.suggestion)

        self.console.print(
            Panel(
                table,
                title=f"[bold]Issue {current}/{total}[/]",
                border_style=color,
            )
        )

    def _hybrid_triage_all(
        self,
        issues: list[ValidationIssue],
    ) -> list[TriagedIssue]:
        """Auto-triage low severity, manual for errors.

        Hybrid mode combines automatic and manual triage:
        - INFO severity: Auto-dismissed (if auto_dismiss_info enabled)
        - WARNING severity: Auto-triaged (rules/LLM or default to FIX)
        - ERROR severity: Manual prompt required

        Args:
            issues: List of issues to triage.

        Returns:
            List of triaged issues with mixed decisions.
        """
        results: list[TriagedIssue] = []

        # Track ERROR issues for manual triage
        error_count = sum(
            1 for issue in issues if issue.severity == IssueSeverity.ERROR
        )
        error_index = 0

        for issue in issues:
            if issue.severity == IssueSeverity.ERROR:
                # Manual triage for ERROR severity
                error_index += 1
                triaged = self._prompt_triage_decision(
                    issue, error_index, error_count
                )
                results.append(triaged)
            else:
                # Auto-triage for non-errors (INFO and WARNING)
                auto_result = self._auto_triage_all([issue])
                results.extend(auto_result)

        return results


__all__ = ["TriageResult", "TriageRule", "TriageStats", "TriageSystem"]
