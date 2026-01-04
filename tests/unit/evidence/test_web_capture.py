"""Tests for web screenshot capture module.

This module tests the WebCaptureStrategy class which handles Playwright
integration for capturing web screenshots.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.evidence.web_capture import (
    PLAYWRIGHT_AVAILABLE,
    WebCaptureStrategy,
    check_playwright_available,
)
from adw.models.evidence import RouteConfig, ScreenshotResult, ViewportConfig


class TestPlaywrightAvailability:
    """Tests for Playwright availability checking."""

    def test_playwright_available_constant_exists(self) -> None:
        """Test that PLAYWRIGHT_AVAILABLE constant exists."""
        assert isinstance(PLAYWRIGHT_AVAILABLE, bool)

    def test_check_playwright_available_function_exists(self) -> None:
        """Test that check_playwright_available function exists."""
        # Should return bool without raising
        result = check_playwright_available()
        assert isinstance(result, bool)

    @patch("adw.evidence.web_capture.PLAYWRIGHT_AVAILABLE", False)
    def test_check_playwright_available_returns_false_when_not_installed(
        self,
    ) -> None:
        """Test that check returns False when Playwright not installed."""
        result = check_playwright_available()
        assert result is False


class TestWebCaptureStrategy:
    """Tests for WebCaptureStrategy class."""

    def test_create_strategy(self, tmp_path: Path) -> None:
        """Test creating a WebCaptureStrategy instance."""
        output_dir = tmp_path / "screenshots"
        strategy = WebCaptureStrategy(
            output_dir=output_dir,
            base_url="http://localhost:3000",
        )
        assert strategy.output_dir == output_dir
        assert strategy.base_url == "http://localhost:3000"

    def test_create_strategy_creates_output_dir(self, tmp_path: Path) -> None:
        """Test that strategy creates output directory if it doesn't exist."""
        output_dir = tmp_path / "screenshots" / "nested"
        assert not output_dir.exists()

        strategy = WebCaptureStrategy(
            output_dir=output_dir,
            base_url="http://localhost:3000",
        )
        # Output directory should be created on initialization
        assert output_dir.exists()

    def test_strategy_default_viewports(self, tmp_path: Path) -> None:
        """Test that strategy has default viewports."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        assert strategy.viewports is not None
        assert len(strategy.viewports) > 0
        # Should have at least desktop viewport
        viewport_names = [v.name for v in strategy.viewports]
        assert "desktop" in viewport_names

    def test_strategy_custom_viewports(self, tmp_path: Path) -> None:
        """Test that strategy accepts custom viewports."""
        custom_viewports = [
            ViewportConfig(name="custom", width=800, height=600),
        ]
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
            viewports=custom_viewports,
        )
        assert strategy.viewports == custom_viewports

    def test_strategy_is_available_property(self, tmp_path: Path) -> None:
        """Test that strategy has is_available property."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        assert isinstance(strategy.is_available, bool)

    def test_strategy_headless_mode_default(self, tmp_path: Path) -> None:
        """Test that headless mode is enabled by default."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        assert strategy.headless is True

    def test_strategy_headless_mode_configurable(self, tmp_path: Path) -> None:
        """Test that headless mode can be disabled."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
            headless=False,
        )
        assert strategy.headless is False


class TestWebCaptureStrategyGracefulDegradation:
    """Tests for graceful degradation when Playwright is not available."""

    @patch("adw.evidence.web_capture.PLAYWRIGHT_AVAILABLE", False)
    def test_strategy_is_available_false_when_not_installed(
        self, tmp_path: Path
    ) -> None:
        """Test that is_available is False when Playwright not installed."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        assert strategy.is_available is False

    @patch("adw.evidence.web_capture.PLAYWRIGHT_AVAILABLE", False)
    def test_strategy_graceful_skip_message(self, tmp_path: Path) -> None:
        """Test that strategy provides skip message when not available."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        # Should have a reason why it's not available
        assert hasattr(strategy, "unavailable_reason")
        assert strategy.unavailable_reason is not None
        assert "playwright" in strategy.unavailable_reason.lower()


class TestRouteCaptureMethod:
    """Tests for capture_route method."""

    def test_capture_route_method_exists(self, tmp_path: Path) -> None:
        """Test that capture_route method exists."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        assert hasattr(strategy, "capture_route")
        assert callable(strategy.capture_route)

    def test_capture_route_returns_screenshot_result(self, tmp_path: Path) -> None:
        """Test that capture_route returns a ScreenshotResult."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="home", path="/")
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        result = strategy.capture_route(route, viewport)

        assert isinstance(result, ScreenshotResult)
        assert result.route == "home"
        assert result.viewport == "1920x1080"

    def test_capture_route_generates_correct_path(self, tmp_path: Path) -> None:
        """Test that capture generates correct output path."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="dashboard", path="/dashboard")
        viewport = ViewportConfig(name="mobile", width=375, height=667)

        result = strategy.capture_route(route, viewport)

        # Path should include route name and viewport
        assert "dashboard" in str(result.path)
        assert "mobile" in str(result.path)
        assert result.path.suffix == ".png"

    @patch("adw.evidence.web_capture.PLAYWRIGHT_AVAILABLE", False)
    def test_capture_route_fails_gracefully_when_unavailable(
        self, tmp_path: Path
    ) -> None:
        """Test that capture_route fails gracefully when Playwright unavailable."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="home", path="/")
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        result = strategy.capture_route(route, viewport)

        assert result.success is False
        assert result.error is not None
        assert "playwright" in result.error.lower()

    def test_capture_route_uses_configured_timeout(self, tmp_path: Path) -> None:
        """Test that capture_route respects route timeout configuration."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="slow", path="/slow", timeout_ms=60000)
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        # Method should accept route with custom timeout without error
        result = strategy.capture_route(route, viewport)
        assert isinstance(result, ScreenshotResult)

    def test_capture_route_has_captured_at_timestamp(self, tmp_path: Path) -> None:
        """Test that capture_route sets captured_at timestamp."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="home", path="/")
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        before = datetime.now()
        result = strategy.capture_route(route, viewport)
        after = datetime.now()

        assert before <= result.captured_at <= after


class TestMultiViewportCapture:
    """Tests for multi-viewport capture functionality."""

    def test_capture_route_all_viewports_method_exists(self, tmp_path: Path) -> None:
        """Test that capture_route_all_viewports method exists."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        assert hasattr(strategy, "capture_route_all_viewports")
        assert callable(strategy.capture_route_all_viewports)

    def test_capture_route_all_viewports_returns_list(self, tmp_path: Path) -> None:
        """Test that capture_route_all_viewports returns list of results."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="home", path="/")

        results = strategy.capture_route_all_viewports(route)

        assert isinstance(results, list)
        # Should have one result per default viewport
        assert len(results) == len(strategy.viewports)

    def test_capture_route_all_viewports_uses_all_viewports(
        self, tmp_path: Path
    ) -> None:
        """Test that capture uses all configured viewports."""
        custom_viewports = [
            ViewportConfig(name="small", width=320, height=480),
            ViewportConfig(name="large", width=2560, height=1440),
        ]
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
            viewports=custom_viewports,
        )
        route = RouteConfig(name="test", path="/test")

        results = strategy.capture_route_all_viewports(route)

        assert len(results) == 2
        viewport_names = {r.viewport for r in results}
        assert "320x480" in viewport_names
        assert "2560x1440" in viewport_names

    def test_default_viewports_include_standard_sizes(self, tmp_path: Path) -> None:
        """Test that default viewports include desktop, tablet, mobile."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )

        viewport_names = [v.name for v in strategy.viewports]
        assert "desktop" in viewport_names
        assert "tablet" in viewport_names
        assert "mobile" in viewport_names

    def test_file_naming_includes_viewport_suffix(self, tmp_path: Path) -> None:
        """Test that screenshot files are named with viewport suffix."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="dashboard", path="/dashboard")

        results = strategy.capture_route_all_viewports(route)

        for result in results:
            # Filename should contain route name and viewport name
            filename = result.path.name
            assert "dashboard" in filename
            # Should have viewport name in filename (desktop, tablet, or mobile)
            assert any(
                vp.name in filename for vp in strategy.viewports
            ), f"Filename {filename} should contain viewport name"


class TestErrorScreenshotCapture:
    """Tests for error screenshot capture functionality."""

    def test_error_screenshot_path_generation(self, tmp_path: Path) -> None:
        """Test that error screenshots have _error suffix."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="broken", path="/broken")
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        error_path = strategy._generate_error_screenshot_path(route, viewport)

        assert "_error" in str(error_path)
        assert error_path.suffix == ".png"

    def test_error_result_includes_details(self, tmp_path: Path) -> None:
        """Test that error results include error details."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="broken", path="/broken")
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        # When Playwright is not available, we should get a failure with error
        result = strategy.capture_route(route, viewport)

        # Since Playwright might not be available in tests, check structure
        assert isinstance(result, ScreenshotResult)
        if not result.success:
            assert result.error is not None
            assert len(result.error) > 0

    @patch("adw.evidence.web_capture.PLAYWRIGHT_AVAILABLE", False)
    def test_error_details_recorded_when_unavailable(self, tmp_path: Path) -> None:
        """Test that error details are recorded when Playwright unavailable."""
        strategy = WebCaptureStrategy(
            output_dir=tmp_path,
            base_url="http://localhost:3000",
        )
        route = RouteConfig(name="test", path="/test")
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)

        result = strategy.capture_route(route, viewport)

        assert result.success is False
        assert result.error is not None
        assert "playwright" in result.error.lower()
        # Error should be descriptive
        assert "not available" in result.error.lower()
