"""Evidence gathering package for ADW.

This package contains modules for:
- Platform detection (determining if project is CLI, WEB, MOBILE, or BACKEND)
- Evidence capture strategies (terminal output, screenshots, API responses)
- CLI evidence gathering (command execution and output capture)
- Web evidence gathering (browser screenshots)
- Mobile screenshot capture (iOS Simulator, Android Emulator, Flutter)
"""

from pathlib import Path

from adw.evidence.cli_capture import CLICaptureStrategy
from adw.evidence.cli_gatherer import CLIEvidenceGatherer
from adw.evidence.config_loader import load_evidence_commands
from adw.evidence.detector import PlatformDetector
from adw.evidence.file_writer import EvidenceFileWriter
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
    EvidenceStrategy,
    MobileDeviceType,
    MobileEvidenceSummary,
    MobileScreenConfig,
    MobileScreenshotResult,
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


__all__ = [
    # Platform detection
    "PlatformDetector",
    "detect_platform",
    "get_evidence_strategy",
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
