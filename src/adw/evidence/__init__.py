"""Evidence gathering package for ADW.

This package contains modules for:
- Platform detection (determining if project is CLI, WEB, MOBILE, or BACKEND)
- Evidence capture strategies (terminal output, screenshots, API responses)
"""

from pathlib import Path

from adw.evidence.api_capture import APICaptureStrategy
from adw.evidence.detector import PlatformDetector
from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    EvidenceStrategy,
    PlatformDetectionResult,
    PlatformType,
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
    "APICaptureStrategy",
    "PlatformDetector",
    "detect_platform",
    "get_evidence_strategy",
]
