"""Evidence manifest generator for ADW.

This module provides the ManifestGenerator class for creating evidence
manifests that link captured evidence to plan steps for traceability
and coverage analysis.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Union

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    APIEvidenceResult,
    APIEvidenceSummary,
    CLIEvidenceSummary,
    CommandResult,
    EvidenceItem,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceType,
    MobileEvidenceSummary,
    MobileScreenshotResult,
    ScreenshotResult,
    WebEvidenceSummary,
)

# Union type for all evidence summary types
EvidenceSummary = Union[
    CLIEvidenceSummary,
    WebEvidenceSummary,
    APIEvidenceSummary,
    MobileEvidenceSummary,
]


class ManifestGenerator:
    """Generator for evidence manifests.

    Creates comprehensive manifests that aggregate all captured evidence
    from different strategies (CLI, web, API, mobile) and link them
    to plan steps for coverage analysis.

    Attributes:
        run_id: Unique identifier for the run
        platform: Detected platform type
        evidence_directory: Path to the evidence directory

    Example:
        >>> generator = ManifestGenerator(
        ...     run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        ...     platform="backend",
        ...     evidence_directory=Path(".adw/runs/01HQXK/evidence"),
        ... )
        >>> manifest = generator.generate([cli_summary, api_summary])
    """

    def __init__(
        self,
        run_id: str,
        platform: str,
        evidence_directory: Path,
    ) -> None:
        """Initialize the manifest generator.

        Args:
            run_id: Unique identifier for the run (ULID)
            platform: Detected platform type (cli, web, backend, etc.)
            evidence_directory: Path to the evidence directory
        """
        self.run_id = run_id
        self.platform = platform
        self.evidence_directory = evidence_directory
        self._logger = get_logger()

    def generate(
        self,
        summaries: list[EvidenceSummary],
    ) -> EvidenceManifest:
        """Generate an evidence manifest from strategy summaries.

        Aggregates results from all evidence capture strategies into
        a single manifest with summary statistics.

        Args:
            summaries: List of evidence summaries from different strategies
                       (CLIEvidenceSummary, WebEvidenceSummary, etc.)

        Returns:
            EvidenceManifest with all evidence items and statistics
        """
        items: list[EvidenceItem] = []

        for summary in summaries:
            items.extend(self._extract_items(summary))

        # Calculate statistics
        passed = sum(1 for item in items if item.status == EvidenceStatus.PASS)
        failed = sum(1 for item in items if item.status == EvidenceStatus.FAIL)
        errors = sum(1 for item in items if item.status == EvidenceStatus.ERROR)
        skipped = sum(1 for item in items if item.status == EvidenceStatus.SKIPPED)

        manifest = EvidenceManifest(
            run_id=self.run_id,
            generated_at=datetime.now(UTC),
            platform=self.platform,
            evidence_directory=str(self.evidence_directory),
            total_items=len(items),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            items=items,
            coverage=None,  # Set by plan step linking
            step_coverage=None,  # Set by plan step linking
        )

        self._logger.info(
            LogCategory.STATE,
            f"Generated evidence manifest: {len(items)} items "
            f"({passed} passed, {failed} failed, {errors} errors, {skipped} skipped)",
        )

        return manifest

    def _extract_items(self, summary: EvidenceSummary) -> list[EvidenceItem]:
        """Extract evidence items from a strategy summary.

        Converts strategy-specific result types into unified EvidenceItem
        objects for the manifest.

        Args:
            summary: Evidence summary from a specific strategy

        Returns:
            List of EvidenceItem objects
        """
        if isinstance(summary, CLIEvidenceSummary):
            return self._extract_cli_items(summary)
        elif isinstance(summary, WebEvidenceSummary):
            return self._extract_web_items(summary)
        elif isinstance(summary, APIEvidenceSummary):
            return self._extract_api_items(summary)
        elif isinstance(summary, MobileEvidenceSummary):
            return self._extract_mobile_items(summary)
        else:
            self._logger.warn(
                LogCategory.STATE,
                f"Unknown evidence summary type: {type(summary).__name__}",
            )
            return []

    def _extract_cli_items(
        self,
        summary: CLIEvidenceSummary,
    ) -> list[EvidenceItem]:
        """Extract evidence items from CLI summary.

        Args:
            summary: CLI evidence summary

        Returns:
            List of EvidenceItem objects from CLI results
        """
        items: list[EvidenceItem] = []

        for result in summary.results:
            status = self._cli_status(result)
            # Generate relative path from command name
            # CLI results are stored as cli/<name>.txt
            name = self._sanitize_name(result.command.split()[0])
            path = f"cli/{name}.txt"

            items.append(
                EvidenceItem(
                    name=name,
                    type=EvidenceType.CLI,
                    path=path,
                    status=status,
                    plan_step=None,  # Set by plan step linking
                    details={
                        "command": result.command,
                        "exit_code": result.exit_code,
                        "duration_seconds": result.duration_seconds,
                    },
                )
            )

        return items

    def _extract_web_items(
        self,
        summary: WebEvidenceSummary,
    ) -> list[EvidenceItem]:
        """Extract evidence items from web screenshot summary.

        Args:
            summary: Web evidence summary

        Returns:
            List of EvidenceItem objects from web results
        """
        items: list[EvidenceItem] = []

        for result in summary.results:
            status = self._web_status(result)
            # Generate relative path from result
            name = f"{result.route}_{result.viewport.replace('x', '_')}"
            path = f"screenshots/{result.path.name}" if result.path else f"screenshots/{name}.png"

            items.append(
                EvidenceItem(
                    name=name,
                    type=EvidenceType.SCREENSHOT,
                    path=path,
                    status=status,
                    plan_step=None,  # Set by plan step linking
                    details={
                        "route": result.route,
                        "viewport": result.viewport,
                        "base_url": summary.base_url,
                    },
                )
            )

        return items

    def _extract_api_items(
        self,
        summary: APIEvidenceSummary,
    ) -> list[EvidenceItem]:
        """Extract evidence items from API summary.

        Args:
            summary: API evidence summary

        Returns:
            List of EvidenceItem objects from API results
        """
        items: list[EvidenceItem] = []

        for result in summary.results:
            status = self._api_status(result)
            name = result.endpoint_name
            path = f"api/{name}.json"

            items.append(
                EvidenceItem(
                    name=name,
                    type=EvidenceType.API,
                    path=path,
                    status=status,
                    plan_step=None,  # Set by plan step linking
                    details={
                        "method": result.request.method,
                        "url": result.request.url,
                        "status_code": result.response.status_code,
                        "duration_seconds": result.response.duration_seconds,
                        "expected_status": result.expected_status,
                        "status_match": result.status_match,
                    },
                )
            )

        return items

    def _extract_mobile_items(
        self,
        summary: MobileEvidenceSummary,
    ) -> list[EvidenceItem]:
        """Extract evidence items from mobile screenshot summary.

        Args:
            summary: Mobile evidence summary

        Returns:
            List of EvidenceItem objects from mobile results
        """
        items: list[EvidenceItem] = []

        for result in summary.results:
            status = self._mobile_status(result)
            name = f"{result.screen_name}_{result.device_type.value}"
            path = f"screenshots/{result.path.name}" if result.path else f"screenshots/{name}.png"

            items.append(
                EvidenceItem(
                    name=name,
                    type=EvidenceType.SCREENSHOT,
                    path=path,
                    status=status,
                    plan_step=None,  # Set by plan step linking
                    details={
                        "screen_name": result.screen_name,
                        "device_type": result.device_type.value,
                        "device_name": result.device_name,
                        "os_version": result.os_version,
                    },
                )
            )

        return items

    def _cli_status(self, result: CommandResult) -> EvidenceStatus:
        """Determine status from CLI result.

        Args:
            result: Command execution result

        Returns:
            EvidenceStatus based on exit code
        """
        if result.success:
            return EvidenceStatus.PASS
        elif result.exit_code == -1:  # Timeout
            return EvidenceStatus.ERROR
        else:
            return EvidenceStatus.FAIL

    def _web_status(self, result: ScreenshotResult) -> EvidenceStatus:
        """Determine status from web screenshot result.

        Args:
            result: Screenshot capture result

        Returns:
            EvidenceStatus based on success flag
        """
        if result.success:
            return EvidenceStatus.PASS
        elif result.error:
            return EvidenceStatus.ERROR
        else:
            return EvidenceStatus.FAIL

    def _api_status(self, result: APIEvidenceResult) -> EvidenceStatus:
        """Determine status from API result.

        Args:
            result: API evidence result

        Returns:
            EvidenceStatus based on success and status match
        """
        if result.error:
            return EvidenceStatus.ERROR
        elif not result.success:
            return EvidenceStatus.FAIL
        elif not result.status_match:
            return EvidenceStatus.FAIL
        else:
            return EvidenceStatus.PASS

    def _mobile_status(self, result: MobileScreenshotResult) -> EvidenceStatus:
        """Determine status from mobile screenshot result.

        Args:
            result: Mobile screenshot result

        Returns:
            EvidenceStatus based on success flag
        """
        if result.success:
            return EvidenceStatus.PASS
        elif result.error:
            return EvidenceStatus.ERROR
        else:
            return EvidenceStatus.FAIL

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in file paths.

        Removes or replaces characters that are problematic in paths.

        Args:
            name: Raw name string

        Returns:
            Sanitized name safe for file paths
        """
        # Replace common path separators and special chars
        sanitized = name.replace("/", "_").replace("\\", "_").replace(":", "_")
        sanitized = sanitized.replace(" ", "_").replace(".", "_")
        # Remove leading/trailing underscores
        return sanitized.strip("_") or "unnamed"
