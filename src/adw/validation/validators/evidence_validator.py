"""EvidenceValidator - Validates evidence gathering results.

This validator checks the evidence manifest from the Validate phase
and reports any failed or missing evidence.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from adw.models.evidence import EvidenceManifest, EvidenceStatus
from adw.validation.models import ValidationIssue, ValidationSource

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)


class EvidenceValidator:
    """Validator that checks evidence gathering results.

    Loads the evidence manifest from the Validate phase and reports
    issues for any failed, errored, or skipped evidence items.

    Attributes:
        report_skipped: Whether to report skipped evidence as issues.
    """

    def __init__(
        self,
        report_skipped: bool = False,
    ) -> None:
        """Initialize the evidence validator.

        Args:
            report_skipped: Whether to report skipped evidence as issues.
        """
        self._report_skipped = report_skipped

    @property
    def name(self) -> str:
        """Return the validator's name."""
        return "evidence"

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        """Check evidence manifest and return issues for failures.

        Args:
            context: Current run context with artifacts.

        Returns:
            List of ValidationIssues for failed/missing evidence.
        """
        # Load evidence manifest
        manifest = self._load_manifest(context)

        if manifest is None:
            return [
                ValidationIssue(
                    source=ValidationSource.EVIDENCE,
                    message="Evidence manifest not found - evidence gathering may have failed",
                    severity="high",
                )
            ]

        logger.info(
            f"Checking evidence manifest: {manifest.total_items} items, "
            f"{manifest.passed} passed, {manifest.failed} failed"
        )

        issues: list[ValidationIssue] = []

        # Check each evidence item
        for item in manifest.items:
            # Get error message from details if present
            error_msg = ""
            if item.details and isinstance(item.details, dict):
                error_msg = item.details.get("error", "")

            if item.status == EvidenceStatus.FAIL:
                issues.append(
                    ValidationIssue(
                        source=ValidationSource.EVIDENCE,
                        message=f"Evidence failed: {item.name}" + (
                            f" - {error_msg}" if error_msg else ""
                        ),
                        severity="high",
                        file_path=item.path,
                    )
                )
            elif item.status == EvidenceStatus.ERROR:
                issues.append(
                    ValidationIssue(
                        source=ValidationSource.EVIDENCE,
                        message=f"Evidence error: {item.name}" + (
                            f" - {error_msg}" if error_msg else ""
                        ),
                        severity="high",
                        file_path=item.path,
                    )
                )
            elif item.status == EvidenceStatus.SKIPPED and self._report_skipped:
                issues.append(
                    ValidationIssue(
                        source=ValidationSource.EVIDENCE,
                        message=f"Evidence skipped: {item.name}",
                        severity="info",
                        file_path=item.path,
                    )
                )

        logger.info(f"Evidence validation found {len(issues)} issues")
        return issues

    def _load_manifest(self, context: RunContext) -> EvidenceManifest | None:
        """Load the evidence manifest from the run directory.

        Args:
            context: Current run context.

        Returns:
            EvidenceManifest if found, None otherwise.
        """
        # Try to find manifest in artifacts (default to cwd if no worktree)
        base_path = context.worktree_path or Path.cwd()

        # Try common manifest locations (ISS-019: validate replaces verify)
        run_dir = base_path / ".adw" / "runs" / context.run_id
        potential_paths = [
            run_dir / "evidence" / "evidence_manifest.json",
            run_dir / "artifacts" / "validate" / "evidence_manifest.json",
            # Backwards compatibility: support legacy runs with verify artifacts
            run_dir / "artifacts" / "verify" / "evidence_manifest.json",
        ]

        for path in potential_paths:
            if path.exists():
                try:
                    content = path.read_text()
                    data = json.loads(content)
                    return EvidenceManifest.model_validate(data)
                except Exception as e:
                    logger.warning(f"Failed to load manifest from {path}: {e}")
                    continue

        logger.warning("Evidence manifest not found in any expected location")
        return None


__all__ = ["EvidenceValidator"]
