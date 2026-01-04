"""Evidence-related models for ADW evidence gathering.

This module contains models for platform detection, evidence gathering
strategy selection, and API evidence capture during the Verify phase.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

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

    platform: PlatformType = Field(
        ..., description="The detected platform type"
    )
    confidence: Confidence = Field(
        ..., description="How confident the detection is"
    )
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
    return datetime.now(timezone.utc)


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
