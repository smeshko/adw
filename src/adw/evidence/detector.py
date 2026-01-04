"""Platform detection for evidence gathering.

This module provides the PlatformDetector class that determines the
project platform type (CLI, WEB, BACKEND) from configuration or file markers.
"""

from pathlib import Path

import yaml

from adw.models.evidence import Confidence, PlatformDetectionResult, PlatformType


class PlatformDetector:
    """Detects the platform type for a project.

    The detector uses a priority-based approach:
    1. Explicit configuration in .adw/project.yaml (highest priority)
    2. File markers (package.json, pyproject.toml, etc.)
    3. Default to CLI with warning (lowest priority)

    Attributes:
        project_root: Path to the project root directory

    Example:
        >>> detector = PlatformDetector(Path("/path/to/project"))
        >>> result = detector.detect()
        >>> result.platform
        <PlatformType.WEB: 'web'>
    """

    CONFIG_FILE = ".adw/project.yaml"

    def __init__(self, project_root: Path) -> None:
        """Initialize the platform detector.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root

    def detect(self) -> PlatformDetectionResult:
        """Detect the platform type for the project.

        Attempts detection in priority order:
        1. Explicit config (returns immediately if found)
        2. File markers (analyzed for confidence scoring)
        3. Default to CLI with low confidence

        Returns:
            PlatformDetectionResult with detected platform and metadata
        """
        # Priority 1: Check explicit configuration
        config_result = self._detect_from_config()
        if config_result is not None:
            return config_result

        # Priority 2: Check file markers
        marker_result = self._detect_from_markers()
        if marker_result is not None:
            return marker_result

        # Priority 3: Default to CLI
        return self._get_default_result()

    def _detect_from_config(self) -> PlatformDetectionResult | None:
        """Attempt to detect platform from configuration file.

        Returns:
            PlatformDetectionResult if config specifies valid platform, None otherwise
        """
        config_path = self.project_root / self.CONFIG_FILE
        if not config_path.exists():
            return None

        try:
            content = config_path.read_text()
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return None

            platform_value = data.get("platform")
            if platform_value is None:
                return None

            # Normalize to lowercase for case-insensitive matching
            platform_str = str(platform_value).lower()

            # Validate against PlatformType enum
            try:
                platform = PlatformType(platform_str)
            except ValueError:
                # Invalid platform value - fall through to marker detection
                return None

            return PlatformDetectionResult(
                platform=platform,
                confidence=Confidence.HIGH,
                source="config",
                markers=[],
            )
        except (yaml.YAMLError, OSError):
            # Config file exists but couldn't be parsed - fall through
            return None

    def _detect_from_markers(self) -> PlatformDetectionResult | None:
        """Attempt to detect platform from file markers.

        This is a placeholder for Task 3 implementation.

        Returns:
            PlatformDetectionResult if markers found, None otherwise
        """
        # Will be implemented in Task 3
        return None

    def _get_default_result(self) -> PlatformDetectionResult:
        """Get the default platform detection result.

        Defaults to CLI platform with low confidence when no other
        detection method succeeds.

        Returns:
            PlatformDetectionResult with CLI platform and low confidence
        """
        return PlatformDetectionResult(
            platform=PlatformType.CLI,
            confidence=Confidence.LOW,
            source="default",
            markers=[],
        )
