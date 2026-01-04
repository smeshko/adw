"""Evidence-related models for ADW evidence gathering.

This module contains models for platform detection and evidence gathering
strategy selection during the Verify phase. Also includes API, CLI, and
web screenshot models for capturing evidence.

Includes:
- Platform detection models (PlatformType, Confidence, PlatformDetectionResult)
- Evidence strategy models (EvidenceStrategy)
- API evidence capture models (EndpointConfig, AuthConfig, APIRequest, APIResponse,
  APIEvidenceResult, APIEvidenceSummary)
- CLI evidence capture models (CommandConfig, CommandResult, CLIEvidenceSummary)
- Web evidence capture models (ViewportConfig, RouteConfig, ScreenshotResult,
  WebEvidenceSummary)
"""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

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


# ==============================================================================
# API Evidence Models (Story 8.4)
# ==============================================================================


class AuthType(str, Enum):
    """Authentication type for API endpoints.

    Supported authentication methods:
    - BEARER: Bearer token authentication (Authorization: Bearer <token>)
    - API_KEY: API key in custom header (X-API-Key: <key>)
    - BASIC: Basic HTTP authentication
    """

    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class EndpointConfig(BaseModel):
    """Configuration for an API endpoint to capture.

    Defines a single API endpoint that should be called during
    evidence gathering, including method, path, headers, body,
    and expected response status.

    Attributes:
        name: Unique identifier for the endpoint
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: URL path (will be appended to base_url)
        headers: Optional custom headers to include
        body: Optional request body (for POST, PUT, PATCH)
        expected_status: Optional expected HTTP status code
        timeout_seconds: Request timeout in seconds

    Example:
        >>> endpoint = EndpointConfig(
        ...     name="create_user",
        ...     method="POST",
        ...     path="/users",
        ...     body={"name": "test", "email": "test@example.com"},
        ...     expected_status=201,
        ... )
    """

    name: str = Field(..., description="Unique identifier for the endpoint")
    method: str = Field(default="GET", description="HTTP method")
    path: str = Field(..., description="URL path")
    headers: dict[str, str] | None = Field(
        default=None, description="Custom headers to include"
    )
    body: dict[str, Any] | None = Field(
        default=None, description="Request body for POST/PUT/PATCH"
    )
    expected_status: int | None = Field(
        default=None, description="Expected HTTP status code"
    )
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")


class AuthConfig(BaseModel):
    """Configuration for API authentication.

    Defines how to authenticate API requests. Supports bearer tokens,
    API keys, and basic authentication. Credentials are read from
    environment variables for security.

    Attributes:
        type: Authentication type (bearer, api_key, basic)
        token_env: Environment variable for bearer token
        header: Header name for API key authentication
        key_env: Environment variable for API key

    Example:
        >>> auth = AuthConfig(
        ...     type=AuthType.BEARER,
        ...     token_env="API_TOKEN",
        ... )
    """

    type: AuthType = Field(..., description="Authentication type")
    token_env: str | None = Field(
        default=None, description="Environment variable for bearer token"
    )
    header: str | None = Field(
        default=None, description="Header name for API key authentication"
    )
    key_env: str | None = Field(
        default=None, description="Environment variable for API key"
    )


class APIRequest(BaseModel):
    """Captured API request details.

    Records the full details of an HTTP request made during
    evidence gathering.

    Attributes:
        method: HTTP method used
        url: Full URL called
        headers: Request headers (auth tokens redacted)
        body: Request body if present

    Example:
        >>> request = APIRequest(
        ...     method="POST",
        ...     url="http://localhost:8000/users",
        ...     headers={"Content-Type": "application/json"},
        ...     body={"name": "test"},
        ... )
    """

    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Full URL")
    headers: dict[str, str] | None = Field(
        default=None, description="Request headers (auth redacted)"
    )
    body: dict[str, Any] | None = Field(default=None, description="Request body")


class APIResponse(BaseModel):
    """Captured API response details.

    Records the full details of an HTTP response received during
    evidence gathering.

    Attributes:
        status_code: HTTP status code
        headers: Response headers
        body: Response body (JSON parsed or raw string)
        duration_seconds: Request duration in seconds

    Example:
        >>> response = APIResponse(
        ...     status_code=200,
        ...     body={"status": "ok"},
        ...     duration_seconds=0.045,
        ... )
    """

    status_code: int = Field(..., description="HTTP status code")
    headers: dict[str, str] | None = Field(
        default=None, description="Response headers"
    )
    body: str | dict[str, Any] = Field(..., description="Response body")
    duration_seconds: float = Field(..., description="Request duration in seconds")


def _utc_now() -> datetime:
    """Return current UTC datetime for default factory."""
    return datetime.now(UTC)


class APIEvidenceResult(BaseModel):
    """Result of capturing a single API endpoint.

    Combines request and response details with success status
    and any error information for evidence purposes.

    Attributes:
        endpoint_name: Name of the endpoint captured
        request: Request details
        response: Response details
        success: Whether the request succeeded (2xx or expected status)
        expected_status: Expected status code if configured
        status_match: Whether actual status matches expected
        error: Error message if request failed
        captured_at: Timestamp when evidence was captured

    Example:
        >>> result = APIEvidenceResult(
        ...     endpoint_name="health",
        ...     request=APIRequest(method="GET", url="http://localhost:8000/health"),
        ...     response=APIResponse(status_code=200, body={"status": "ok"}, duration_seconds=0.01),
        ...     success=True,
        ... )
    """

    endpoint_name: str = Field(..., description="Name of the endpoint")
    request: APIRequest = Field(..., description="Request details")
    response: APIResponse = Field(..., description="Response details")
    success: bool = Field(..., description="Whether request succeeded")
    expected_status: int | None = Field(
        default=None, description="Expected status code"
    )
    status_match: bool = Field(
        default=True, description="Whether actual matches expected status"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    captured_at: datetime = Field(
        default_factory=_utc_now, description="Capture timestamp"
    )


class APIEvidenceSummary(BaseModel):
    """Summary of all API evidence captures.

    Aggregates results from all captured endpoints with
    success/failure counts and timing information.

    Attributes:
        base_url: Base URL for all endpoints
        total_endpoints: Total number of endpoints captured
        successful: Number of successful captures
        failed: Number of failed captures
        status_mismatches: Number of status code mismatches
        results: List of individual capture results
        captured_at: Timestamp when summary was generated

    Example:
        >>> summary = APIEvidenceSummary(
        ...     base_url="http://localhost:8000",
        ...     total_endpoints=5,
        ...     successful=4,
        ...     failed=1,
        ...     status_mismatches=0,
        ...     results=[...],
        ... )
    """

    base_url: str = Field(..., description="Base URL for endpoints")
    total_endpoints: int = Field(..., description="Total endpoints captured")
    successful: int = Field(..., description="Successful captures")
    failed: int = Field(..., description="Failed captures")
    status_mismatches: int = Field(..., description="Status code mismatches")
    results: list[APIEvidenceResult] = Field(
        default_factory=list, description="Individual results"
    )
    captured_at: datetime = Field(
        default_factory=_utc_now, description="Summary timestamp"
    )


# =============================================================================
# CLI Evidence Capture Models
# =============================================================================


class CommandConfig(BaseModel):
    """Configuration for a CLI command to execute during evidence gathering.

    This model represents a single command that will be executed to gather
    evidence during the Verify phase for CLI projects.

    Attributes:
        name: Unique identifier for the command (used in output filenames)
        cmd: The shell command to execute
        timeout: Maximum execution time in seconds (default: 30)

    Example:
        >>> config = CommandConfig(
        ...     name="version",
        ...     cmd="adw --version",
        ...     timeout=30,
        ... )
        >>> config.name
        'version'
    """

    name: str = Field(..., description="Unique name for this command")
    cmd: str = Field(..., description="The shell command to execute")
    timeout: int = Field(
        default=30,
        gt=0,
        description="Maximum execution time in seconds",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "name": "version",
                "cmd": "adw --version",
                "timeout": 30,
            }
        },
    }


class CommandResult(BaseModel):
    """Result of executing a CLI command.

    Captures the complete output and metadata from executing a command,
    including stdout, stderr, exit code, duration, and success status.

    Attributes:
        command: The command that was executed
        exit_code: Exit code from the command (-1 for timeout)
        stdout: Standard output captured from the command
        stderr: Standard error captured from the command
        duration_seconds: How long the command took to execute
        success: Whether the command succeeded (exit_code == 0)
        executed_at: When the command was executed (UTC)

    Example:
        >>> result = CommandResult(
        ...     command="adw --version",
        ...     exit_code=0,
        ...     stdout="adw version 1.0.0",
        ...     stderr="",
        ...     duration_seconds=0.125,
        ...     success=True,
        ... )
        >>> result.success
        True
    """

    command: str = Field(..., description="The command that was executed")
    exit_code: int = Field(..., description="Exit code from the command")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    duration_seconds: float = Field(
        ..., ge=0, description="Execution duration in seconds"
    )
    success: bool = Field(..., description="Whether the command succeeded")
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the command was executed (UTC)",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "command": "adw --version",
                "exit_code": 0,
                "stdout": "adw version 1.0.0",
                "stderr": "",
                "duration_seconds": 0.125,
                "success": True,
                "executed_at": "2026-01-03T10:30:45Z",
            }
        },
    }


class CLIEvidenceSummary(BaseModel):
    """Summary of CLI evidence gathering results.

    Aggregates the results of executing multiple CLI commands during
    the Verify phase, providing counts and detailed results.

    Attributes:
        total_commands: Total number of commands executed
        passed: Number of commands that succeeded (exit_code == 0)
        failed: Number of commands that failed (exit_code != 0)
        results: List of individual command results
        platform: The platform type (always "cli" for this summary)
        captured_at: When the evidence was captured (UTC)

    Example:
        >>> summary = CLIEvidenceSummary(
        ...     total_commands=5,
        ...     passed=4,
        ...     failed=1,
        ...     results=[...],
        ... )
        >>> summary.passed
        4
    """

    total_commands: int = Field(
        ..., ge=0, description="Total number of commands executed"
    )
    passed: int = Field(..., ge=0, description="Number of commands that succeeded")
    failed: int = Field(..., ge=0, description="Number of commands that failed")
    results: list[CommandResult] = Field(
        default_factory=list, description="Individual command results"
    )
    platform: str = Field(default="cli", description="Platform type (always 'cli')")
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When evidence was captured (UTC)",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "total_commands": 5,
                "passed": 4,
                "failed": 1,
                "platform": "cli",
                "captured_at": "2026-01-03T10:30:45Z",
                "results": [],
            }
        },
    }


# =============================================================================
# Web Evidence Capture Models
# =============================================================================


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
    wait_for: Literal["load", "domcontentloaded", "networkidle"] = Field(
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
    error: str | None = Field(
        default=None, description="Error message if capture failed"
    )
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
