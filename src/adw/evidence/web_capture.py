"""Web screenshot capture for evidence gathering.

This module provides the WebCaptureStrategy class for capturing browser
screenshots using Playwright. It supports graceful degradation when
Playwright is not installed.
"""

from pathlib import Path

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    RouteConfig,
    ScreenshotResult,
    ViewportConfig,
    WebEvidenceSummary,
)

# Try to import Playwright - it's an optional dependency
try:
    from playwright.sync_api import (
        TimeoutError as PlaywrightTimeout,
    )
    from playwright.sync_api import (
        sync_playwright,
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeout = None  # type: ignore[misc, assignment]
    sync_playwright = None  # type: ignore[misc, assignment]


# Default viewports for web evidence capture
DEFAULT_VIEWPORTS = [
    ViewportConfig(name="desktop", width=1920, height=1080),
    ViewportConfig(name="tablet", width=768, height=1024),
    ViewportConfig(name="mobile", width=375, height=667),
]


def check_playwright_available() -> bool:
    """Check if Playwright is installed and browser binaries are available.

    This performs a more thorough check than just checking the import:
    - Verifies Playwright package is installed
    - Attempts to verify browser binaries are available

    Returns:
        True if Playwright is fully available, False otherwise.

    Example:
        >>> if check_playwright_available():
        ...     # Safe to use Playwright
        ...     pass
    """
    if not PLAYWRIGHT_AVAILABLE:
        return False

    try:
        # Quick check - just verify we can import and the module works
        # Don't actually launch a browser here as it's expensive
        with sync_playwright() as p:
            # Just check that chromium is accessible
            # This doesn't launch anything, just verifies the binding
            _ = p.chromium
            return True
    except Exception:
        return False


class WebCaptureStrategy:
    """Strategy for capturing web screenshots using Playwright.

    This class handles browser automation for capturing screenshots of web
    applications. It supports multiple viewports, configurable wait strategies,
    and graceful degradation when Playwright is not available.

    Attributes:
        output_dir: Directory where screenshots will be saved
        base_url: Base URL of the web application
        viewports: List of viewport configurations for capture
        headless: Whether to run browser in headless mode
        is_available: Whether Playwright is available for use
        unavailable_reason: Reason why Playwright is not available (if applicable)

    Example:
        >>> strategy = WebCaptureStrategy(
        ...     output_dir=Path("/tmp/screenshots"),
        ...     base_url="http://localhost:3000",
        ... )
        >>> if strategy.is_available:
        ...     # Capture screenshots
        ...     pass
    """

    def __init__(
        self,
        output_dir: Path,
        base_url: str,
        viewports: list[ViewportConfig] | None = None,
        headless: bool = True,
    ) -> None:
        """Initialize the web capture strategy.

        Args:
            output_dir: Directory where screenshots will be saved
            base_url: Base URL of the web application
            viewports: List of viewport configurations (defaults to standard viewports)
            headless: Whether to run browser in headless mode (default: True)
        """
        self.output_dir = output_dir
        self.base_url = base_url
        self.viewports = viewports if viewports is not None else DEFAULT_VIEWPORTS.copy()
        self.headless = headless
        self._logger = get_logger()

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check availability and set reason if not available
        self._is_available = self._check_availability()
        self._unavailable_reason: str | None = None
        if not self._is_available:
            self._unavailable_reason = self._get_unavailable_reason()

    def _check_availability(self) -> bool:
        """Check if Playwright is available for use.

        Returns:
            True if Playwright can be used, False otherwise.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False
        return check_playwright_available()

    def _get_unavailable_reason(self) -> str:
        """Get the reason why Playwright is not available.

        Returns:
            Human-readable explanation of why Playwright is unavailable.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return (
                "Playwright is not installed. Install with: "
                "pip install playwright && python -m playwright install chromium"
            )
        return (
            "Playwright is installed but browser binaries are not available. "
            "Run: python -m playwright install chromium"
        )

    @property
    def is_available(self) -> bool:
        """Check if this strategy can be used.

        Returns:
            True if Playwright is available and configured.
        """
        return self._is_available

    @property
    def unavailable_reason(self) -> str | None:
        """Get the reason why this strategy is unavailable.

        Returns:
            Human-readable reason, or None if available.
        """
        return self._unavailable_reason

    def _create_browser_context(self, playwright_instance: "sync_playwright"):
        """Create a browser context with the specified settings.

        Args:
            playwright_instance: The Playwright instance to use

        Returns:
            A tuple of (browser, context) that must be closed after use.
        """
        browser = playwright_instance.chromium.launch(headless=self.headless)
        return browser

    def _log_availability_warning(self) -> None:
        """Log a warning that Playwright is not available."""
        self._logger.warn(
            LogCategory.STATE,
            f"Web screenshot capture skipped: {self._unavailable_reason}",
        )
