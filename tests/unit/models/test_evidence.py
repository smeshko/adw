"""Tests for evidence-related models.

This module tests all evidence-related models:
- PlatformType, Confidence, and PlatformDetectionResult for platform detection
- API evidence models: EndpointConfig, AuthConfig, APIRequest, APIResponse,
  APIEvidenceResult, APIEvidenceSummary
- Web screenshot models: RouteConfig, ViewportConfig, ScreenshotResult,
  WebEvidenceSummary
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from adw.models.evidence import (
    APIEvidenceResult,
    APIEvidenceSummary,
    APIRequest,
    APIResponse,
    AuthConfig,
    AuthType,
    Confidence,
    EndpointConfig,
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


# ==============================================================================
# API Evidence Models Tests (Story 8.4)
# ==============================================================================


class TestEndpointConfig:
    """Tests for EndpointConfig model."""

    def test_create_basic_endpoint(self) -> None:
        """Test creating a basic endpoint configuration."""
        endpoint = EndpointConfig(
            name="health",
            path="/health",
        )
        assert endpoint.name == "health"
        assert endpoint.path == "/health"
        assert endpoint.method == "GET"  # Default
        assert endpoint.headers is None
        assert endpoint.body is None
        assert endpoint.expected_status is None
        assert endpoint.timeout_seconds == 30  # Default

    def test_create_post_endpoint_with_body(self) -> None:
        """Test creating a POST endpoint with body."""
        endpoint = EndpointConfig(
            name="create_user",
            method="POST",
            path="/users",
            body={"name": "test", "email": "test@example.com"},
            expected_status=201,
        )
        assert endpoint.method == "POST"
        assert endpoint.body == {"name": "test", "email": "test@example.com"}
        assert endpoint.expected_status == 201

    def test_endpoint_with_headers(self) -> None:
        """Test endpoint with custom headers."""
        endpoint = EndpointConfig(
            name="get_users",
            path="/users",
            headers={"Accept": "application/json", "X-Custom": "value"},
        )
        assert endpoint.headers == {"Accept": "application/json", "X-Custom": "value"}

    def test_endpoint_json_serialization(self) -> None:
        """Test JSON serialization of endpoint config."""
        endpoint = EndpointConfig(
            name="test",
            method="DELETE",
            path="/items/123",
            timeout_seconds=60,
        )
        data = endpoint.model_dump()
        assert data["name"] == "test"
        assert data["method"] == "DELETE"
        assert data["path"] == "/items/123"
        assert data["timeout_seconds"] == 60

    def test_endpoint_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            EndpointConfig(name="test")  # Missing path

        with pytest.raises(ValidationError):
            EndpointConfig(path="/test")  # Missing name


class TestAuthConfig:
    """Tests for AuthConfig model."""

    def test_create_bearer_auth(self) -> None:
        """Test creating bearer token auth config."""
        auth = AuthConfig(
            type=AuthType.BEARER,
            token_env="API_TOKEN",
        )
        assert auth.type == AuthType.BEARER
        assert auth.token_env == "API_TOKEN"
        assert auth.header is None
        assert auth.key_env is None

    def test_create_api_key_auth(self) -> None:
        """Test creating API key auth config."""
        auth = AuthConfig(
            type=AuthType.API_KEY,
            header="X-API-Key",
            key_env="API_KEY",
        )
        assert auth.type == AuthType.API_KEY
        assert auth.header == "X-API-Key"
        assert auth.key_env == "API_KEY"

    def test_auth_type_enum_values(self) -> None:
        """Test AuthType enum values."""
        assert AuthType.BEARER == "bearer"
        assert AuthType.API_KEY == "api_key"
        assert AuthType.BASIC == "basic"


class TestAPIRequest:
    """Tests for APIRequest model."""

    def test_create_get_request(self) -> None:
        """Test creating a GET request."""
        request = APIRequest(
            method="GET",
            url="http://localhost:8000/health",
        )
        assert request.method == "GET"
        assert request.url == "http://localhost:8000/health"
        assert request.headers is None
        assert request.body is None

    def test_create_post_request_with_body(self) -> None:
        """Test creating a POST request with body."""
        request = APIRequest(
            method="POST",
            url="http://localhost:8000/users",
            headers={"Content-Type": "application/json"},
            body={"name": "test"},
        )
        assert request.method == "POST"
        assert request.headers == {"Content-Type": "application/json"}
        assert request.body == {"name": "test"}

    def test_request_json_serialization(self) -> None:
        """Test JSON serialization of request."""
        request = APIRequest(
            method="PUT",
            url="http://localhost:8000/items/1",
            body={"value": 42},
        )
        data = request.model_dump()
        assert data["method"] == "PUT"
        assert data["url"] == "http://localhost:8000/items/1"
        assert data["body"] == {"value": 42}


class TestAPIResponse:
    """Tests for APIResponse model."""

    def test_create_success_response(self) -> None:
        """Test creating a success response."""
        response = APIResponse(
            status_code=200,
            body={"status": "ok"},
            duration_seconds=0.045,
        )
        assert response.status_code == 200
        assert response.body == {"status": "ok"}
        assert response.duration_seconds == 0.045
        assert response.headers is None

    def test_create_response_with_headers(self) -> None:
        """Test creating response with headers."""
        response = APIResponse(
            status_code=201,
            headers={"Content-Type": "application/json", "X-Request-Id": "abc123"},
            body={"id": 123},
            duration_seconds=0.123,
        )
        assert response.headers == {
            "Content-Type": "application/json",
            "X-Request-Id": "abc123",
        }

    def test_response_with_string_body(self) -> None:
        """Test response with string body (non-JSON)."""
        response = APIResponse(
            status_code=200,
            body="OK",
            duration_seconds=0.01,
        )
        assert response.body == "OK"

    def test_response_json_serialization(self) -> None:
        """Test JSON serialization of response."""
        response = APIResponse(
            status_code=404,
            body={"error": "Not found"},
            duration_seconds=0.05,
        )
        data = response.model_dump()
        assert data["status_code"] == 404
        assert data["body"] == {"error": "Not found"}


class TestAPIEvidenceResult:
    """Tests for APIEvidenceResult model."""

    def test_create_evidence_result(self) -> None:
        """Test creating an API evidence result."""
        result = APIEvidenceResult(
            endpoint_name="health",
            request=APIRequest(method="GET", url="http://localhost:8000/health"),
            response=APIResponse(
                status_code=200, body={"status": "ok"}, duration_seconds=0.01
            ),
            success=True,
        )
        assert result.endpoint_name == "health"
        assert result.success is True
        assert result.error is None
        assert result.status_match is True  # Default

    def test_evidence_result_with_expected_status(self) -> None:
        """Test evidence result with status matching."""
        result = APIEvidenceResult(
            endpoint_name="create_user",
            request=APIRequest(
                method="POST",
                url="http://localhost:8000/users",
                body={"name": "test"},
            ),
            response=APIResponse(status_code=201, body={"id": 1}, duration_seconds=0.1),
            success=True,
            expected_status=201,
            status_match=True,
        )
        assert result.expected_status == 201
        assert result.status_match is True

    def test_evidence_result_status_mismatch(self) -> None:
        """Test evidence result with status mismatch."""
        result = APIEvidenceResult(
            endpoint_name="get_item",
            request=APIRequest(method="GET", url="http://localhost:8000/items/999"),
            response=APIResponse(
                status_code=404, body={"error": "Not found"}, duration_seconds=0.05
            ),
            success=False,
            expected_status=200,
            status_match=False,
        )
        assert result.success is False
        assert result.status_match is False

    def test_evidence_result_with_error(self) -> None:
        """Test evidence result with error."""
        result = APIEvidenceResult(
            endpoint_name="timeout_endpoint",
            request=APIRequest(method="GET", url="http://localhost:8000/slow"),
            response=APIResponse(status_code=0, body="", duration_seconds=30.0),
            success=False,
            error="Connection timeout after 30 seconds",
        )
        assert result.success is False
        assert result.error == "Connection timeout after 30 seconds"

    def test_evidence_result_has_captured_at(self) -> None:
        """Test that evidence result has captured_at timestamp."""
        before = datetime.now(UTC)
        result = APIEvidenceResult(
            endpoint_name="test",
            request=APIRequest(method="GET", url="http://localhost:8000/test"),
            response=APIResponse(status_code=200, body="", duration_seconds=0.01),
            success=True,
        )
        after = datetime.now(UTC)
        assert before <= result.captured_at <= after

    def test_evidence_result_json_serialization(self) -> None:
        """Test JSON serialization of evidence result."""
        result = APIEvidenceResult(
            endpoint_name="test",
            request=APIRequest(method="GET", url="http://localhost:8000/test"),
            response=APIResponse(status_code=200, body="OK", duration_seconds=0.01),
            success=True,
        )
        data = result.model_dump()
        assert data["endpoint_name"] == "test"
        assert data["request"]["method"] == "GET"
        assert data["response"]["status_code"] == 200
        assert "captured_at" in data


class TestAPIEvidenceSummary:
    """Tests for APIEvidenceSummary model."""

    def test_create_summary(self) -> None:
        """Test creating an evidence summary."""
        results = [
            APIEvidenceResult(
                endpoint_name="health",
                request=APIRequest(method="GET", url="http://localhost:8000/health"),
                response=APIResponse(
                    status_code=200, body={"status": "ok"}, duration_seconds=0.01
                ),
                success=True,
            ),
            APIEvidenceResult(
                endpoint_name="users",
                request=APIRequest(method="GET", url="http://localhost:8000/users"),
                response=APIResponse(
                    status_code=200, body={"users": []}, duration_seconds=0.05
                ),
                success=True,
            ),
        ]
        summary = APIEvidenceSummary(
            base_url="http://localhost:8000",
            total_endpoints=2,
            successful=2,
            failed=0,
            status_mismatches=0,
            results=results,
        )
        assert summary.base_url == "http://localhost:8000"
        assert summary.total_endpoints == 2
        assert summary.successful == 2
        assert summary.failed == 0
        assert len(summary.results) == 2

    def test_summary_with_failures(self) -> None:
        """Test summary with failed endpoints."""
        results = [
            APIEvidenceResult(
                endpoint_name="health",
                request=APIRequest(method="GET", url="http://localhost:8000/health"),
                response=APIResponse(
                    status_code=200, body={"status": "ok"}, duration_seconds=0.01
                ),
                success=True,
            ),
            APIEvidenceResult(
                endpoint_name="broken",
                request=APIRequest(method="GET", url="http://localhost:8000/broken"),
                response=APIResponse(
                    status_code=500, body={"error": "Internal"}, duration_seconds=0.1
                ),
                success=False,
            ),
        ]
        summary = APIEvidenceSummary(
            base_url="http://localhost:8000",
            total_endpoints=2,
            successful=1,
            failed=1,
            status_mismatches=0,
            results=results,
        )
        assert summary.successful == 1
        assert summary.failed == 1

    def test_summary_json_serialization(self) -> None:
        """Test JSON serialization of summary."""
        summary = APIEvidenceSummary(
            base_url="http://localhost:8000",
            total_endpoints=0,
            successful=0,
            failed=0,
            status_mismatches=0,
            results=[],
        )
        data = summary.model_dump()
        assert data["base_url"] == "http://localhost:8000"
        assert data["total_endpoints"] == 0
        assert data["results"] == []

    def test_summary_has_captured_at(self) -> None:
        """Test that summary has captured_at timestamp."""
        before = datetime.now(UTC)
        summary = APIEvidenceSummary(
            base_url="http://localhost:8000",
            total_endpoints=0,
            successful=0,
            failed=0,
            status_mismatches=0,
            results=[],
        )
        after = datetime.now(UTC)
        assert before <= summary.captured_at <= after


# ==============================================================================
# Web Evidence Models Tests
# ==============================================================================


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


# =============================================================================
# Mobile Evidence Models Tests (Story 8.3b)
# =============================================================================


class TestMobileDeviceType:
    """Tests for MobileDeviceType enum."""

    def test_mobile_device_type_values(self) -> None:
        """Test all mobile device type values exist."""
        from adw.models.evidence import MobileDeviceType

        assert MobileDeviceType.IOS.value == "ios"
        assert MobileDeviceType.ANDROID.value == "android"
        assert MobileDeviceType.FLUTTER_IOS.value == "flutter_ios"
        assert MobileDeviceType.FLUTTER_ANDROID.value == "flutter_android"

    def test_mobile_device_type_is_string_enum(self) -> None:
        """Test MobileDeviceType is a string enum."""
        from adw.models.evidence import MobileDeviceType

        assert isinstance(MobileDeviceType.IOS, str)
        assert MobileDeviceType.IOS.value == "ios"

    def test_mobile_device_type_from_string(self) -> None:
        """Test creating MobileDeviceType from string."""
        from adw.models.evidence import MobileDeviceType

        assert MobileDeviceType("ios") == MobileDeviceType.IOS
        assert MobileDeviceType("android") == MobileDeviceType.ANDROID

    def test_invalid_mobile_device_type_raises(self) -> None:
        """Test invalid mobile device type raises ValueError."""
        from adw.models.evidence import MobileDeviceType

        with pytest.raises(ValueError):
            MobileDeviceType("invalid")


class TestMobileScreenConfig:
    """Tests for MobileScreenConfig model."""

    def test_create_basic_screen_config(self) -> None:
        """Test creating a basic screen config."""
        from adw.models.evidence import MobileScreenConfig

        config = MobileScreenConfig(name="home")
        assert config.name == "home"
        assert config.deeplink is None
        assert config.capture_delay_ms == 500

    def test_create_screen_config_with_deeplink(self) -> None:
        """Test creating a screen config with deeplink."""
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

        config = MobileScreenConfig(name="home", deeplink="myapp://home")
        data = config.model_dump()
        assert data["name"] == "home"
        assert data["deeplink"] == "myapp://home"

    def test_screen_config_name_required(self) -> None:
        """Test that name is required."""
        from adw.models.evidence import MobileScreenConfig

        with pytest.raises(ValidationError):
            MobileScreenConfig()


class TestMobileScreenshotResult:
    """Tests for MobileScreenshotResult model."""

    def test_create_successful_screenshot_result(self) -> None:
        """Test creating a successful screenshot result."""
        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/home.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            success=True,
        )
        assert result.path == Path("/tmp/home.png")
        assert result.screen_name == "home"
        assert result.device_type == MobileDeviceType.IOS
        assert result.success is True
        assert result.error is None

    def test_create_failed_screenshot_result(self) -> None:
        """Test creating a failed screenshot result."""
        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/profile.png"),
            screen_name="profile",
            device_type=MobileDeviceType.ANDROID,
            success=False,
            error="Device not found",
        )
        assert result.success is False
        assert result.error == "Device not found"

    def test_screenshot_result_with_device_info(self) -> None:
        """Test screenshot result with device info."""
        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/home.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            device_name="iPhone 15 Pro",
            os_version="17.2",
            success=True,
        )
        assert result.device_name == "iPhone 15 Pro"
        assert result.os_version == "17.2"

    def test_screenshot_result_has_captured_at(self) -> None:
        """Test screenshot result has captured_at timestamp."""
        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/home.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            success=True,
        )
        assert result.captured_at is not None

    def test_screenshot_result_json_serialization(self) -> None:
        """Test JSON serialization of screenshot result."""
        from adw.models.evidence import MobileDeviceType, MobileScreenshotResult

        result = MobileScreenshotResult(
            path=Path("/tmp/home.png"),
            screen_name="home",
            device_type=MobileDeviceType.IOS,
            success=True,
        )
        data = result.model_dump()
        assert data["screen_name"] == "home"
        assert data["device_type"] == "ios"


class TestMobileEvidenceSummary:
    """Tests for MobileEvidenceSummary model."""

    def test_create_empty_summary(self) -> None:
        """Test creating an empty summary."""
        from adw.models.evidence import MobileEvidenceSummary

        summary = MobileEvidenceSummary()
        assert summary.total_screenshots == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.results == []

    def test_create_summary_with_results(self) -> None:
        """Test creating a summary with results."""
        from adw.models.evidence import (
            MobileDeviceType,
            MobileEvidenceSummary,
            MobileScreenshotResult,
        )

        results = [
            MobileScreenshotResult(
                path=Path("/tmp/home.png"),
                screen_name="home",
                device_type=MobileDeviceType.IOS,
                success=True,
            ),
            MobileScreenshotResult(
                path=Path("/tmp/profile.png"),
                screen_name="profile",
                device_type=MobileDeviceType.IOS,
                success=False,
                error="Navigation failed",
            ),
        ]
        summary = MobileEvidenceSummary(
            total_screenshots=2,
            successful=1,
            failed=1,
            results=results,
        )
        assert summary.total_screenshots == 2
        assert len(summary.results) == 2

    def test_summary_json_serialization(self) -> None:
        """Test JSON serialization of summary."""
        from adw.models.evidence import MobileEvidenceSummary

        summary = MobileEvidenceSummary(
            total_screenshots=5,
            successful=4,
            failed=1,
        )
        data = summary.model_dump()
        assert data["total_screenshots"] == 5
        assert data["successful"] == 4

    def test_summary_has_captured_at(self) -> None:
        """Test summary has captured_at timestamp."""
        from adw.models.evidence import MobileEvidenceSummary

        summary = MobileEvidenceSummary()
        assert summary.captured_at is not None
