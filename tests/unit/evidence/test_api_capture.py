"""Tests for API evidence capture functionality.

This module tests the APICaptureStrategy class that handles
HTTP requests and response capture for evidence gathering.
"""

from unittest.mock import MagicMock, patch

from adw.evidence.api_capture import APICaptureStrategy
from adw.models.evidence import (
    APIEvidenceResult,
    APIRequest,
    APIResponse,
    AuthConfig,
    AuthType,
    EndpointConfig,
)


class TestAPICaptureStrategy:
    """Tests for APICaptureStrategy class."""

    def test_create_strategy(self) -> None:
        """Test creating an API capture strategy."""
        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        assert strategy.base_url == "http://localhost:8000"

    def test_create_strategy_with_trailing_slash(self) -> None:
        """Test that trailing slash is normalized."""
        strategy = APICaptureStrategy(base_url="http://localhost:8000/")
        assert strategy.base_url == "http://localhost:8000"

    def test_create_strategy_with_auth(self) -> None:
        """Test creating strategy with auth config."""
        auth = AuthConfig(type=AuthType.BEARER, token_env="API_TOKEN")
        strategy = APICaptureStrategy(
            base_url="http://localhost:8000",
            auth=auth,
        )
        assert strategy.auth == auth


class TestCallEndpoint:
    """Tests for the call_endpoint method."""

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_call_get_endpoint(self, mock_client_class: MagicMock) -> None:
        """Test calling a GET endpoint."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"status": "ok"}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        # Execute
        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="health", path="/health")
        result = strategy.call_endpoint(endpoint)

        # Verify
        assert isinstance(result, APIEvidenceResult)
        assert result.endpoint_name == "health"
        assert result.success is True
        assert result.request.method == "GET"
        assert result.request.url == "http://localhost:8000/health"
        assert result.response.status_code == 200

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_call_post_endpoint(self, mock_client_class: MagicMock) -> None:
        """Test calling a POST endpoint with body."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"id": 1}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        # Execute
        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="create_user",
            method="POST",
            path="/users",
            body={"name": "test"},
        )
        result = strategy.call_endpoint(endpoint)

        # Verify
        assert result.request.method == "POST"
        assert result.request.body == {"name": "test"}
        assert result.response.status_code == 201

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_call_put_endpoint(self, mock_client_class: MagicMock) -> None:
        """Test calling a PUT endpoint."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"updated": true}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="update_user",
            method="PUT",
            path="/users/1",
            body={"name": "updated"},
        )
        result = strategy.call_endpoint(endpoint)

        assert result.request.method == "PUT"
        assert result.success is True

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_call_delete_endpoint(self, mock_client_class: MagicMock) -> None:
        """Test calling a DELETE endpoint."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="delete_user",
            method="DELETE",
            path="/users/1",
        )
        result = strategy.call_endpoint(endpoint)

        assert result.request.method == "DELETE"
        assert result.response.status_code == 204

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_call_patch_endpoint(self, mock_client_class: MagicMock) -> None:
        """Test calling a PATCH endpoint."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"patched": true}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="patch_user",
            method="PATCH",
            path="/users/1",
            body={"name": "patched"},
        )
        result = strategy.call_endpoint(endpoint)

        assert result.request.method == "PATCH"
        assert result.success is True


class TestTimeoutHandling:
    """Tests for timeout handling."""

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_timeout_returns_error_result(self, mock_client_class: MagicMock) -> None:
        """Test that timeout returns error result instead of raising."""
        import httpx

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = httpx.TimeoutException("Connection timeout")

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="slow_endpoint",
            path="/slow",
            timeout_seconds=5,
        )
        result = strategy.call_endpoint(endpoint)

        assert result.success is False
        assert result.error is not None
        assert "timeout" in result.error.lower()

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_connection_error_returns_error_result(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that connection error returns error result."""
        import httpx

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = httpx.ConnectError("Connection refused")

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="unreachable", path="/api")
        result = strategy.call_endpoint(endpoint)

        assert result.success is False
        assert result.error is not None


class TestRequestResponseCapture:
    """Tests for request/response capture functionality (Task 3)."""

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_captures_full_request_details(self, mock_client_class: MagicMock) -> None:
        """Test that full request details are captured."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "{}"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="test",
            method="POST",
            path="/api/test",
            headers={"X-Custom": "value"},
            body={"key": "data"},
        )
        result = strategy.call_endpoint(endpoint)

        # Verify request details captured
        assert result.request.method == "POST"
        assert result.request.url == "http://localhost:8000/api/test"
        assert result.request.headers == {"X-Custom": "value"}
        assert result.request.body == {"key": "data"}

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_captures_full_response_details(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that full response details are captured."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-Request-Id": "abc123",
        }
        mock_response.text = '{"id": 42, "created": true}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="test", path="/test")
        result = strategy.call_endpoint(endpoint)

        # Verify response details captured
        assert result.response.status_code == 201
        assert result.response.headers is not None
        assert "Content-Type" in result.response.headers
        assert result.response.body == {"id": 42, "created": True}
        assert result.response.duration_seconds >= 0

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_preserves_json_response_as_dict(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that JSON responses are parsed to dict."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"users": [{"id": 1}, {"id": 2}]}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="test", path="/test")
        result = strategy.call_endpoint(endpoint)

        assert isinstance(result.response.body, dict)
        assert result.response.body == {"users": [{"id": 1}, {"id": 2}]}

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_preserves_non_json_response_as_string(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that non-JSON responses are kept as string."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "OK - Server is running"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="test", path="/test")
        result = strategy.call_endpoint(endpoint)

        assert isinstance(result.response.body, str)
        assert result.response.body == "OK - Server is running"

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_calculates_request_duration(self, mock_client_class: MagicMock) -> None:
        """Test that request duration is calculated."""
        import time

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate a small delay
        def slow_request(*args, **kwargs):
            time.sleep(0.01)  # 10ms
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.text = "{}"
            mock_response.is_success = True
            return mock_response

        mock_client.request.side_effect = slow_request

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="test", path="/test")
        result = strategy.call_endpoint(endpoint)

        # Duration should be at least 10ms
        assert result.response.duration_seconds >= 0.01


class TestAuthenticationSupport:
    """Tests for authentication support (Task 4)."""

    @patch("adw.evidence.api_capture.httpx.Client")
    @patch.dict("os.environ", {"API_TOKEN": "secret-bearer-token"})
    def test_bearer_token_auth_from_env(self, mock_client_class: MagicMock) -> None:
        """Test bearer token auth from environment variable."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "{}"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        auth = AuthConfig(type=AuthType.BEARER, token_env="API_TOKEN")
        strategy = APICaptureStrategy(base_url="http://localhost:8000", auth=auth)
        endpoint = EndpointConfig(name="test", path="/test")
        strategy.call_endpoint(endpoint)

        # Verify auth header was included in request
        call_kwargs = mock_client.request.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer secret-bearer-token"

    @patch("adw.evidence.api_capture.httpx.Client")
    @patch.dict("os.environ", {"API_KEY": "my-api-key"})
    def test_api_key_auth_from_env(self, mock_client_class: MagicMock) -> None:
        """Test API key auth from environment variable."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "{}"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        auth = AuthConfig(type=AuthType.API_KEY, header="X-API-Key", key_env="API_KEY")
        strategy = APICaptureStrategy(base_url="http://localhost:8000", auth=auth)
        endpoint = EndpointConfig(name="test", path="/test")
        strategy.call_endpoint(endpoint)

        # Verify API key header was included
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs["headers"]["X-API-Key"] == "my-api-key"

    @patch("adw.evidence.api_capture.httpx.Client")
    @patch.dict("os.environ", {"API_TOKEN": "secret-token"}, clear=False)
    def test_auth_headers_redacted_in_result(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that auth headers are redacted in captured result."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "{}"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        auth = AuthConfig(type=AuthType.BEARER, token_env="API_TOKEN")
        strategy = APICaptureStrategy(base_url="http://localhost:8000", auth=auth)
        endpoint = EndpointConfig(name="test", path="/test")
        result = strategy.call_endpoint(endpoint)

        # Captured result should have redacted auth header
        if result.request.headers and "Authorization" in result.request.headers:
            assert result.request.headers["Authorization"] == "[REDACTED]"

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_missing_env_var_handles_gracefully(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test graceful handling when env var is missing."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "{}"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        # Auth config points to non-existent env var
        auth = AuthConfig(type=AuthType.BEARER, token_env="NONEXISTENT_TOKEN")
        strategy = APICaptureStrategy(base_url="http://localhost:8000", auth=auth)
        endpoint = EndpointConfig(name="test", path="/test")

        # Should not raise, but may warn
        result = strategy.call_endpoint(endpoint)
        assert result is not None

    @patch("adw.evidence.api_capture.httpx.Client")
    @patch.dict("os.environ", {"BASIC_USER": "admin", "BASIC_PASS": "secret123"})
    def test_basic_auth_from_env(self, mock_client_class: MagicMock) -> None:
        """Test basic authentication from environment variables."""
        import base64

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "{}"
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        auth = AuthConfig(
            type=AuthType.BASIC,
            token_env="BASIC_USER",  # username
            key_env="BASIC_PASS",  # password
        )
        strategy = APICaptureStrategy(base_url="http://localhost:8000", auth=auth)
        endpoint = EndpointConfig(name="test", path="/test")
        strategy.call_endpoint(endpoint)

        # Verify basic auth header was included
        call_kwargs = mock_client.request.call_args[1]
        assert "headers" in call_kwargs
        expected_credentials = base64.b64encode(b"admin:secret123").decode()
        assert call_kwargs["headers"]["Authorization"] == f"Basic {expected_credentials}"


class TestSummaryGeneration:
    """Tests for summary generation (Task 7)."""

    def test_generate_summary_from_results(self) -> None:
        """Test generating summary from a list of results."""
        from adw.evidence.api_capture import generate_summary

        results = [
            APIEvidenceResult(
                endpoint_name="health",
                request=APIRequest(method="GET", url="http://localhost/health"),
                response=APIResponse(
                    status_code=200, body={"status": "ok"}, duration_seconds=0.01
                ),
                success=True,
            ),
            APIEvidenceResult(
                endpoint_name="users",
                request=APIRequest(method="GET", url="http://localhost/users"),
                response=APIResponse(
                    status_code=200, body={"users": []}, duration_seconds=0.02
                ),
                success=True,
            ),
        ]

        summary = generate_summary(
            base_url="http://localhost:8000",
            results=results,
        )

        assert summary.base_url == "http://localhost:8000"
        assert summary.total_endpoints == 2
        assert summary.successful == 2
        assert summary.failed == 0
        assert len(summary.results) == 2

    def test_generate_summary_with_failures(self) -> None:
        """Test generating summary with failed endpoints."""
        from adw.evidence.api_capture import generate_summary

        results = [
            APIEvidenceResult(
                endpoint_name="health",
                request=APIRequest(method="GET", url="http://localhost/health"),
                response=APIResponse(
                    status_code=200, body={}, duration_seconds=0.01
                ),
                success=True,
            ),
            APIEvidenceResult(
                endpoint_name="broken",
                request=APIRequest(method="GET", url="http://localhost/broken"),
                response=APIResponse(
                    status_code=500, body={"error": "Internal"}, duration_seconds=0.05
                ),
                success=False,
            ),
        ]

        summary = generate_summary(base_url="http://localhost", results=results)

        assert summary.total_endpoints == 2
        assert summary.successful == 1
        assert summary.failed == 1

    def test_generate_summary_with_status_mismatches(self) -> None:
        """Test generating summary counting status mismatches."""
        from adw.evidence.api_capture import generate_summary

        results = [
            APIEvidenceResult(
                endpoint_name="create",
                request=APIRequest(method="POST", url="http://localhost/items"),
                response=APIResponse(
                    status_code=400, body={"error": "Bad"}, duration_seconds=0.01
                ),
                success=False,
                expected_status=201,
                status_match=False,
            ),
            APIEvidenceResult(
                endpoint_name="get",
                request=APIRequest(method="GET", url="http://localhost/items/1"),
                response=APIResponse(
                    status_code=200, body={}, duration_seconds=0.01
                ),
                success=True,
                expected_status=200,
                status_match=True,
            ),
        ]

        summary = generate_summary(base_url="http://localhost", results=results)

        assert summary.status_mismatches == 1


class TestErrorResponseCapture:
    """Tests for error response capture (AC: error responses captured for verification)."""

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_captures_4xx_error_response_body(self, mock_client_class: MagicMock) -> None:
        """Test that 4xx error responses are fully captured with body content."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"error": "Bad Request", "details": "Missing required field"}'
        mock_response.is_success = False
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="create_item", method="POST", path="/items")
        result = strategy.call_endpoint(endpoint)

        # Verify error response is fully captured for verification
        assert result.success is False
        assert result.response.status_code == 400
        assert result.response.body == {"error": "Bad Request", "details": "Missing required field"}
        assert result.error is None  # HTTP errors don't set error field

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_captures_5xx_error_response_body(self, mock_client_class: MagicMock) -> None:
        """Test that 5xx error responses are fully captured with body content."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"error": "Internal Server Error", "trace_id": "abc123"}'
        mock_response.is_success = False
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="health", path="/health")
        result = strategy.call_endpoint(endpoint)

        # Verify 5xx error response is fully captured
        assert result.success is False
        assert result.response.status_code == 500
        assert result.response.body == {"error": "Internal Server Error", "trace_id": "abc123"}
        assert result.response.headers is not None

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_captures_error_response_with_non_json_body(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that error responses with non-JSON bodies are captured as strings."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.text = "Service Unavailable - Server is overloaded"
        mock_response.is_success = False
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(name="api", path="/api")
        result = strategy.call_endpoint(endpoint)

        # Verify non-JSON error body is captured as string
        assert result.success is False
        assert result.response.status_code == 503
        assert result.response.body == "Service Unavailable - Server is overloaded"


class TestStatusMatching:
    """Tests for expected status matching."""

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_expected_status_match(self, mock_client_class: MagicMock) -> None:
        """Test status matching when expected status matches actual."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = '{"id": 1}'
        mock_response.is_success = True
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="create",
            method="POST",
            path="/items",
            expected_status=201,
        )
        result = strategy.call_endpoint(endpoint)

        assert result.expected_status == 201
        assert result.status_match is True

    @patch("adw.evidence.api_capture.httpx.Client")
    def test_expected_status_mismatch(self, mock_client_class: MagicMock) -> None:
        """Test status matching when expected status differs from actual."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {}
        mock_response.text = '{"error": "bad request"}'
        mock_response.is_success = False
        mock_client.request.return_value = mock_response

        strategy = APICaptureStrategy(base_url="http://localhost:8000")
        endpoint = EndpointConfig(
            name="create",
            method="POST",
            path="/items",
            expected_status=201,
        )
        result = strategy.call_endpoint(endpoint)

        assert result.expected_status == 201
        assert result.response.status_code == 400
        assert result.status_match is False
