"""Tests for evidence-related models.

This module tests the PlatformType, Confidence, and PlatformDetectionResult
models used for evidence gathering platform detection.
Also tests web screenshot models: RouteConfig, ViewportConfig, ScreenshotResult,
and WebEvidenceSummary.
"""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from adw.models.evidence import (
    Confidence,
    EvidenceStrategy,
    PlatformDetectionResult,
    PlatformType,
    RouteConfig,
    ScreenshotResult,
    ViewportConfig,
    WebEvidenceSummary,
)


class TestPlatformType:
    """Tests for PlatformType enum."""

    def test_platform_type_values(self) -> None:
        """Test that all expected platform types exist."""
        assert PlatformType.CLI == "cli"
        assert PlatformType.WEB == "web"
        assert PlatformType.MOBILE == "mobile"
        assert PlatformType.BACKEND == "backend"
        assert PlatformType.UNKNOWN == "unknown"

    def test_platform_type_is_string_enum(self) -> None:
        """Test that PlatformType inherits from str."""
        assert isinstance(PlatformType.CLI, str)
        assert isinstance(PlatformType.WEB, str)
        assert isinstance(PlatformType.MOBILE, str)

    def test_platform_type_from_string(self) -> None:
        """Test creating PlatformType from string value."""
        assert PlatformType("cli") == PlatformType.CLI
        assert PlatformType("web") == PlatformType.WEB
        assert PlatformType("mobile") == PlatformType.MOBILE
        assert PlatformType("backend") == PlatformType.BACKEND
        assert PlatformType("unknown") == PlatformType.UNKNOWN

    def test_invalid_platform_type_raises(self) -> None:
        """Test that invalid platform type raises ValueError."""
        with pytest.raises(ValueError):
            PlatformType("invalid")

    def test_platform_type_json_serialization(self) -> None:
        """Test that PlatformType serializes correctly."""
        # Value is accessible as the string
        assert PlatformType.CLI.value == "cli"
        assert PlatformType.WEB.value == "web"
        # Can be compared to string due to str inheritance
        assert PlatformType.CLI == "cli"
        assert PlatformType.WEB == "web"


class TestConfidence:
    """Tests for Confidence enum."""

    def test_confidence_values(self) -> None:
        """Test that all expected confidence levels exist."""
        assert Confidence.HIGH == "high"
        assert Confidence.MEDIUM == "medium"
        assert Confidence.LOW == "low"

    def test_confidence_is_string_enum(self) -> None:
        """Test that Confidence inherits from str."""
        assert isinstance(Confidence.HIGH, str)
        assert isinstance(Confidence.MEDIUM, str)
        assert isinstance(Confidence.LOW, str)

    def test_confidence_from_string(self) -> None:
        """Test creating Confidence from string value."""
        assert Confidence("high") == Confidence.HIGH
        assert Confidence("medium") == Confidence.MEDIUM
        assert Confidence("low") == Confidence.LOW

    def test_invalid_confidence_raises(self) -> None:
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError):
            Confidence("invalid")


class TestEvidenceStrategy:
    """Tests for EvidenceStrategy enum."""

    def test_evidence_strategy_values(self) -> None:
        """Test that all expected evidence strategies exist."""
        assert EvidenceStrategy.TERMINAL_OUTPUT == "terminal_output"
        assert EvidenceStrategy.SCREENSHOT == "screenshot"
        assert EvidenceStrategy.API_CAPTURE == "api_capture"

    def test_evidence_strategy_is_string_enum(self) -> None:
        """Test that EvidenceStrategy inherits from str."""
        assert isinstance(EvidenceStrategy.TERMINAL_OUTPUT, str)
        assert isinstance(EvidenceStrategy.SCREENSHOT, str)
        assert isinstance(EvidenceStrategy.API_CAPTURE, str)

    def test_evidence_strategy_from_string(self) -> None:
        """Test creating EvidenceStrategy from string value."""
        assert EvidenceStrategy("terminal_output") == EvidenceStrategy.TERMINAL_OUTPUT
        assert EvidenceStrategy("screenshot") == EvidenceStrategy.SCREENSHOT
        assert EvidenceStrategy("api_capture") == EvidenceStrategy.API_CAPTURE

    def test_invalid_evidence_strategy_raises(self) -> None:
        """Test that invalid evidence strategy raises ValueError."""
        with pytest.raises(ValueError):
            EvidenceStrategy("invalid")


class TestPlatformDetectionResult:
    """Tests for PlatformDetectionResult model."""

    def test_create_detection_result(self) -> None:
        """Test creating a basic detection result."""
        result = PlatformDetectionResult(
            platform=PlatformType.CLI,
            confidence=Confidence.HIGH,
            source="config",
        )
        assert result.platform == PlatformType.CLI
        assert result.confidence == Confidence.HIGH
        assert result.source == "config"
        assert result.markers == []  # Default empty list

    def test_detection_result_with_markers(self) -> None:
        """Test creating detection result with markers."""
        result = PlatformDetectionResult(
            platform=PlatformType.WEB,
            confidence=Confidence.MEDIUM,
            source="markers",
            markers=["package.json:react", "next.config.js"],
        )
        assert result.platform == PlatformType.WEB
        assert result.markers == ["package.json:react", "next.config.js"]

    def test_detection_result_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            PlatformDetectionResult(
                platform=PlatformType.CLI,
                # missing confidence and source
            )

    def test_detection_result_json_serialization(self) -> None:
        """Test JSON serialization of detection result."""
        result = PlatformDetectionResult(
            platform=PlatformType.BACKEND,
            confidence=Confidence.LOW,
            source="default",
            markers=["Dockerfile"],
        )
        data = result.model_dump()
        assert data["platform"] == "backend"
        assert data["confidence"] == "low"
        assert data["source"] == "default"
        assert data["markers"] == ["Dockerfile"]

    def test_detection_result_json_deserialization(self) -> None:
        """Test creating detection result from JSON data."""
        data = {
            "platform": "web",
            "confidence": "high",
            "source": "config",
            "markers": [],
        }
        result = PlatformDetectionResult.model_validate(data)
        assert result.platform == PlatformType.WEB
        assert result.confidence == Confidence.HIGH

    def test_detection_result_invalid_platform(self) -> None:
        """Test that invalid platform value raises error."""
        with pytest.raises(ValidationError):
            PlatformDetectionResult(
                platform="invalid",
                confidence=Confidence.HIGH,
                source="config",
            )

    def test_detection_result_invalid_confidence(self) -> None:
        """Test that invalid confidence value raises error."""
        with pytest.raises(ValidationError):
            PlatformDetectionResult(
                platform=PlatformType.CLI,
                confidence="invalid",
                source="config",
            )

    def test_detection_result_source_values(self) -> None:
        """Test valid source values."""
        for source in ["config", "markers", "default"]:
            result = PlatformDetectionResult(
                platform=PlatformType.CLI,
                confidence=Confidence.HIGH,
                source=source,
            )
            assert result.source == source

    def test_detection_result_markers_default_factory(self) -> None:
        """Test that markers defaults to empty list (not shared mutable)."""
        result1 = PlatformDetectionResult(
            platform=PlatformType.CLI,
            confidence=Confidence.HIGH,
            source="config",
        )
        result2 = PlatformDetectionResult(
            platform=PlatformType.WEB,
            confidence=Confidence.LOW,
            source="markers",
        )
        # Ensure different instances have different lists
        result1.markers.append("test")
        assert result2.markers == []


class TestViewportConfig:
    """Tests for ViewportConfig model."""

    def test_create_viewport_config(self) -> None:
        """Test creating a basic viewport configuration."""
        viewport = ViewportConfig(name="desktop", width=1920, height=1080)
        assert viewport.name == "desktop"
        assert viewport.width == 1920
        assert viewport.height == 1080

    def test_viewport_config_required_fields(self) -> None:
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            ViewportConfig(name="desktop")  # Missing width and height

    def test_viewport_config_json_serialization(self) -> None:
        """Test JSON serialization of viewport config."""
        viewport = ViewportConfig(name="mobile", width=375, height=667)
        data = viewport.model_dump()
        assert data["name"] == "mobile"
        assert data["width"] == 375
        assert data["height"] == 667

    def test_viewport_config_json_deserialization(self) -> None:
        """Test creating viewport from JSON data."""
        data = {"name": "tablet", "width": 768, "height": 1024}
        viewport = ViewportConfig.model_validate(data)
        assert viewport.name == "tablet"
        assert viewport.width == 768
        assert viewport.height == 1024

    def test_viewport_config_positive_dimensions(self) -> None:
        """Test that dimensions must be positive."""
        with pytest.raises(ValidationError):
            ViewportConfig(name="invalid", width=-100, height=100)
        with pytest.raises(ValidationError):
            ViewportConfig(name="invalid", width=100, height=-100)


class TestRouteConfig:
    """Tests for RouteConfig model."""

    def test_create_route_config_minimal(self) -> None:
        """Test creating a route with minimal required fields."""
        route = RouteConfig(name="home", path="/")
        assert route.name == "home"
        assert route.path == "/"
        assert route.wait_for == "networkidle"  # Default
        assert route.timeout_ms == 30000  # Default

    def test_create_route_config_full(self) -> None:
        """Test creating a route with all fields."""
        route = RouteConfig(
            name="dashboard",
            path="/dashboard",
            wait_for="load",
            timeout_ms=60000,
        )
        assert route.name == "dashboard"
        assert route.path == "/dashboard"
        assert route.wait_for == "load"
        assert route.timeout_ms == 60000

    def test_route_config_wait_for_values(self) -> None:
        """Test valid wait_for values."""
        for wait_for in ["networkidle", "load", "domcontentloaded"]:
            route = RouteConfig(name="test", path="/test", wait_for=wait_for)
            assert route.wait_for == wait_for

    def test_route_config_json_serialization(self) -> None:
        """Test JSON serialization of route config."""
        route = RouteConfig(name="login", path="/login", timeout_ms=15000)
        data = route.model_dump()
        assert data["name"] == "login"
        assert data["path"] == "/login"
        assert data["wait_for"] == "networkidle"
        assert data["timeout_ms"] == 15000

    def test_route_config_json_deserialization(self) -> None:
        """Test creating route from JSON data."""
        data = {
            "name": "profile",
            "path": "/profile",
            "wait_for": "load",
            "timeout_ms": 45000,
        }
        route = RouteConfig.model_validate(data)
        assert route.name == "profile"
        assert route.path == "/profile"
        assert route.wait_for == "load"
        assert route.timeout_ms == 45000

    def test_route_config_required_fields(self) -> None:
        """Test that name and path are required."""
        with pytest.raises(ValidationError):
            RouteConfig(name="test")  # Missing path
        with pytest.raises(ValidationError):
            RouteConfig(path="/test")  # Missing name


class TestScreenshotResult:
    """Tests for ScreenshotResult model."""

    def test_create_screenshot_result_success(self) -> None:
        """Test creating a successful screenshot result."""
        result = ScreenshotResult(
            path=Path("/tmp/screenshots/home_desktop.png"),
            route="home",
            viewport="1920x1080",
            success=True,
        )
        assert result.path == Path("/tmp/screenshots/home_desktop.png")
        assert result.route == "home"
        assert result.viewport == "1920x1080"
        assert result.success is True
        assert result.error is None
        assert isinstance(result.captured_at, datetime)

    def test_create_screenshot_result_failure(self) -> None:
        """Test creating a failed screenshot result."""
        result = ScreenshotResult(
            path=Path("/tmp/screenshots/dashboard_error.png"),
            route="dashboard",
            viewport="1920x1080",
            success=False,
            error="Timeout waiting for page load",
        )
        assert result.success is False
        assert result.error == "Timeout waiting for page load"

    def test_screenshot_result_path_types(self) -> None:
        """Test that path can be string or Path."""
        # With Path
        result1 = ScreenshotResult(
            path=Path("/tmp/test.png"),
            route="test",
            viewport="1920x1080",
            success=True,
        )
        assert isinstance(result1.path, Path)

        # With string (should convert to Path)
        result2 = ScreenshotResult(
            path="/tmp/test.png",
            route="test",
            viewport="1920x1080",
            success=True,
        )
        assert isinstance(result2.path, Path)

    def test_screenshot_result_json_serialization(self) -> None:
        """Test JSON serialization of screenshot result."""
        result = ScreenshotResult(
            path=Path("/tmp/home.png"),
            route="home",
            viewport="1920x1080",
            success=True,
        )
        data = result.model_dump()
        assert data["route"] == "home"
        assert data["viewport"] == "1920x1080"
        assert data["success"] is True
        assert data["error"] is None

    def test_screenshot_result_default_captured_at(self) -> None:
        """Test that captured_at is auto-generated."""
        before = datetime.now()
        result = ScreenshotResult(
            path=Path("/tmp/test.png"),
            route="test",
            viewport="1920x1080",
            success=True,
        )
        after = datetime.now()
        assert before <= result.captured_at <= after


class TestWebEvidenceSummary:
    """Tests for WebEvidenceSummary model."""

    def test_create_evidence_summary_empty(self) -> None:
        """Test creating an empty evidence summary."""
        summary = WebEvidenceSummary(
            base_url="http://localhost:3000",
            total_screenshots=0,
            successful=0,
            failed=0,
            results=[],
        )
        assert summary.base_url == "http://localhost:3000"
        assert summary.total_screenshots == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.results == []

    def test_create_evidence_summary_with_results(self) -> None:
        """Test creating an evidence summary with results."""
        results = [
            ScreenshotResult(
                path=Path("/tmp/home.png"),
                route="home",
                viewport="1920x1080",
                success=True,
            ),
            ScreenshotResult(
                path=Path("/tmp/dashboard.png"),
                route="dashboard",
                viewport="1920x1080",
                success=False,
                error="Timeout",
            ),
        ]
        summary = WebEvidenceSummary(
            base_url="http://localhost:3000",
            total_screenshots=2,
            successful=1,
            failed=1,
            results=results,
        )
        assert summary.total_screenshots == 2
        assert summary.successful == 1
        assert summary.failed == 1
        assert len(summary.results) == 2

    def test_evidence_summary_json_serialization(self) -> None:
        """Test JSON serialization of evidence summary."""
        summary = WebEvidenceSummary(
            base_url="http://localhost:3000",
            total_screenshots=1,
            successful=1,
            failed=0,
            results=[
                ScreenshotResult(
                    path=Path("/tmp/home.png"),
                    route="home",
                    viewport="1920x1080",
                    success=True,
                ),
            ],
        )
        data = summary.model_dump()
        assert data["base_url"] == "http://localhost:3000"
        assert data["total_screenshots"] == 1
        assert len(data["results"]) == 1

    def test_evidence_summary_required_fields(self) -> None:
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            WebEvidenceSummary(base_url="http://localhost:3000")

    def test_evidence_summary_results_type(self) -> None:
        """Test that results must be a list of ScreenshotResult."""
        with pytest.raises(ValidationError):
            WebEvidenceSummary(
                base_url="http://localhost:3000",
                total_screenshots=1,
                successful=1,
                failed=0,
                results=["not a ScreenshotResult"],
            )
