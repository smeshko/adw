"""Evidence-related models for ADW evidence gathering.

This module contains models for platform detection and evidence gathering
strategy selection during the Verify phase. Also includes web screenshot
models for capturing browser-based evidence.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


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


class ViewportConfig(BaseModel):
    """Configuration for browser viewport dimensions.

    Used to specify screenshot capture dimensions for web evidence.

    Attributes:
        name: Human-readable name for the viewport (e.g., "desktop", "mobile")
        width: Viewport width in pixels
        height: Viewport height in pixels

    Example:
        >>> viewport = ViewportConfig(name="desktop", width=1920, height=1080)
        >>> viewport.width
        1920
    """

    name: str = Field(..., description="Human-readable name for the viewport")
    width: int = Field(..., gt=0, description="Viewport width in pixels")
    height: int = Field(..., gt=0, description="Viewport height in pixels")

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "name": "desktop",
                "width": 1920,
                "height": 1080,
            }
        },
    }


class RouteConfig(BaseModel):
    """Configuration for a web route to capture.

    Specifies how to navigate to and capture a specific route during
    web evidence gathering.

    Attributes:
        name: Human-readable name for the route (used in filenames)
        path: URL path relative to base_url (e.g., "/", "/dashboard")
        wait_for: Page load strategy - "networkidle", "load", or "domcontentloaded"
        timeout_ms: Maximum time to wait for page load in milliseconds

    Example:
        >>> route = RouteConfig(name="home", path="/", wait_for="networkidle")
        >>> route.timeout_ms
        30000
    """

    name: str = Field(..., description="Human-readable name for the route")
    path: str = Field(..., description="URL path relative to base_url")
    wait_for: str = Field(
        default="networkidle",
        description="Page load strategy: networkidle, load, or domcontentloaded",
    )
    timeout_ms: int = Field(
        default=30000,
        gt=0,
        description="Maximum time to wait for page load in milliseconds",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "name": "home",
                "path": "/",
                "wait_for": "networkidle",
                "timeout_ms": 30000,
            }
        },
    }


class ScreenshotResult(BaseModel):
    """Result of a single screenshot capture.

    Records the outcome of capturing a screenshot for a specific route
    and viewport combination.

    Attributes:
        path: File path where screenshot was saved
        route: Name of the route that was captured
        viewport: Viewport dimensions as string (e.g., "1920x1080")
        success: Whether the capture was successful
        error: Error message if capture failed
        captured_at: Timestamp when screenshot was captured

    Example:
        >>> result = ScreenshotResult(
        ...     path=Path("/tmp/home_desktop.png"),
        ...     route="home",
        ...     viewport="1920x1080",
        ...     success=True,
        ... )
        >>> result.success
        True
    """

    path: Path = Field(..., description="File path where screenshot was saved")
    route: str = Field(..., description="Name of the route that was captured")
    viewport: str = Field(
        ..., description='Viewport dimensions as string (e.g., "1920x1080")'
    )
    success: bool = Field(..., description="Whether the capture was successful")
    error: str | None = Field(default=None, description="Error message if capture failed")
    captured_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when screenshot was captured",
    )

    @field_validator("path", mode="before")
    @classmethod
    def convert_path(cls, v: str | Path) -> Path:
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "path": "/tmp/screenshots/home_desktop.png",
                "route": "home",
                "viewport": "1920x1080",
                "success": True,
                "error": None,
                "captured_at": "2026-01-03T10:30:45",
            }
        },
    }


class WebEvidenceSummary(BaseModel):
    """Summary of web evidence gathering results.

    Aggregates all screenshot results from a web evidence capture session.

    Attributes:
        base_url: Base URL that was captured
        total_screenshots: Total number of screenshots attempted
        successful: Number of successful captures
        failed: Number of failed captures
        results: List of individual screenshot results

    Example:
        >>> summary = WebEvidenceSummary(
        ...     base_url="http://localhost:3000",
        ...     total_screenshots=4,
        ...     successful=3,
        ...     failed=1,
        ...     results=[...],
        ... )
        >>> summary.successful
        3
    """

    base_url: str = Field(..., description="Base URL that was captured")
    total_screenshots: int = Field(
        ..., ge=0, description="Total number of screenshots attempted"
    )
    successful: int = Field(..., ge=0, description="Number of successful captures")
    failed: int = Field(..., ge=0, description="Number of failed captures")
    results: list[ScreenshotResult] = Field(
        ..., description="List of individual screenshot results"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "base_url": "http://localhost:3000",
                "total_screenshots": 4,
                "successful": 3,
                "failed": 1,
                "results": [],
            }
        },
    }
