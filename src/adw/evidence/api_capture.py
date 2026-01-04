"""API evidence capture for backend projects.

This module provides the APICaptureStrategy class that handles
HTTP requests to configured endpoints and captures request/response
pairs for evidence gathering during the Verify phase.
"""

from datetime import datetime, timezone

import httpx

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    APIEvidenceResult,
    APIRequest,
    APIResponse,
    AuthConfig,
    AuthType,
    EndpointConfig,
)


class APICaptureStrategy:
    """Strategy for capturing API request/response pairs.

    Handles HTTP requests to configured endpoints and captures
    complete request/response details for evidence purposes.

    Attributes:
        base_url: Base URL for all API endpoints
        auth: Optional authentication configuration

    Example:
        >>> strategy = APICaptureStrategy(
        ...     base_url="http://localhost:8000",
        ...     auth=AuthConfig(type=AuthType.BEARER, token_env="API_TOKEN"),
        ... )
        >>> endpoint = EndpointConfig(name="health", path="/health")
        >>> result = strategy.call_endpoint(endpoint)
        >>> result.success
        True
    """

    def __init__(
        self,
        base_url: str,
        auth: AuthConfig | None = None,
    ) -> None:
        """Initialize the API capture strategy.

        Args:
            base_url: Base URL for all API endpoints
            auth: Optional authentication configuration
        """
        # Normalize base URL (remove trailing slash)
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self._logger = get_logger()

    def call_endpoint(self, config: EndpointConfig) -> APIEvidenceResult:
        """Call an API endpoint and capture the result.

        Makes an HTTP request to the specified endpoint and captures
        the full request/response details. Handles errors gracefully
        and returns a result even for failed requests.

        Args:
            config: Endpoint configuration with method, path, etc.

        Returns:
            APIEvidenceResult with request/response details
        """
        url = f"{self.base_url}{config.path}"
        headers = self._build_headers(config)

        self._logger.debug(
            LogCategory.STATE,
            f"Calling endpoint: {config.method} {url} (name={config.name})",
        )

        start_time = datetime.now(timezone.utc)

        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.request(
                    method=config.method,
                    url=url,
                    headers=headers,
                    json=config.body if config.body else None,
                )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Build request record
            request = APIRequest(
                method=config.method,
                url=url,
                headers=self._redact_auth_headers(headers) if headers else None,
                body=config.body,
            )

            # Build response record
            api_response = APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers) if response.headers else None,
                body=self._parse_response_body(response.text),
                duration_seconds=duration,
            )

            # Determine success and status matching
            success = response.is_success
            status_match = True
            if config.expected_status is not None:
                status_match = response.status_code == config.expected_status

            return APIEvidenceResult(
                endpoint_name=config.name,
                request=request,
                response=api_response,
                success=success,
                expected_status=config.expected_status,
                status_match=status_match,
            )

        except httpx.TimeoutException as e:
            return self._error_result(
                config=config,
                url=url,
                headers=headers,
                error=f"Request timeout: {e}",
                start_time=start_time,
            )

        except httpx.ConnectError as e:
            return self._error_result(
                config=config,
                url=url,
                headers=headers,
                error=f"Connection error: {e}",
                start_time=start_time,
            )

        except httpx.HTTPError as e:
            return self._error_result(
                config=config,
                url=url,
                headers=headers,
                error=f"HTTP error: {e}",
                start_time=start_time,
            )

    def _build_headers(self, config: EndpointConfig) -> dict[str, str] | None:
        """Build headers for the request.

        Combines endpoint-specific headers with authentication headers.

        Args:
            config: Endpoint configuration

        Returns:
            Combined headers dictionary or None
        """
        headers: dict[str, str] = {}

        # Add endpoint-specific headers
        if config.headers:
            headers.update(config.headers)

        # Add auth headers if configured
        # (Auth header injection will be implemented in Task 4)

        return headers if headers else None

    def _redact_auth_headers(
        self, headers: dict[str, str] | None
    ) -> dict[str, str] | None:
        """Redact sensitive values from headers for logging.

        Args:
            headers: Original headers

        Returns:
            Headers with auth values redacted
        """
        if not headers:
            return None

        redacted = dict(headers)
        sensitive_keys = ["authorization", "x-api-key", "api-key", "token"]

        for key in redacted:
            if key.lower() in sensitive_keys:
                redacted[key] = "[REDACTED]"

        return redacted

    def _parse_response_body(self, text: str) -> str | dict:
        """Parse response body, attempting JSON decode.

        Args:
            text: Raw response text

        Returns:
            Parsed JSON dict or original text string
        """
        if not text:
            return ""

        try:
            import json

            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text

    def _error_result(
        self,
        config: EndpointConfig,
        url: str,
        headers: dict[str, str] | None,
        error: str,
        start_time: datetime,
    ) -> APIEvidenceResult:
        """Create an error result for failed requests.

        Args:
            config: Endpoint configuration
            url: Full URL that was called
            headers: Request headers
            error: Error message
            start_time: When the request started

        Returns:
            APIEvidenceResult with error details
        """
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        return APIEvidenceResult(
            endpoint_name=config.name,
            request=APIRequest(
                method=config.method,
                url=url,
                headers=self._redact_auth_headers(headers),
                body=config.body,
            ),
            response=APIResponse(
                status_code=0,
                body="",
                duration_seconds=duration,
            ),
            success=False,
            expected_status=config.expected_status,
            status_match=False,
            error=error,
        )
