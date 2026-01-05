"""Evidence gathering package for ADW.

This package contains modules for:
- Platform detection (determining if project is CLI, WEB, MOBILE, or BACKEND)
- Evidence capture strategies (terminal output, screenshots, API responses)
- CLI evidence gathering (command execution and output capture)
- Web evidence gathering (browser screenshots)
- Mobile screenshot capture (iOS Simulator, Android Emulator, Flutter)
"""

from pathlib import Path
from typing import TYPE_CHECKING

from adw.evidence.cli_capture import CLICaptureStrategy
from adw.evidence.cli_gatherer import CLIEvidenceGatherer
from adw.evidence.config_loader import (
    EvidenceConfig,
    load_evidence_commands,
    load_evidence_config,
    load_optimization_config,
)
from adw.evidence.detector import PlatformDetector
from adw.evidence.file_writer import EvidenceFileWriter
from adw.evidence.manifest import (
    EvidenceDirectoryScanner,
    EvidenceSummary,  # Union type alias
    ManifestGenerator,
    ManifestWriter,
    PlanStepLinker,
)

# Re-export for type annotation usage
__EvidenceSummary = EvidenceSummary
from adw.evidence.optimizer import (
    PILLOW_AVAILABLE,
    EvidenceOptimizer,
)

# API capture requires httpx (optional dependency)
try:
    from adw.evidence.api_capture import (
        HTTPX_AVAILABLE,
        APICaptureStrategy,
        generate_summary,
    )
    from adw.evidence.evidence_writer import APIEvidenceWriter
except ImportError:
    HTTPX_AVAILABLE = False
    APICaptureStrategy = None  # type: ignore[assignment,misc]
    generate_summary = None  # type: ignore[assignment]
    APIEvidenceWriter = None  # type: ignore[assignment,misc]
    if TYPE_CHECKING:
        from adw.evidence.api_capture import APICaptureStrategy, generate_summary
        from adw.evidence.evidence_writer import APIEvidenceWriter
from adw.evidence.mobile_capture import (
    capture_android_screenshot,
    capture_configured_screens,
    capture_flutter_screenshot,
    capture_ios_screenshot,
    check_android_emulator_available,
    check_ios_simulator_available,
    detect_flutter_device,
    get_booted_simulator,
    get_running_emulator,
    load_mobile_screens_config,
    navigate_android_deeplink,
    navigate_ios_deeplink,
    save_evidence_metadata,
)
from adw.evidence.summary_generator import SummaryGenerator
from adw.evidence.web_capture import (
    DEFAULT_VIEWPORTS,
    WebCaptureStrategy,
    check_playwright_available,
    create_evidence_directory,
    generate_evidence_metadata,
    load_routes_from_config,
)
from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    CLIEvidenceSummary,
    CommandConfig,
    CommandResult,
    CoverageSummary,
    EvidenceItem,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceStrategy,
    EvidenceType,
    FileOptimization,
    MobileDeviceType,
    MobileEvidenceSummary,
    MobileScreenConfig,
    MobileScreenshotResult,
    OptimizationConfig,
    OptimizationReport,
    PlanStepCoverage,
    PlatformDetectionResult,
    PlatformType,
    RouteConfig,
    ScreenshotResult,
    ViewportConfig,
    WebEvidenceSummary,
)


def detect_platform(project_root: Path) -> PlatformDetectionResult:
    """Detect the platform type for a project.

    This is a convenience function that creates a PlatformDetector
    and runs detection.

    Args:
        project_root: Path to the project root directory

    Returns:
        PlatformDetectionResult with detected platform and metadata

    Example:
        >>> from pathlib import Path
        >>> result = detect_platform(Path("/my/project"))
        >>> result.platform
        <PlatformType.WEB: 'web'>
    """
    detector = PlatformDetector(project_root)
    return detector.detect()


def get_evidence_strategy(platform: PlatformType) -> EvidenceStrategy:
    """Get the appropriate evidence strategy for a platform type.

    Maps platform types to evidence gathering strategies:
    - CLI -> TERMINAL_OUTPUT: Capture stdout/stderr
    - WEB -> SCREENSHOT: Capture browser screenshots
    - MOBILE -> SCREENSHOT: Capture device/simulator screenshots
    - BACKEND -> API_CAPTURE: Capture HTTP request/response pairs
    - UNKNOWN -> TERMINAL_OUTPUT: Default with warning

    Args:
        platform: The detected platform type

    Returns:
        The appropriate EvidenceStrategy for the platform

    Example:
        >>> from adw.models.evidence import PlatformType
        >>> strategy = get_evidence_strategy(PlatformType.WEB)
        >>> strategy
        <EvidenceStrategy.SCREENSHOT: 'screenshot'>
    """
    logger = get_logger()

    strategy_map = {
        PlatformType.CLI: EvidenceStrategy.TERMINAL_OUTPUT,
        PlatformType.WEB: EvidenceStrategy.SCREENSHOT,
        PlatformType.MOBILE: EvidenceStrategy.SCREENSHOT,
        PlatformType.BACKEND: EvidenceStrategy.API_CAPTURE,
        PlatformType.UNKNOWN: EvidenceStrategy.TERMINAL_OUTPUT,
    }

    strategy = strategy_map[platform]

    if platform == PlatformType.UNKNOWN:
        logger.warn(
            LogCategory.STATE,
            "Platform could not be determined - defaulting to terminal output "
            "strategy. Add 'platform: cli|web|mobile|backend' to .adw/project.yaml",
        )

    return strategy


def generate_evidence_manifest(
    run_id: str,
    platform: str,
    evidence_directory: Path,
    summaries: list[EvidenceSummary] | None = None,
    plan_path: Path | None = None,
    explicit_links: dict[str, str] | None = None,
) -> "EvidenceManifest":
    """Generate a complete evidence manifest for a run.

    This is the main integration point for manifest generation during
    the Verify phase. It combines:
    - ManifestGenerator for creating the manifest from summaries
    - PlanStepLinker for linking evidence to plan steps
    - ManifestWriter for persisting to disk

    Args:
        run_id: Unique identifier for the run (ULID)
        platform: Detected platform type (cli, web, backend, etc.)
        evidence_directory: Path to the evidence directory
        summaries: Optional list of evidence summaries from capture strategies.
                   If None, will scan the evidence directory for files.
        plan_path: Optional path to plan.md for step linking
        explicit_links: Optional dict mapping evidence names to step IDs

    Returns:
        EvidenceManifest with all evidence items and coverage data

    Example:
        >>> from adw.evidence import generate_evidence_manifest
        >>> manifest = generate_evidence_manifest(
        ...     run_id="01HQ...",
        ...     platform="backend",
        ...     evidence_directory=Path(".adw/runs/01HQ/evidence"),
        ...     summaries=[cli_summary, api_summary],
        ...     plan_path=Path(".adw/plan.md"),
        ... )
    """
    logger = get_logger()

    # Generate manifest from summaries or scan directory
    if summaries:
        generator = ManifestGenerator(
            run_id=run_id,
            platform=platform,
            evidence_directory=evidence_directory,
        )
        manifest = generator.generate(summaries)
    else:
        # Scan directory for evidence files
        scanner = EvidenceDirectoryScanner(evidence_directory)
        items = scanner.scan()

        # Calculate statistics
        passed = sum(1 for i in items if i.status == EvidenceStatus.PASS)
        failed = sum(1 for i in items if i.status == EvidenceStatus.FAIL)
        errors = sum(1 for i in items if i.status == EvidenceStatus.ERROR)
        skipped = sum(1 for i in items if i.status == EvidenceStatus.SKIPPED)

        manifest = EvidenceManifest(
            run_id=run_id,
            platform=platform,
            evidence_directory=str(evidence_directory),
            total_items=len(items),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            items=items,
        )

    # Link to plan steps if plan exists
    if plan_path and plan_path.exists():
        linker = PlanStepLinker(plan_path=plan_path, explicit_links=explicit_links)
        manifest = linker.link_steps(manifest)

    # Write manifest to file
    writer = ManifestWriter(evidence_directory)
    manifest_path = writer.write(manifest)

    logger.info(
        LogCategory.STATE,
        f"Evidence manifest generated: {manifest.total_items} items, "
        f"{manifest.passed} passed, {manifest.failed} failed. "
        f"Written to: {manifest_path}",
    )

    return manifest


def optimize_evidence(
    run_id: str,
    evidence_directory: Path,
    project_root: Path | None = None,
    config: "OptimizationConfig | None" = None,
) -> "OptimizationReport":
    """Optimize evidence files for storage and transfer.

    This is the main integration point for evidence optimization during
    the Verify phase. It should be called BEFORE manifest generation
    to ensure optimized file sizes are reflected in the manifest.

    Optimization includes:
    - Image compression (PNG/JPEG) using Pillow if available
    - Text file truncation with head/tail preservation
    - JSON minification

    Args:
        run_id: Unique identifier for the run (ULID)
        evidence_directory: Path to the evidence directory to optimize
        project_root: Optional project root for loading config from project.yaml.
                      If not provided, uses default OptimizationConfig.
        config: Optional explicit OptimizationConfig. Takes precedence over
                loading from project.yaml.

    Returns:
        OptimizationReport with complete optimization results

    Example:
        >>> from adw.evidence import optimize_evidence
        >>> report = optimize_evidence(
        ...     run_id="01HQ...",
        ...     evidence_directory=Path(".adw/runs/01HQ/evidence"),
        ...     project_root=Path("/my/project"),
        ... )
        >>> print(f"Saved {report.total_savings_bytes} bytes")
    """
    logger = get_logger()

    # Load config from project.yaml if not provided explicitly
    if config is None and project_root is not None:
        config = load_optimization_config(project_root)
    elif config is None:
        config = OptimizationConfig()

    # Check if optimization is enabled
    if not config.enabled:
        logger.info(
            LogCategory.STATE,
            "Evidence optimization disabled by configuration",
        )
        # Return empty report
        return OptimizationReport(
            run_id=run_id,
            total_files=0,
            files_optimized=0,
            files_skipped=0,
            original_total_bytes=0,
            optimized_total_bytes=0,
            total_savings_bytes=0,
            total_savings_percent=0.0,
        )

    # Create optimizer and run
    optimizer = EvidenceOptimizer(config=config)
    report = optimizer.optimize_directory(evidence_directory, run_id=run_id)

    # Write optimization report to evidence directory (Story 8.6)
    report_path = evidence_directory / "optimization_report.json"
    report_path.write_text(report.model_dump_json(indent=2))
    logger.debug(
        LogCategory.STATE,
        f"Optimization report written to {report_path}",
    )

    logger.info(
        LogCategory.STATE,
        f"Evidence optimization complete: {report.files_optimized}/"
        f"{report.total_files} files optimized, saved {report.total_savings_bytes:,} "
        f"bytes ({report.total_savings_percent:.1f}%)",
    )

    return report


__all__ = [
    # Platform detection
    "PlatformDetector",
    "detect_platform",
    "get_evidence_strategy",
    # Manifest generation (main integration point)
    "generate_evidence_manifest",
    "EvidenceSummary",
    # Evidence optimization
    "EvidenceOptimizer",
    "optimize_evidence",
    "load_optimization_config",
    "PILLOW_AVAILABLE",
    # Optimization models
    "FileOptimization",
    "OptimizationConfig",
    "OptimizationReport",
    # API evidence gathering (requires httpx)
    "HTTPX_AVAILABLE",
    "APIEvidenceWriter",
    "APICaptureStrategy",
    "EvidenceConfig",
    "generate_summary",
    "load_evidence_config",
    # CLI evidence gathering
    "CLICaptureStrategy",
    "CLIEvidenceGatherer",
    "EvidenceFileWriter",
    "SummaryGenerator",
    "load_evidence_commands",
    # CLI models
    "CLIEvidenceSummary",
    "CommandConfig",
    "CommandResult",
    # Manifest generation
    "EvidenceDirectoryScanner",
    "ManifestGenerator",
    "ManifestWriter",
    "PlanStepLinker",
    # Manifest models
    "CoverageSummary",
    "EvidenceItem",
    "EvidenceManifest",
    "EvidenceStatus",
    "EvidenceType",
    "PlanStepCoverage",
    # Web capture
    "DEFAULT_VIEWPORTS",
    "WebCaptureStrategy",
    "check_playwright_available",
    "create_evidence_directory",
    "generate_evidence_metadata",
    "load_routes_from_config",
    # Web models
    "RouteConfig",
    "ScreenshotResult",
    "ViewportConfig",
    "WebEvidenceSummary",
    # Mobile capture
    "capture_android_screenshot",
    "capture_configured_screens",
    "capture_flutter_screenshot",
    "capture_ios_screenshot",
    "check_android_emulator_available",
    "check_ios_simulator_available",
    "detect_flutter_device",
    "get_booted_simulator",
    "get_running_emulator",
    "load_mobile_screens_config",
    "navigate_android_deeplink",
    "navigate_ios_deeplink",
    "save_evidence_metadata",
    # Mobile models
    "MobileDeviceType",
    "MobileEvidenceSummary",
    "MobileScreenConfig",
    "MobileScreenshotResult",
]
