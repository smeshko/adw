"""Tests for web screenshot capture module.

This module tests the WebCaptureStrategy class which handles Playwright
integration for capturing web screenshots.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.evidence.web_capture import (
    PLAYWRIGHT_AVAILABLE,
    WebCaptureStrategy,
    check_playwright_available,
)
from adw.models.evidence import RouteConfig, ViewportConfig


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
