"""Validation report generation.

Story 11.7: Validation Report Generation

This module provides:
- ValidationReport: Pydantic model for validation loop results
- ConfidenceLevel: Enum for confidence assessment
- DeferredIssueSummary: Summary of deferred issues for reports
- ValidationReportGenerator: Generates reports from loop results

Reports are stored at:
.adw/runs/<run_id>/artifacts/validation/
├── report.md        # Human-readable report
└── report.json      # Machine-readable report
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from adw.validation.config import ValidationConfig
    from adw.validation.models import ValidationIssue
    from adw.validation.state_manager import ValidationStateManager

__all__ = [
    "ConfidenceLevel",
    "DeferredIssueSummary",
    "ValidationReport",
    "ValidationReportGenerator",
]

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level for validation results.

    - HIGH: All resolved, none deferred
    - MEDIUM: Some deferred (<30%)
    - LOW: Many deferred (>=30%) or many dismissed
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DeferredIssueSummary(BaseModel):
    """Summary of a deferred issue for reports.

    Contains minimal information needed to describe a deferred issue
    in the validation report and PR description.

    Attributes:
        issue_id: Unique issue ID (VI-{ulid} format).
        source: Which validator found this issue (TEST, REVIEW, EVIDENCE).
        severity: Issue severity level (ERROR, WARNING, INFO).
        description: Human-readable description of the issue.
        reason: Reason for deferral.
        file_path: File path where the issue was found, if known.
    """

    issue_id: str
    source: str
    severity: str
    description: str
    reason: str
    file_path: str | None = None

    model_config = {"frozen": False, "validate_assignment": True}


class ValidationReport(BaseModel):
    """Validation report summarizing loop results.

    Contains all metrics and details from the validation loop execution,
    including issue counts, confidence assessment, and deferred issues.

    Attributes:
        run_id: The run ID this report belongs to.
        generated_at: When the report was generated.
        duration_seconds: Total validation duration in seconds.
        iterations_run: Number of iterations completed.
        max_iterations: Maximum iterations configured.
        exit_reason: Why the loop exited (ALL_RESOLVED, MAX_ITERATIONS, etc.).
        issues_found: Total issues discovered.
        issues_fixed: Number of issues successfully fixed.
        issues_dismissed: Number of issues dismissed as false positives.
        issues_deferred: Number of issues deferred for later.
        confidence: Overall confidence level.
        confidence_explanation: Explanation for the confidence level.
        deferred_issues: List of deferred issue summaries.
    """

    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float

    # Iteration metrics
    iterations_run: int
    max_iterations: int
    exit_reason: str

    # Issue metrics
    issues_found: int
    issues_fixed: int
    issues_dismissed: int
    issues_deferred: int

    # Confidence
    confidence: ConfidenceLevel
    confidence_explanation: str

    # Detailed lists
    deferred_issues: list[DeferredIssueSummary] = Field(default_factory=list)

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "run_id": "01HQ123456789ABCDEFGHJKMNP",
                "generated_at": "2026-01-05T10:30:00Z",
                "duration_seconds": 45.2,
                "iterations_run": 3,
                "max_iterations": 5,
                "exit_reason": "ALL_RESOLVED",
                "issues_found": 8,
                "issues_fixed": 5,
                "issues_dismissed": 1,
                "issues_deferred": 2,
                "confidence": "MEDIUM",
                "confidence_explanation": "2 issues deferred (25%)",
            }
        },
    }

    def to_markdown(self) -> str:
        """Generate markdown report.

        Produces a GitHub-flavored markdown report with:
        - Header with run info
        - Summary table with metrics
        - Confidence section
        - Deferred issues section (if any)

        Returns:
            Markdown-formatted string.
        """
        lines = [
            "# Validation Report",
            "",
            f"**Run ID:** {self.run_id}",
            f"**Generated:** {self.generated_at.isoformat()}",
            f"**Duration:** {self.duration_seconds:.1f}s",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Iterations | {self.iterations_run}/{self.max_iterations} |",
            f"| Issues Found | {self.issues_found} |",
            f"| Issues Fixed | {self.issues_fixed} |",
            f"| Issues Dismissed | {self.issues_dismissed} |",
            f"| Issues Deferred | {self.issues_deferred} |",
            f"| Exit Reason | {self.exit_reason} |",
            "",
            f"## Confidence: {self.confidence.value}",
            "",
            f"{self.confidence_explanation}",
            "",
        ]

        if self.deferred_issues:
            lines.extend(
                [
                    "## Deferred Issues",
                    "",
                    "The following issues were deferred for later resolution:",
                    "",
                ]
            )
            for issue in self.deferred_issues:
                lines.extend(
                    [
                        f"### {issue.issue_id}",
                        "",
                        f"- **Source:** {issue.source}",
                        f"- **Severity:** {issue.severity}",
                        f"- **Description:** {issue.description}",
                        f"- **Reason:** {issue.reason}",
                    ]
                )
                if issue.file_path:
                    lines.append(f"- **Location:** `{issue.file_path}`")
                lines.append("")

        return "\n".join(lines)

    def to_pr_section(self) -> str:
        """Generate PR description section for known issues.

        Produces a concise section suitable for PR descriptions,
        including a confidence badge and list of deferred issues.

        Returns:
            Markdown string for PR description, or empty string if no deferred.
        """
        if not self.deferred_issues:
            return ""

        badge = {
            ConfidenceLevel.HIGH: (
                "![HIGH](https://img.shields.io/badge/confidence-HIGH-green)"
            ),
            ConfidenceLevel.MEDIUM: (
                "![MEDIUM](https://img.shields.io/badge/confidence-MEDIUM-yellow)"
            ),
            ConfidenceLevel.LOW: (
                "![LOW](https://img.shields.io/badge/confidence-LOW-red)"
            ),
        }[self.confidence]

        lines = [
            f"## Known Issues {badge}",
            "",
            "The following issues were identified but deferred:",
            "",
        ]
        for issue in self.deferred_issues:
            lines.append(f"- **{issue.source}:** {issue.description}")
            if issue.file_path:
                lines.append(f"  - Location: `{issue.file_path}`")

        return "\n".join(lines)


class ValidationReportGenerator:
    """Generates validation reports from loop results.

    Takes loop summary data and issues, calculates confidence,
    and produces both human and machine-readable reports.

    Attributes:
        state_manager: ValidationStateManager for data access.
        config: ValidationConfig for max_iterations reference.

    Example:
        >>> generator = ValidationReportGenerator(state_manager, config)
        >>> report = generator.generate(loop_summary, issues, start_time)
        >>> report_path = generator.save(report)
    """

    def __init__(
        self,
        state_manager: ValidationStateManager,
        config: ValidationConfig,
    ) -> None:
        """Initialize the report generator.

        Args:
            state_manager: ValidationStateManager for data access and paths.
            config: ValidationConfig for configuration values.
        """
        self.state_manager = state_manager
        self.config = config

    def generate(
        self,
        loop_summary: dict[str, Any],
        issues: list[ValidationIssue],
        start_time: datetime,
    ) -> ValidationReport:
        """Generate validation report from loop results.

        Args:
            loop_summary: Dictionary with loop statistics from controller.
            issues: List of all validation issues.
            start_time: When validation phase started.

        Returns:
            ValidationReport with all metrics and deferred issues.
        """
        duration = (datetime.now(UTC) - start_time).total_seconds()

        # Collect deferred issues for the report
        deferred = [
            DeferredIssueSummary(
                issue_id=i.id,
                source=i.source.value,
                severity=i.severity.value,
                description=i.description,
                reason=i.triage_reason or "Unknown",
                file_path=i.location.file_path if i.location else None,
            )
            for i in issues
            if i.triage_decision == "DEFER"
        ]

        # Calculate confidence
        confidence, explanation = self._calculate_confidence(
            issues_found=len(issues),
            issues_fixed=loop_summary.get("resolved", 0),
            issues_dismissed=loop_summary.get("dismissed", 0),
            issues_deferred=loop_summary.get("deferred", 0),
        )

        return ValidationReport(
            run_id=self.state_manager.run_id,
            duration_seconds=duration,
            iterations_run=loop_summary.get("iterations_run", 0),
            max_iterations=self.config.max_iterations,
            exit_reason=loop_summary.get("exit_reason", "COMPLETED"),
            issues_found=len(issues),
            issues_fixed=loop_summary.get("resolved", 0),
            issues_dismissed=loop_summary.get("dismissed", 0),
            issues_deferred=loop_summary.get("deferred", 0),
            confidence=confidence,
            confidence_explanation=explanation,
            deferred_issues=deferred,
        )

    def _calculate_confidence(
        self,
        issues_found: int,
        issues_fixed: int,
        issues_dismissed: int,
        issues_deferred: int,
    ) -> tuple[ConfidenceLevel, str]:
        """Calculate confidence level based on issue resolution.

        Args:
            issues_found: Total issues found.
            issues_fixed: Issues successfully fixed.
            issues_dismissed: Issues dismissed.
            issues_deferred: Issues deferred.

        Returns:
            Tuple of (ConfidenceLevel, explanation string).
        """
        if issues_found == 0:
            return ConfidenceLevel.HIGH, "No issues found during validation."

        deferred_ratio = issues_deferred / issues_found if issues_found > 0 else 0
        dismissed_ratio = issues_dismissed / issues_found if issues_found > 0 else 0

        if issues_deferred == 0 and dismissed_ratio < 0.5:
            return (
                ConfidenceLevel.HIGH,
                f"All {issues_found} issues resolved or appropriately handled.",
            )

        # LOW: many deferred (>= 30%) OR many dismissed (>= 50%)
        if deferred_ratio >= 0.3:
            return (
                ConfidenceLevel.LOW,
                f"{issues_deferred} issues deferred ({deferred_ratio:.0%}). "
                "Manual review required.",
            )

        if dismissed_ratio >= 0.5:
            return (
                ConfidenceLevel.LOW,
                f"{issues_dismissed} issues dismissed ({dismissed_ratio:.0%}). "
                "Manual review required.",
            )

        # MEDIUM: some deferred (< 30%) and not many dismissed
        return (
            ConfidenceLevel.MEDIUM,
            f"{issues_deferred} issues deferred ({deferred_ratio:.0%}). "
            "Review recommended.",
        )

    def save(self, report: ValidationReport) -> Path:
        """Save report to artifacts directory.

        Creates both markdown and JSON versions of the report
        in the artifacts/validation/ directory.

        Args:
            report: The ValidationReport to save.

        Returns:
            Path to the markdown report file.
        """
        # Get artifacts directory (parent of validation_dir)
        artifacts_dir = (
            self.state_manager.validation_dir.parent / "artifacts" / "validation"
        )
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Save markdown
        md_path = artifacts_dir / "report.md"
        md_path.write_text(report.to_markdown())
        logger.info("Saved markdown report", extra={"path": str(md_path)})

        # Save JSON
        json_path = artifacts_dir / "report.json"
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, default=str)
        )
        logger.info("Saved JSON report", extra={"path": str(json_path)})

        return md_path
