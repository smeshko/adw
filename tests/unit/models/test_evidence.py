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
