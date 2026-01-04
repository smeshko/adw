"""Evidence-related models for ADW evidence gathering.

This module contains models for platform detection and evidence gathering
strategy selection during the Verify phase.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Type of project platform for evidence gathering.

    The platform type determines which evidence gathering strategy
    to use during the Verify phase:
    - CLI: Capture terminal output from CLI commands
    - WEB: Capture browser screenshots
    - MOBILE: Capture device/simulator screenshots
    - BACKEND: Capture API request/response pairs
    - UNKNOWN: Default to CLI strategy with warning
    """

    CLI = "cli"
    WEB = "web"
    MOBILE = "mobile"
    BACKEND = "backend"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    """Confidence level for platform detection.

    Confidence levels indicate how certain the detection is:
    - HIGH: Explicit config or multiple strong markers
    - MEDIUM: Multiple weak markers corroborating
    - LOW: Single weak marker or inference
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceStrategy(str, Enum):
    """Strategy for gathering evidence during Verify phase.

    Each strategy determines how evidence is captured:
    - TERMINAL_OUTPUT: Capture stdout/stderr from CLI commands
    - SCREENSHOT: Capture browser/device screenshots (WEB and MOBILE)
    - API_CAPTURE: Capture HTTP request/response pairs
    """

    TERMINAL_OUTPUT = "terminal_output"
    SCREENSHOT = "screenshot"
    API_CAPTURE = "api_capture"


class PlatformDetectionResult(BaseModel):
    """Result of platform detection.

    This model captures the outcome of detecting a project's platform type,
    including the confidence level and what markers were found.

    Attributes:
        platform: The detected platform type
        confidence: How confident the detection is
        source: Where the detection came from (config, markers, default)
        markers: List of markers found that informed the detection

    Example:
        >>> result = PlatformDetectionResult(
        ...     platform=PlatformType.WEB,
        ...     confidence=Confidence.HIGH,
        ...     source="markers",
        ...     markers=["package.json:react", "next.config.js"],
        ... )
        >>> result.platform
        <PlatformType.WEB: 'web'>
    """

    platform: PlatformType = Field(..., description="The detected platform type")
    confidence: Confidence = Field(..., description="How confident the detection is")
    source: str = Field(
        ..., description="Where the detection came from (config, markers, default)"
    )
    markers: list[str] = Field(
        default_factory=list,
        description="List of markers found that informed the detection",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "platform": "web",
                "confidence": "high",
                "source": "markers",
                "markers": ["package.json:react", "next.config.js"],
            }
        },
    }


# =============================================================================
# Mobile Evidence Models (Story 8.3b)
# =============================================================================


class MobileDeviceType(str, Enum):
    """Type of mobile device for evidence gathering.

    Distinguishes between native iOS, native Android, and Flutter-based
    mobile apps running on each platform.
    """

    IOS = "ios"
    ANDROID = "android"
    FLUTTER_IOS = "flutter_ios"
    FLUTTER_ANDROID = "flutter_android"


class MobileScreenConfig(BaseModel):
    """Configuration for a mobile screen to capture.

    Attributes:
        name: Screen identifier (used in filename)
        deeplink: Optional deeplink URL to navigate to this screen
        capture_delay_ms: Delay before capture after navigation (default 500ms)
        navigation_steps: Optional list of navigation actions (for complex navigation)

    Example:
        >>> config = MobileScreenConfig(
        ...     name="profile",
        ...     deeplink="myapp://profile/123",
        ...     capture_delay_ms=1000,
        ... )
    """

    name: str = Field(..., description="Screen identifier for the screenshot")
    deeplink: str | None = Field(
        default=None, description="Deeplink URL to navigate to this screen"
    )
    capture_delay_ms: int = Field(
        default=500, description="Delay in milliseconds before capture"
    )
    navigation_steps: list[dict[str, str]] = Field(
        default_factory=list,
        description="Navigation steps if deeplink not available",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "profile",
                "deeplink": "myapp://profile/123",
                "capture_delay_ms": 500,
            }
        }
    }


class MobileScreenshotResult(BaseModel):
    """Result of a mobile screenshot capture operation.

    Attributes:
        path: Path to the saved screenshot file
        screen_name: Name of the screen captured
        device_type: Type of mobile device used
        device_name: Human-readable device name (e.g., "iPhone 15 Pro")
        os_version: OS version string (e.g., "17.2")
        success: Whether the capture was successful
        error: Error message if capture failed
        captured_at: Timestamp when capture was performed

    Example:
        >>> result = MobileScreenshotResult(
        ...     path=Path("/tmp/home_ios.png"),
        ...     screen_name="home",
        ...     device_type=MobileDeviceType.IOS,
        ...     device_name="iPhone 15 Pro",
        ...     os_version="17.2",
        ...     success=True,
        ... )
    """

    path: Path = Field(..., description="Path to the saved screenshot file")
    screen_name: str = Field(..., description="Name of the screen captured")
    device_type: MobileDeviceType = Field(..., description="Type of mobile device")
    device_name: str | None = Field(
        default=None, description="Human-readable device name"
    )
    os_version: str | None = Field(default=None, description="OS version string")
    success: bool = Field(..., description="Whether capture was successful")
    error: str | None = Field(default=None, description="Error message if failed")
    captured_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp of capture"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "/tmp/home_ios.png",
                "screen_name": "home",
                "device_type": "ios",
                "device_name": "iPhone 15 Pro",
                "os_version": "17.2",
                "success": True,
            }
        }
    }


class MobileEvidenceSummary(BaseModel):
    """Summary of mobile evidence capture results.

    Aggregates results from multiple screenshot captures for reporting.

    Attributes:
        total_screenshots: Total number of screenshots attempted
        successful: Number of successful captures
        failed: Number of failed captures
        results: List of individual screenshot results
        captured_at: Timestamp when capture session completed

    Example:
        >>> summary = MobileEvidenceSummary(
        ...     total_screenshots=4,
        ...     successful=3,
        ...     failed=1,
        ...     results=[...],
        ... )
    """

    total_screenshots: int = Field(
        default=0, description="Total number of screenshots attempted"
    )
    successful: int = Field(default=0, description="Number of successful captures")
    failed: int = Field(default=0, description="Number of failed captures")
    results: list[MobileScreenshotResult] = Field(
        default_factory=list, description="Individual screenshot results"
    )
    captured_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp of capture session"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_screenshots": 4,
                "successful": 3,
                "failed": 1,
                "results": [],
            }
        }
    }
