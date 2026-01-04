"""Web screenshot capture for evidence gathering.

This module provides the WebCaptureStrategy class for capturing browser
screenshots using Playwright. It supports graceful degradation when
Playwright is not installed.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    RouteConfig,
    ScreenshotResult,
    ViewportConfig,
)

# Playwright is an optional dependency
PLAYWRIGHT_AVAILABLE = False
PlaywrightTimeout: type[Exception] = TimeoutError
sync_playwright: Callable[[], Any] | None = None

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout  # noqa: F811
    from playwright.sync_api import (
        sync_playwright,  # type: ignore[assignment]  # noqa: F811
    )

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


DEFAULT_VIEWPORTS: list[ViewportConfig] = [
    ViewportConfig(name="desktop", width=1920, height=1080),
    ViewportConfig(name="tablet", width=768, height=1024),
    ViewportConfig(name="mobile", width=375, height=667),
]
"""Default viewport configurations for web evidence capture.

Provides standard screen sizes for responsive testing:
- desktop: 1920x1080 (Full HD)
- tablet: 768x1024 (iPad portrait)
- mobile: 375x667 (iPhone SE)
"""

# Config file path
CONFIG_FILE = ".adw/project.yaml"


def load_routes_from_config(
    project_root: Path,
) -> tuple[list[RouteConfig], str, list[ViewportConfig]] | None:
    """Load route and viewport configuration from project config.

    Reads the evidence configuration section from .adw/project.yaml and
    returns parsed routes, base URL, and viewports.

    Args:
        project_root: Path to the project root directory

    Returns:
        Tuple of (routes, base_url, viewports) if config is valid,
        None if config doesn't exist or is invalid.

    Example:
        >>> result = load_routes_from_config(Path("/my/project"))
        >>> if result:
        ...     routes, base_url, viewports = result
        ...     print(f"Found {len(routes)} routes")
    """
    logger = get_logger()
    config_path = project_root / CONFIG_FILE

    # Check if config file exists
    if not config_path.exists():
        logger.debug(
            LogCategory.STATE,
            f"No config file found at {config_path}",
        )
        return None

    # Load and parse config
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.warn(
            LogCategory.STATE,
            f"Failed to parse config file {config_path}: {e}",
        )
        return None

    # Check for evidence section
    if not config or "evidence" not in config:
        logger.debug(
            LogCategory.STATE,
            "No 'evidence' section in project config",
        )
        return None

    evidence_config = config["evidence"]

    # Extract base_url (required)
    if "base_url" not in evidence_config:
        logger.warn(
            LogCategory.STATE,
            "Missing 'base_url' in evidence config",
        )
        return None

    base_url = evidence_config["base_url"]

    # Extract routes (required)
    if "routes" not in evidence_config or not evidence_config["routes"]:
        logger.warn(
            LogCategory.STATE,
            "Missing or empty 'routes' in evidence config",
        )
        return None

    # Parse routes
    routes: list[RouteConfig] = []
    try:
        for route_data in evidence_config["routes"]:
            route = RouteConfig.model_validate(route_data)
            routes.append(route)
    except ValidationError as e:
        logger.warn(
            LogCategory.STATE,
            f"Invalid route configuration: {e}",
        )
        return None

    # Parse viewports (optional, use defaults if not specified)
    viewports: list[ViewportConfig] = []
    if "viewports" in evidence_config and evidence_config["viewports"]:
        try:
            for viewport_data in evidence_config["viewports"]:
                viewport = ViewportConfig.model_validate(viewport_data)
                viewports.append(viewport)
        except ValidationError as e:
            logger.warn(
                LogCategory.STATE,
                f"Invalid viewport configuration: {e}",
            )
            return None
    else:
        viewports = DEFAULT_VIEWPORTS.copy()

    logger.debug(
        LogCategory.STATE,
        f"Loaded {len(routes)} routes and {len(viewports)} viewports from config",
    )

    return routes, base_url, viewports


def create_evidence_directory(project_root: Path, run_id: str) -> Path:
    """Create the evidence directory for a run.

    Creates the directory structure for storing web screenshots:
    .adw/runs/<run_id>/evidence/screenshots/

    Args:
        project_root: Path to the project root directory
        run_id: Unique identifier for the run

    Returns:
        Path to the created screenshots directory.

    Example:
        >>> evidence_dir = create_evidence_directory(Path("/my/project"), "01HQ...")
        >>> str(evidence_dir)
        '/my/project/.adw/runs/01HQ.../evidence/screenshots'
    """
    evidence_dir = project_root / ".adw" / "runs" / run_id / "evidence" / "screenshots"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir


def generate_evidence_metadata(
    results: list[ScreenshotResult],
    base_url: str,
) -> dict[str, Any]:
    """Generate metadata for captured screenshots.

    Creates a dictionary suitable for serialization to JSON with summary
    information and details about each screenshot.

    Args:
        results: List of screenshot capture results
        base_url: Base URL that was captured

    Returns:
        Dictionary with metadata about the evidence capture session.

    Example:
        >>> metadata = generate_evidence_metadata(results, "http://localhost:3000")
        >>> metadata["total_screenshots"]
        4
    """
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    screenshots = []
    for result in results:
        screenshot_info = {
            "path": str(result.path),
            "route": result.route,
            "viewport": result.viewport,
            "success": result.success,
            "captured_at": result.captured_at.isoformat(),
        }
        if result.error:
            screenshot_info["error"] = result.error
        screenshots.append(screenshot_info)

    return {
        "base_url": base_url,
        "total_screenshots": len(results),
        "successful": successful,
        "failed": failed,
        "screenshots": screenshots,
    }


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
    if not PLAYWRIGHT_AVAILABLE or sync_playwright is None:
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
        if viewports is not None:
            self.viewports = viewports
        else:
            self.viewports = DEFAULT_VIEWPORTS.copy()
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

    def _log_availability_warning(self) -> None:
        """Log a warning that Playwright is not available."""
        self._logger.warn(
            LogCategory.STATE,
            f"Web screenshot capture skipped: {self._unavailable_reason}",
        )

    def _generate_screenshot_path(
        self, route: RouteConfig, viewport: ViewportConfig
    ) -> Path:
        """Generate the output path for a screenshot.

        Args:
            route: Route configuration
            viewport: Viewport configuration

        Returns:
            Path where screenshot should be saved.
        """
        # Sanitize route name for filename
        safe_name = route.name.replace("/", "_").replace(" ", "_")
        filename = f"{safe_name}_{viewport.name}.png"
        return self.output_dir / filename

    def _generate_error_screenshot_path(
        self, route: RouteConfig, viewport: ViewportConfig
    ) -> Path:
        """Generate the output path for an error screenshot.

        Error screenshots have an _error suffix to distinguish them from
        successful captures.

        Args:
            route: Route configuration
            viewport: Viewport configuration

        Returns:
            Path where error screenshot should be saved.
        """
        # Sanitize route name for filename
        safe_name = route.name.replace("/", "_").replace(" ", "_")
        filename = f"{safe_name}_{viewport.name}_error.png"
        return self.output_dir / filename

    def _build_full_url(self, route: RouteConfig) -> str:
        """Build the full URL for a route.

        Args:
            route: Route configuration with path

        Returns:
            Full URL combining base_url and route path.
        """
        base = self.base_url.rstrip("/")
        path = route.path if route.path.startswith("/") else f"/{route.path}"
        return f"{base}{path}"

    def capture_route(
        self, route: RouteConfig, viewport: ViewportConfig
    ) -> ScreenshotResult:
        """Capture a screenshot of a single route at a specific viewport.

        This method navigates to the route URL, waits for the page to load
        according to the route's wait_for strategy, and captures a full-page
        screenshot.

        Args:
            route: Configuration for the route to capture
            viewport: Viewport dimensions for the screenshot

        Returns:
            ScreenshotResult with path, success status, and any error info.

        Example:
            >>> route = RouteConfig(name="home", path="/")
            >>> viewport = ViewportConfig(name="desktop", width=1920, height=1080)
            >>> result = strategy.capture_route(route, viewport)
            >>> result.success
            True
        """
        screenshot_path = self._generate_screenshot_path(route, viewport)
        viewport_str = f"{viewport.width}x{viewport.height}"
        full_url = self._build_full_url(route)

        # If Playwright is not available, return failure result
        if not self.is_available or sync_playwright is None:
            self._log_availability_warning()
            return ScreenshotResult(
                path=screenshot_path,
                route=route.name,
                viewport=viewport_str,
                success=False,
                error=f"Playwright not available: {self._unavailable_reason}",
            )

        # Capture with Playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": viewport.width, "height": viewport.height}
                )
                page = context.new_page()

                try:
                    # Navigate to the URL with configured wait strategy
                    page.goto(
                        full_url,
                        timeout=route.timeout_ms,
                        wait_until=route.wait_for,
                    )

                    # Take full-page screenshot
                    page.screenshot(path=str(screenshot_path), full_page=True)

                    self._logger.debug(
                        LogCategory.STATE,
                        f"Screenshot captured: {route.name} at {viewport_str}",
                    )

                    return ScreenshotResult(
                        path=screenshot_path,
                        route=route.name,
                        viewport=viewport_str,
                        success=True,
                    )

                except PlaywrightTimeout:
                    error_msg = (
                        f"Timeout waiting for page load: {full_url} "
                        f"(timeout: {route.timeout_ms}ms)"
                    )
                    self._logger.warn(LogCategory.STATE, error_msg)

                    # Capture error screenshot of current state
                    error_path = self._generate_error_screenshot_path(route, viewport)
                    try:
                        page.screenshot(path=str(error_path), full_page=True)
                        self._logger.debug(
                            LogCategory.STATE,
                            f"Error screenshot captured: {error_path}",
                        )
                    except Exception:
                        pass  # Best effort - don't fail if error screenshot fails

                    return ScreenshotResult(
                        path=error_path,
                        route=route.name,
                        viewport=viewport_str,
                        success=False,
                        error=error_msg,
                    )

                except Exception as e:
                    error_msg = f"Navigation failed: {e!s}"
                    self._logger.warn(LogCategory.STATE, error_msg)

                    # Capture error screenshot of current state
                    error_path = self._generate_error_screenshot_path(route, viewport)
                    try:
                        page.screenshot(path=str(error_path), full_page=True)
                        self._logger.debug(
                            LogCategory.STATE,
                            f"Error screenshot captured: {error_path}",
                        )
                    except Exception:
                        pass  # Best effort - don't fail if error screenshot fails

                    return ScreenshotResult(
                        path=error_path,
                        route=route.name,
                        viewport=viewport_str,
                        success=False,
                        error=error_msg,
                    )

                finally:
                    browser.close()

        except Exception as e:
            error_msg = f"Browser launch failed: {e!s}"
            self._logger.error(LogCategory.STATE, error_msg)
            return ScreenshotResult(
                path=screenshot_path,
                route=route.name,
                viewport=viewport_str,
                success=False,
                error=error_msg,
            )

    def capture_route_all_viewports(self, route: RouteConfig) -> list[ScreenshotResult]:
        """Capture screenshots of a route at all configured viewports.

        This method captures the same route at each viewport configuration,
        generating one screenshot per viewport.

        Args:
            route: Configuration for the route to capture

        Returns:
            List of ScreenshotResult, one per viewport.

        Example:
            >>> route = RouteConfig(name="home", path="/")
            >>> results = strategy.capture_route_all_viewports(route)
            >>> len(results)  # One per viewport (desktop, tablet, mobile)
            3
        """
        results: list[ScreenshotResult] = []

        for viewport in self.viewports:
            result = self.capture_route(route, viewport)
            results.append(result)

        return results
