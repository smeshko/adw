"""Evidence manifest generator for ADW.

This module provides the ManifestGenerator class for creating evidence
manifests that link captured evidence to plan steps for traceability
and coverage analysis.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Union

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    APIEvidenceResult,
    APIEvidenceSummary,
    CLIEvidenceSummary,
    CommandResult,
    CoverageSummary,
    EvidenceItem,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceType,
    MobileEvidenceSummary,
    MobileScreenshotResult,
    PlanStepCoverage,
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


class PlanStepLinker:
    """Links evidence items to plan steps.

    Parses plan.md files to extract step definitions and uses
    heuristics to link evidence items to their corresponding
    plan steps for coverage analysis.

    Example:
        >>> linker = PlanStepLinker(plan_path=Path(".adw/plan.md"))
        >>> manifest = linker.link_steps(manifest)
    """

    # Patterns for extracting plan steps from markdown
    STEP_PATTERNS = [
        # "## Step 1: Description" or "## Step 1 - Description"
        re.compile(r"^##\s+Step\s+(\d+)[:\s-]+\s*(.+)$", re.IGNORECASE),
        # "### 1.1 Description" (numbered sub-steps)
        re.compile(r"^###\s+(\d+\.\d+)\s+(.+)$"),
        # "### Task 1: Description"
        re.compile(r"^###\s+Task\s+(\d+)[:\s-]+\s*(.+)$", re.IGNORECASE),
        # "- [ ] Checkbox task"
        re.compile(r"^-\s+\[.\]\s+(.+)$"),
    ]

    def __init__(
        self,
        plan_path: Path | None = None,
        explicit_links: dict[str, str] | None = None,
    ) -> None:
        """Initialize the plan step linker.

        Args:
            plan_path: Path to plan.md file (optional)
            explicit_links: Dict mapping evidence names to step IDs
                            for explicit linking configuration
        """
        self.plan_path = plan_path
        self.explicit_links = explicit_links or {}
        self._logger = get_logger()
        self._plan_steps: list[tuple[str, str]] = []

    def parse_plan_steps(self) -> list[tuple[str, str]]:
        """Parse plan.md to extract step IDs and descriptions.

        Returns:
            List of (step_id, description) tuples

        Example:
            >>> linker = PlanStepLinker(Path("plan.md"))
            >>> steps = linker.parse_plan_steps()
            >>> steps[0]
            ('step_1', 'Implement health check endpoint')
        """
        if self._plan_steps:
            return self._plan_steps

        if not self.plan_path or not self.plan_path.exists():
            self._logger.debug(
                LogCategory.STATE,
                "No plan.md file found - skipping plan step parsing",
            )
            return []

        try:
            content = self.plan_path.read_text(encoding="utf-8")
        except OSError as e:
            self._logger.warn(
                LogCategory.STATE,
                f"Failed to read plan.md: {e}",
            )
            return []

        steps: list[tuple[str, str]] = []
        task_counter = 0

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            for pattern in self.STEP_PATTERNS:
                match = pattern.match(line)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        # Numbered step pattern
                        step_num, description = groups
                        step_id = f"step_{step_num.replace('.', '_')}"
                    else:
                        # Checkbox task pattern
                        task_counter += 1
                        description = groups[0]
                        step_id = f"task_{task_counter}"

                    steps.append((step_id, description))
                    break

        self._plan_steps = steps
        self._logger.info(
            LogCategory.STATE,
            f"Parsed {len(steps)} plan steps from {self.plan_path}",
        )

        return steps

    def link_evidence_to_step(
        self,
        evidence_name: str,
        plan_steps: list[tuple[str, str]] | None = None,
    ) -> str | None:
        """Attempt to link an evidence item to a plan step.

        Uses the following priority:
        1. Explicit configuration (if provided)
        2. Keyword matching between evidence name and step descriptions

        Args:
            evidence_name: Name of the evidence item
            plan_steps: Optional list of (step_id, description) tuples

        Returns:
            Step ID if linked, None otherwise
        """
        # Check explicit links first
        if evidence_name in self.explicit_links:
            return self.explicit_links[evidence_name]

        # Fall back to heuristic matching
        steps = plan_steps or self.parse_plan_steps()
        if not steps:
            return None

        evidence_lower = evidence_name.lower()
        evidence_words = set(self._tokenize(evidence_lower))

        best_match: str | None = None
        best_score = 0

        for step_id, description in steps:
            desc_lower = description.lower()
            desc_words = set(self._tokenize(desc_lower))

            # Score by word overlap
            overlap = evidence_words & desc_words
            if overlap:
                score = len(overlap)
                # Bonus for exact substring match
                if evidence_lower in desc_lower or desc_lower in evidence_lower:
                    score += 5

                if score > best_score:
                    best_score = score
                    best_match = step_id

        return best_match

    def link_steps(self, manifest: EvidenceManifest) -> EvidenceManifest:
        """Link all evidence items in a manifest to plan steps.

        Updates evidence items with plan_step references and
        calculates coverage statistics.

        Args:
            manifest: Evidence manifest to process

        Returns:
            Updated manifest with plan_step links and coverage
        """
        plan_steps = self.parse_plan_steps()

        # Link each evidence item
        linked_items: list[EvidenceItem] = []
        for item in manifest.items:
            step_id = self.link_evidence_to_step(item.name, plan_steps)
            if step_id and step_id != item.plan_step:
                # Create new item with updated plan_step
                linked_item = EvidenceItem(
                    name=item.name,
                    type=item.type,
                    path=item.path,
                    status=item.status,
                    plan_step=step_id,
                    details=item.details,
                )
                linked_items.append(linked_item)
            else:
                linked_items.append(item)

        # Calculate coverage if we have plan steps
        coverage = None
        step_coverage = None

        if plan_steps:
            coverage, step_coverage = self._calculate_coverage(
                plan_steps, linked_items
            )

        # Return updated manifest
        return EvidenceManifest(
            run_id=manifest.run_id,
            generated_at=manifest.generated_at,
            platform=manifest.platform,
            evidence_directory=manifest.evidence_directory,
            total_items=manifest.total_items,
            passed=manifest.passed,
            failed=manifest.failed,
            errors=manifest.errors,
            skipped=manifest.skipped,
            items=linked_items,
            coverage=coverage,
            step_coverage=step_coverage,
        )

    def _calculate_coverage(
        self,
        plan_steps: list[tuple[str, str]],
        items: list[EvidenceItem],
    ) -> tuple[CoverageSummary, list[PlanStepCoverage]]:
        """Calculate coverage statistics.

        Args:
            plan_steps: List of (step_id, description) tuples
            items: List of evidence items with plan_step links

        Returns:
            Tuple of (CoverageSummary, list[PlanStepCoverage])
        """
        # Build step coverage map
        step_items: dict[str, list[str]] = {
            step_id: [] for step_id, _ in plan_steps
        }

        for item in items:
            if item.plan_step and item.plan_step in step_items:
                step_items[item.plan_step].append(item.name)

        # Build PlanStepCoverage list
        step_coverage_list: list[PlanStepCoverage] = []
        covered_count = 0
        uncovered_ids: list[str] = []

        for step_id, description in plan_steps:
            evidence_items = step_items.get(step_id, [])
            covered = len(evidence_items) > 0

            if covered:
                covered_count += 1
            else:
                uncovered_ids.append(step_id)

            step_coverage_list.append(
                PlanStepCoverage(
                    step_id=step_id,
                    step_description=description,
                    evidence_items=evidence_items,
                    covered=covered,
                )
            )

        # Calculate summary
        total = len(plan_steps)
        uncovered = total - covered_count
        percentage = (covered_count / total * 100) if total > 0 else 100.0

        coverage_summary = CoverageSummary(
            total_plan_steps=total,
            covered_steps=covered_count,
            uncovered_steps=uncovered,
            coverage_percentage=round(percentage, 1),
            uncovered_step_ids=uncovered_ids,
        )

        self._logger.info(
            LogCategory.STATE,
            f"Plan coverage: {covered_count}/{total} steps "
            f"({coverage_summary.coverage_percentage}%)",
        )

        return coverage_summary, step_coverage_list

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words for matching.

        Splits on common separators and filters short tokens.

        Args:
            text: Text to tokenize

        Returns:
            List of word tokens
        """
        # Split on common separators
        words = re.split(r"[_\-\s/]+", text)
        # Filter short tokens and common words
        stop_words = {"the", "a", "an", "and", "or", "to", "in", "for", "of"}
        return [w for w in words if len(w) > 2 and w not in stop_words]
