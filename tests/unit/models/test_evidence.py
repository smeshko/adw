"""Tests for evidence-related models.

This module tests the PlatformType, Confidence, and PlatformDetectionResult
models used for evidence gathering platform detection.
"""

import pytest
from pydantic import ValidationError

from adw.models.evidence import (
    Confidence,
    EvidenceStrategy,
    PlatformDetectionResult,
    PlatformType,
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


# =============================================================================
# Mobile Evidence Models Tests (Story 8.3b)
# =============================================================================


class TestMobileDeviceType:
    """Tests for MobileDeviceType enum."""

    def test_mobile_device_type_values(self) -> None:
        """Test that all expected mobile device types exist."""
        from adw.models.evidence import MobileDeviceType

        assert MobileDeviceType.IOS == "ios"
        assert MobileDeviceType.ANDROID == "android"
        assert MobileDeviceType.FLUTTER_IOS == "flutter_ios"
        assert MobileDeviceType.FLUTTER_ANDROID == "flutter_android"

    def test_mobile_device_type_is_string_enum(self) -> None:
        """Test that MobileDeviceType inherits from str."""
        from adw.models.evidence import MobileDeviceType

        assert isinstance(MobileDeviceType.IOS, str)
        assert isinstance(MobileDeviceType.ANDROID, str)
        assert isinstance(MobileDeviceType.FLUTTER_IOS, str)
        assert isinstance(MobileDeviceType.FLUTTER_ANDROID, str)

    def test_mobile_device_type_from_string(self) -> None:
        """Test creating MobileDeviceType from string value."""
        from adw.models.evidence import MobileDeviceType

        assert MobileDeviceType("ios") == MobileDeviceType.IOS
        assert MobileDeviceType("android") == MobileDeviceType.ANDROID
        assert MobileDeviceType("flutter_ios") == MobileDeviceType.FLUTTER_IOS
        assert MobileDeviceType("flutter_android") == MobileDeviceType.FLUTTER_ANDROID

    def test_invalid_mobile_device_type_raises(self) -> None:
        """Test that invalid mobile device type raises ValueError."""
        from adw.models.evidence import MobileDeviceType

        with pytest.raises(ValueError):
            MobileDeviceType("invalid")


class TestMobileScreenConfig:
    """Tests for MobileScreenConfig model."""

    def test_create_basic_screen_config(self) -> None:
        """Test creating a basic screen configuration."""
        from adw.models.evidence import MobileScreenConfig

        config = MobileScreenConfig(name="home")
        assert config.name == "home"
        assert config.deeplink is None
        assert config.capture_delay_ms == 500  # default
        assert config.navigation_steps == []

    def test_create_screen_config_with_deeplink(self) -> None:
        """Test creating screen config with deeplink."""
        from adw.models.evidence import MobileScreenConfig

        config = MobileScreenConfig(
            name="profile",
            deeplink="myapp://profile/123",
            capture_delay_ms=1000,
        )
        assert config.name == "profile"
        assert config.deeplink == "myapp://profile/123"
        assert config.capture_delay_ms == 1000

    def test_screen_config_json_serialization(self) -> None:
        """Test JSON serialization of screen config."""
        from adw.models.evidence import MobileScreenConfig

        config = MobileScreenConfig(
            name="settings",
            deeplink="myapp://settings",
        )
        data = config.model_dump()
        assert data["name"] == "settings"
        assert data["deeplink"] == "myapp://settings"

    def test_screen_config_name_required(self) -> None:
        """Test that name is required."""
        from adw.models.evidence import MobileScreenConfig

        with pytest.raises(ValidationError):
            MobileScreenConfig()  # type: ignore


class TestMobileScreenshotResult:
    """Tests for MobileScreenshotResult model."""

    def test_create_successful_screenshot_result(self) -> None:
        """Test creating a successful screenshot result."""
        from pathlib import Path

        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/screenshot.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            success=True,
        )
        assert result.path == Path("/tmp/screenshot.png")
        assert result.screen_name == "home"
        assert result.device_type == MobileDeviceType.IOS
        assert result.success is True
        assert result.error is None
        assert result.device_name is None
        assert result.os_version is None

    def test_create_failed_screenshot_result(self) -> None:
        """Test creating a failed screenshot result."""
        from pathlib import Path

        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/screenshot.png"),
            screen_name="profile",
            device_type=MobileDeviceType.ANDROID,
            success=False,
            error="No emulator running",
        )
        assert result.success is False
        assert result.error == "No emulator running"

    def test_screenshot_result_with_device_info(self) -> None:
        """Test screenshot result with device info."""
        from pathlib import Path

        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/home_ios.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            device_name="iPhone 15 Pro",
            os_version="17.2",
            success=True,
        )
        assert result.device_name == "iPhone 15 Pro"
        assert result.os_version == "17.2"

    def test_screenshot_result_has_captured_at(self) -> None:
        """Test that screenshot result has captured_at timestamp."""
        from datetime import datetime
        from pathlib import Path

        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/screenshot.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            success=True,
        )
        assert isinstance(result.captured_at, datetime)

    def test_screenshot_result_json_serialization(self) -> None:
        """Test JSON serialization of screenshot result."""
        from pathlib import Path

        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/home_android.png"),
            screen_name="home",
            device_type=MobileDeviceType.ANDROID,
            device_name="sdk_gphone64",
            os_version="14",
            success=True,
        )
        data = result.model_dump()
        assert data["screen_name"] == "home"
        assert data["device_type"] == "android"
        assert data["device_name"] == "sdk_gphone64"
        assert data["success"] is True


class TestMobileEvidenceSummary:
    """Tests for MobileEvidenceSummary model."""

    def test_create_empty_summary(self) -> None:
        """Test creating an empty mobile evidence summary."""
        from adw.models.evidence import MobileEvidenceSummary

        summary = MobileEvidenceSummary()
        assert summary.total_screenshots == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.results == []

    def test_create_summary_with_results(self) -> None:
        """Test creating summary with screenshot results."""
        from pathlib import Path

        from adw.models.evidence import (
            MobileDeviceType,
            MobileEvidenceSummary,
            MobileScreenshotResult,
        )

        results = [
            MobileScreenshotResult(
                path=Path("/tmp/home_ios.png"),
                screen_name="home",
                device_type=MobileDeviceType.IOS,
                success=True,
            ),
            MobileScreenshotResult(
                path=Path("/tmp/profile_ios.png"),
                screen_name="profile",
                device_type=MobileDeviceType.IOS,
                success=False,
                error="Timeout",
            ),
        ]
        summary = MobileEvidenceSummary(
            total_screenshots=2,
            successful=1,
            failed=1,
            results=results,
        )
        assert summary.total_screenshots == 2
        assert summary.successful == 1
        assert summary.failed == 1
        assert len(summary.results) == 2

    def test_summary_json_serialization(self) -> None:
        """Test JSON serialization of evidence summary."""
        from adw.models.evidence import MobileEvidenceSummary

        summary = MobileEvidenceSummary(
            total_screenshots=5,
            successful=4,
            failed=1,
            results=[],
        )
        data = summary.model_dump()
        assert data["total_screenshots"] == 5
        assert data["successful"] == 4
        assert data["failed"] == 1

    def test_summary_has_captured_at(self) -> None:
        """Test that summary has captured_at timestamp."""
        from datetime import datetime

        from adw.models.evidence import MobileEvidenceSummary

        summary = MobileEvidenceSummary()
        assert isinstance(summary.captured_at, datetime)
