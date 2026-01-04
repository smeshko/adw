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
            # Use configured name if available, fall back to command binary
            if result.name:
                # Sanitize same way as EvidenceFileWriter
                name = self._sanitize_cli_name(result.name)
            else:
                # Legacy fallback for results without name field
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
            # Sanitize same way as APIEvidenceWriter._sanitize_filename
            safe_name = self._sanitize_api_filename(name)
            path = f"api/{safe_name}.json"

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
            # Mobile screenshots go to mobile/ directory, not screenshots/
            # Use relative path from result if available
            if result.path:
                try:
                    # Try to get relative path from evidence directory
                    path = str(result.path.relative_to(self.evidence_directory))
                except ValueError:
                    # If path is not under evidence_directory, use mobile/<filename>
                    path = f"mobile/{result.path.name}"
            else:
                path = f"mobile/{name}.png"

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

    def _sanitize_cli_name(self, name: str) -> str:
        """Sanitize CLI config name to match EvidenceFileWriter.

        Uses the same regex sanitization as EvidenceFileWriter.write_command_result.

        Args:
            name: Config name for the command

        Returns:
            Sanitized name safe for filenames
        """
        # Match EvidenceFileWriter: re.sub(r"[^\w\-]", "_", name)
        return re.sub(r"[^\w\-]", "_", name)

    def _sanitize_api_filename(self, name: str) -> str:
        """Sanitize API endpoint name to match APIEvidenceWriter.

        Uses the same sanitization as APIEvidenceWriter._sanitize_filename.

        Args:
            name: Endpoint name (e.g., "GET /health")

        Returns:
            Sanitized name safe for filenames
        """
        # Match APIEvidenceWriter._sanitize_filename
        safe = re.sub(r"[/\\:*?\"<>|]", "_", name)
        safe = safe.strip("_")
        safe = re.sub(r"_+", "_", safe)
        return safe if safe else "unnamed"


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


class EvidenceDirectoryScanner:
    """Scans evidence directory to collect captured files.

    Discovers evidence files from an evidence directory structure
    and creates EvidenceItem objects for each file found.

    The expected directory structure is:
        evidence/
        ├── cli/
        │   ├── *.txt (command output files)
        │   └── summary.json
        ├── screenshots/
        │   ├── *.png (screenshot files)
        │   └── metadata.json
        ├── api/
        │   ├── *.json (API response files)
        │   └── summary.json
        └── mobile/
            ├── *.png (mobile screenshot files)
            └── metadata.json

    Example:
        >>> scanner = EvidenceDirectoryScanner(Path(".adw/runs/01HQ/evidence"))
        >>> items = scanner.scan()
    """

    # File extension to evidence type mapping
    TYPE_MAPPINGS = {
        "cli": EvidenceType.CLI,
        "screenshots": EvidenceType.SCREENSHOT,
        "api": EvidenceType.API,
        "mobile": EvidenceType.SCREENSHOT,
        "logs": EvidenceType.LOG,
    }

    # Extensions for evidence files (not metadata)
    EVIDENCE_EXTENSIONS = {".txt", ".png", ".jpg", ".jpeg", ".json", ".log"}

    # Files to skip (metadata files)
    SKIP_FILES = {"summary.json", "metadata.json"}

    def __init__(self, evidence_directory: Path) -> None:
        """Initialize the evidence directory scanner.

        Args:
            evidence_directory: Path to the evidence directory
        """
        self.evidence_directory = evidence_directory
        self._logger = get_logger()

    def scan(self) -> list[EvidenceItem]:
        """Scan the evidence directory for captured files.

        Walks the directory structure, categorizes files by type,
        and creates EvidenceItem objects.

        Returns:
            List of EvidenceItem objects for each evidence file
        """
        if not self.evidence_directory.exists():
            self._logger.warn(
                LogCategory.STATE,
                f"Evidence directory does not exist: {self.evidence_directory}",
            )
            return []

        items: list[EvidenceItem] = []

        # Scan each subdirectory
        for subdir in self.evidence_directory.iterdir():
            if not subdir.is_dir():
                continue

            subdir_name = subdir.name.lower()
            evidence_type = self.TYPE_MAPPINGS.get(subdir_name)

            if evidence_type is None:
                self._logger.debug(
                    LogCategory.STATE,
                    f"Skipping unknown evidence subdirectory: {subdir_name}",
                )
                continue

            # Scan files in this subdirectory
            subdir_items = self._scan_directory(subdir, evidence_type)
            items.extend(subdir_items)

        self._logger.info(
            LogCategory.STATE,
            f"Scanned evidence directory: found {len(items)} evidence files",
        )

        return items

    def _scan_directory(
        self,
        directory: Path,
        evidence_type: EvidenceType,
    ) -> list[EvidenceItem]:
        """Scan a specific evidence subdirectory.

        Args:
            directory: Path to the subdirectory
            evidence_type: Type of evidence in this directory

        Returns:
            List of EvidenceItem objects
        """
        items: list[EvidenceItem] = []

        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue

            # Skip metadata files
            if file_path.name in self.SKIP_FILES:
                continue

            # Check extension
            if file_path.suffix.lower() not in self.EVIDENCE_EXTENSIONS:
                continue

            # Create relative path from evidence directory
            relative_path = file_path.relative_to(self.evidence_directory)

            # Generate name from filename (without extension)
            name = file_path.stem

            # Determine status from file content if possible
            status = self._determine_status(file_path, evidence_type)

            items.append(
                EvidenceItem(
                    name=name,
                    type=evidence_type,
                    path=str(relative_path),
                    status=status,
                    plan_step=None,  # Set by plan step linking
                    details=self._extract_details(file_path, evidence_type),
                )
            )

        return items

    def _determine_status(
        self,
        file_path: Path,
        evidence_type: EvidenceType,
    ) -> EvidenceStatus:
        """Determine evidence status from file content.

        For JSON files, looks for status/success fields.
        For other files, checks if they exist and have content.

        Args:
            file_path: Path to the evidence file
            evidence_type: Type of evidence

        Returns:
            EvidenceStatus based on file content
        """
        import json

        try:
            # Check file exists and has content
            if not file_path.exists() or file_path.stat().st_size == 0:
                return EvidenceStatus.ERROR

            # For JSON files, try to parse and check for status fields
            if file_path.suffix.lower() == ".json":
                try:
                    content = json.loads(file_path.read_text(encoding="utf-8"))
                    if isinstance(content, dict):
                        # Check various status field patterns
                        if content.get("success") is False:
                            return EvidenceStatus.FAIL
                        if content.get("error"):
                            return EvidenceStatus.ERROR
                        if content.get("status") == "fail":
                            return EvidenceStatus.FAIL
                        if content.get("exit_code", 0) != 0:
                            return EvidenceStatus.FAIL
                except json.JSONDecodeError:
                    return EvidenceStatus.ERROR

            # For images, existence with content = success
            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                return EvidenceStatus.PASS

            # For text files, check for error indicators
            if file_path.suffix.lower() == ".txt":
                content = file_path.read_text(encoding="utf-8", errors="replace")
                # Simple heuristic: check for error patterns
                error_patterns = ["error:", "failed:", "exception:", "traceback"]
                content_lower = content.lower()
                for pattern in error_patterns:
                    if pattern in content_lower:
                        return EvidenceStatus.FAIL

            return EvidenceStatus.PASS

        except OSError:
            return EvidenceStatus.ERROR

    def _extract_details(
        self,
        file_path: Path,
        evidence_type: EvidenceType,
    ) -> dict[str, str | int | float] | None:
        """Extract details from evidence file.

        Args:
            file_path: Path to the evidence file
            evidence_type: Type of evidence

        Returns:
            Dictionary of details, or None if no details available
        """
        import json

        details: dict[str, str | int | float] = {
            "file_size": file_path.stat().st_size,
        }

        # For JSON files, extract key metadata
        if file_path.suffix.lower() == ".json":
            try:
                content = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(content, dict):
                    # Extract common fields
                    for key in ["status_code", "method", "exit_code", "duration_seconds"]:
                        if key in content:
                            details[key] = content[key]
            except (json.JSONDecodeError, OSError):
                pass

        # For images, get dimensions if possible
        if file_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            # We don't want to import PIL just for this
            details["format"] = file_path.suffix[1:].upper()

        return details if len(details) > 1 else None


class ManifestWriter:
    """Writes evidence manifests to JSON files.

    Handles serialization and file writing for evidence manifests,
    including validation and pretty-printing.

    Example:
        >>> writer = ManifestWriter(Path(".adw/runs/01HQ/evidence"))
        >>> path = writer.write(manifest)
    """

    DEFAULT_FILENAME = "manifest.json"

    def __init__(self, evidence_directory: Path) -> None:
        """Initialize the manifest writer.

        Args:
            evidence_directory: Path to the evidence directory
        """
        self.evidence_directory = evidence_directory
        self._logger = get_logger()

    def write(
        self,
        manifest: EvidenceManifest,
        filename: str | None = None,
    ) -> Path:
        """Write manifest to JSON file.

        Serializes the manifest to pretty-printed JSON and writes
        it to the evidence directory.

        Args:
            manifest: Evidence manifest to write
            filename: Optional custom filename (default: manifest.json)

        Returns:
            Path to the written manifest file

        Raises:
            OSError: If unable to write the file
        """
        filename = filename or self.DEFAULT_FILENAME
        output_path = self.evidence_directory / filename

        # Validate manifest before writing
        self._validate_manifest(manifest)

        # Ensure evidence directory exists
        self.evidence_directory.mkdir(parents=True, exist_ok=True)

        # Serialize with custom datetime handling
        json_content = manifest.model_dump_json(indent=2)

        # Write atomically using temporary file
        temp_path = output_path.with_suffix(".tmp")
        try:
            temp_path.write_text(json_content, encoding="utf-8")
            temp_path.rename(output_path)
        except OSError:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

        self._logger.info(
            LogCategory.STATE,
            f"Manifest written to {output_path} "
            f"({manifest.total_items} items, {len(json_content)} bytes)",
        )

        return output_path

    def _validate_manifest(self, manifest: EvidenceManifest) -> None:
        """Validate manifest structure before writing.

        Checks that required fields are present and statistics are consistent.

        Args:
            manifest: Manifest to validate

        Raises:
            ValueError: If manifest is invalid
        """
        # Check required fields
        if not manifest.run_id:
            raise ValueError("Manifest missing required field: run_id")
        if not manifest.platform:
            raise ValueError("Manifest missing required field: platform")
        if not manifest.evidence_directory:
            raise ValueError("Manifest missing required field: evidence_directory")

        # Validate statistics consistency
        expected_total = (
            manifest.passed + manifest.failed + manifest.errors + manifest.skipped
        )
        if manifest.total_items != expected_total:
            self._logger.warn(
                LogCategory.STATE,
                f"Manifest statistics inconsistent: total_items={manifest.total_items} "
                f"but passed+failed+errors+skipped={expected_total}",
            )

        # Validate item count matches total
        if len(manifest.items) != manifest.total_items:
            self._logger.warn(
                LogCategory.STATE,
                f"Manifest item count inconsistent: items list has {len(manifest.items)} "
                f"but total_items={manifest.total_items}",
            )

        # Validate coverage if present
        if manifest.coverage:
            total = manifest.coverage.total_plan_steps
            covered = manifest.coverage.covered_steps
            uncovered = manifest.coverage.uncovered_steps

            if covered + uncovered != total:
                self._logger.warn(
                    LogCategory.STATE,
                    f"Coverage statistics inconsistent: covered={covered} + "
                    f"uncovered={uncovered} != total={total}",
                )

    def read(self, filename: str | None = None) -> EvidenceManifest | None:
        """Read an existing manifest from file.

        Args:
            filename: Optional custom filename (default: manifest.json)

        Returns:
            EvidenceManifest if file exists and is valid, None otherwise
        """
        import json

        filename = filename or self.DEFAULT_FILENAME
        manifest_path = self.evidence_directory / filename

        if not manifest_path.exists():
            self._logger.debug(
                LogCategory.STATE,
                f"Manifest file not found: {manifest_path}",
            )
            return None

        try:
            content = manifest_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return EvidenceManifest.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            self._logger.warn(
                LogCategory.STATE,
                f"Failed to parse manifest file: {e}",
            )
            return None
