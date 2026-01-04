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
- Evidence manifest models (EvidenceType, EvidenceStatus, EvidenceItem,
  PlanStepCoverage, CoverageSummary, EvidenceManifest)
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
    headers: dict[str, str] | None = Field(default=None, description="Response headers")
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


# =============================================================================
# Evidence Manifest Models (Story 8.5)
# =============================================================================


class EvidenceType(str, Enum):
    """Type of evidence captured during the Verify phase.

    Used to categorize evidence items in the manifest:
    - CLI: Terminal/command output captures
    - SCREENSHOT: Browser or device screenshots
    - API: HTTP request/response pairs
    - LOG: Application or server logs
    """

    CLI = "cli"
    SCREENSHOT = "screenshot"
    API = "api"
    LOG = "log"


class EvidenceStatus(str, Enum):
    """Status of an evidence item.

    Indicates whether the evidence capture succeeded and if the
    captured evidence shows expected behavior:
    - PASS: Evidence captured and shows expected behavior
    - FAIL: Evidence captured but shows unexpected/failed behavior
    - ERROR: Failed to capture evidence (technical error)
    - SKIPPED: Evidence capture was skipped (e.g., prerequisite failed)
    """

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class EvidenceItem(BaseModel):
    """Single piece of captured evidence.

    Represents one evidence item captured during the Verify phase,
    linking it to the plan step it verifies (if determinable).

    Attributes:
        name: Unique identifier for this evidence (e.g., "health_check", "home_screenshot")
        type: Type of evidence (cli, screenshot, api, log)
        path: Relative path within the evidence directory
        status: Status of this evidence (pass, fail, error, skipped)
        plan_step: Reference to plan.md step if linkable (e.g., "step_3")
        details: Type-specific details (e.g., exit_code, status_code, duration)

    Example:
        >>> item = EvidenceItem(
        ...     name="health_check",
        ...     type=EvidenceType.API,
        ...     path="api/health.json",
        ...     status=EvidenceStatus.PASS,
        ...     plan_step="step_1",
        ...     details={"method": "GET", "status_code": 200},
        ... )
    """

    name: str = Field(..., description="Unique identifier for this evidence")
    type: EvidenceType = Field(..., description="Type of evidence")
    path: str = Field(..., description="Relative path within evidence directory")
    status: EvidenceStatus = Field(..., description="Status of this evidence")
    plan_step: str | None = Field(
        default=None, description="Reference to plan.md step (e.g., 'step_3')"
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Type-specific details"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "health_check",
                "type": "api",
                "path": "api/health.json",
                "status": "pass",
                "plan_step": "step_1",
                "details": {"method": "GET", "status_code": 200, "duration_seconds": 0.012},
            }
        }
    }


class PlanStepCoverage(BaseModel):
    """Coverage information for a single plan step.

    Tracks which evidence items are linked to a specific plan step,
    enabling coverage analysis.

    Attributes:
        step_id: Identifier for the plan step (e.g., "step_1", "task_3")
        step_description: Human-readable description of the step
        evidence_items: Names of evidence items linked to this step
        covered: Whether this step has any linked evidence

    Example:
        >>> coverage = PlanStepCoverage(
        ...     step_id="step_1",
        ...     step_description="Implement health check endpoint",
        ...     evidence_items=["health_check", "status_endpoint"],
        ...     covered=True,
        ... )
    """

    step_id: str = Field(..., description="Plan step identifier")
    step_description: str | None = Field(
        default=None, description="Human-readable step description"
    )
    evidence_items: list[str] = Field(
        default_factory=list, description="Names of linked evidence items"
    )
    covered: bool = Field(default=False, description="Whether step has linked evidence")

    model_config = {
        "json_schema_extra": {
            "example": {
                "step_id": "step_1",
                "step_description": "Implement health check endpoint",
                "evidence_items": ["health_check"],
                "covered": True,
            }
        }
    }


class CoverageSummary(BaseModel):
    """Summary of evidence coverage for plan steps.

    Provides an overview of how well the evidence covers the plan,
    identifying gaps in verification.

    Attributes:
        total_plan_steps: Total number of steps parsed from plan.md
        covered_steps: Number of steps with at least one evidence item
        uncovered_steps: Number of steps without evidence
        coverage_percentage: Percentage of steps covered (0-100)
        uncovered_step_ids: List of step IDs without evidence

    Example:
        >>> summary = CoverageSummary(
        ...     total_plan_steps=5,
        ...     covered_steps=3,
        ...     uncovered_steps=2,
        ...     coverage_percentage=60.0,
        ...     uncovered_step_ids=["step_2", "step_5"],
        ... )
    """

    total_plan_steps: int = Field(..., ge=0, description="Total plan steps")
    covered_steps: int = Field(..., ge=0, description="Steps with evidence")
    uncovered_steps: int = Field(..., ge=0, description="Steps without evidence")
    coverage_percentage: float = Field(
        ..., ge=0, le=100, description="Coverage percentage"
    )
    uncovered_step_ids: list[str] = Field(
        default_factory=list, description="Step IDs without evidence"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_plan_steps": 5,
                "covered_steps": 3,
                "uncovered_steps": 2,
                "coverage_percentage": 60.0,
                "uncovered_step_ids": ["step_2", "step_5"],
            }
        }
    }


class EvidenceManifest(BaseModel):
    """Complete evidence manifest for a run.

    The manifest is the central index of all captured evidence,
    linking evidence items to plan steps for traceability and
    providing coverage analysis for the Validate phase.

    Attributes:
        run_id: Unique identifier for the run (ULID)
        generated_at: When the manifest was generated
        platform: Platform type that was detected (cli, web, backend, etc.)
        evidence_directory: Path to the evidence directory
        total_items: Total number of evidence items
        passed: Number of items with PASS status
        failed: Number of items with FAIL status
        errors: Number of items with ERROR status
        skipped: Number of items with SKIPPED status
        items: List of all evidence items
        coverage: Coverage summary (optional - only if plan.md exists)
        step_coverage: Per-step coverage details (optional)

    Example:
        >>> manifest = EvidenceManifest(
        ...     run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
        ...     platform="backend",
        ...     evidence_directory=".adw/runs/01HQXK/evidence",
        ...     total_items=8,
        ...     passed=6,
        ...     failed=1,
        ...     errors=0,
        ...     skipped=1,
        ...     items=[...],
        ... )
    """

    run_id: str = Field(..., description="Unique run identifier (ULID)")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When manifest was generated",
    )
    platform: str = Field(..., description="Detected platform type")
    evidence_directory: str = Field(..., description="Path to evidence directory")

    # Summary statistics
    total_items: int = Field(..., ge=0, description="Total evidence items")
    passed: int = Field(..., ge=0, description="Items with PASS status")
    failed: int = Field(..., ge=0, description="Items with FAIL status")
    errors: int = Field(..., ge=0, description="Items with ERROR status")
    skipped: int = Field(..., ge=0, description="Items with SKIPPED status")

    # Evidence items
    items: list[EvidenceItem] = Field(
        default_factory=list, description="All evidence items"
    )

    # Plan coverage (optional - only if plan.md exists)
    coverage: CoverageSummary | None = Field(
        default=None, description="Coverage summary"
    )
    step_coverage: list[PlanStepCoverage] | None = Field(
        default=None, description="Per-step coverage details"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "run_id": "01HQXK5P3Z7V8R2M4N6T9W1Y3C",
                "generated_at": "2026-01-03T10:30:45Z",
                "platform": "backend",
                "evidence_directory": ".adw/runs/01HQXK5P3Z7V8R2M4N6T9W1Y3C/evidence",
                "total_items": 8,
                "passed": 6,
                "failed": 1,
                "errors": 0,
                "skipped": 1,
                "items": [],
                "coverage": None,
                "step_coverage": None,
            }
        }
    }
