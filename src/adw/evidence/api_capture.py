"""API evidence capture for backend projects.

This module provides the APICaptureStrategy class that handles
HTTP requests to configured endpoints and captures request/response
pairs for evidence gathering during the Verify phase.
"""

import base64
import json
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    APIEvidenceResult,
    APIEvidenceSummary,
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

        start_time = datetime.now(UTC)

        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.request(
                    method=config.method,
                    url=url,
                    headers=headers,
                    json=config.body if config.body else None,
                )

            duration = (datetime.now(UTC) - start_time).total_seconds()

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
        if self.auth:
            auth_headers = self._get_auth_headers()
            if auth_headers:
                headers.update(auth_headers)

        return headers if headers else None

    def _get_auth_headers(self) -> dict[str, str] | None:
        """Get authentication headers from config and environment.

        Reads auth tokens from environment variables based on
        the authentication configuration.

        Returns:
            Dictionary of auth headers or None if not configured/available
        """
        if not self.auth:
            return None

        if self.auth.type == AuthType.BEARER:
            if self.auth.token_env:
                token = os.environ.get(self.auth.token_env)
                if token:
                    return {"Authorization": f"Bearer {token}"}
                else:
                    self._logger.warn(
                        LogCategory.STATE,
                        f"Bearer token env var '{self.auth.token_env}' not set",
                    )
            return None

        elif self.auth.type == AuthType.API_KEY:
            if self.auth.key_env and self.auth.header:
                key = os.environ.get(self.auth.key_env)
                if key:
                    return {self.auth.header: key}
                else:
                    self._logger.warn(
                        LogCategory.STATE,
                        f"API key env var '{self.auth.key_env}' not set",
                    )
            return None

        elif self.auth.type == AuthType.BASIC:
            # Basic auth requires username and password from env vars
            # Convention: token_env for username, key_env for password
            if self.auth.token_env and self.auth.key_env:
                username = os.environ.get(self.auth.token_env)
                password = os.environ.get(self.auth.key_env)
                if username and password:
                    credentials = f"{username}:{password}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    return {"Authorization": f"Basic {encoded}"}
                else:
                    missing = []
                    if not username:
                        missing.append(self.auth.token_env)
                    if not password:
                        missing.append(self.auth.key_env)
                    self._logger.warn(
                        LogCategory.STATE,
                        f"Basic auth env vars not set: {', '.join(missing)}",
                    )
            return None

        return None

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

    def _parse_response_body(self, text: str) -> str | dict[str, Any]:
        """Parse response body, attempting JSON decode.

        Args:
            text: Raw response text

        Returns:
            Parsed JSON dict or original text string
        """
        if not text:
            return ""

        try:
            result: dict[str, Any] = json.loads(text)
            return result
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
        duration = (datetime.now(UTC) - start_time).total_seconds()

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


def generate_summary(
    base_url: str,
    results: list[APIEvidenceResult],
) -> APIEvidenceSummary:
    """Generate a summary from API evidence results.

    Aggregates results from all captured endpoints and calculates
    success/failure counts and status mismatch counts. Logs the
    summary to console via LogManager.

    Args:
        base_url: Base URL for all endpoints
        results: List of individual endpoint results

    Returns:
        APIEvidenceSummary with aggregated statistics

    Example:
        >>> summary = generate_summary(
        ...     base_url="http://localhost:8000",
        ...     results=[result1, result2],
        ... )
        >>> summary.successful
        2
    """
    logger = get_logger()

    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    status_mismatches = sum(1 for r in results if not r.status_match)

    summary = APIEvidenceSummary(
        base_url=base_url,
        total_endpoints=total,
        successful=successful,
        failed=failed,
        status_mismatches=status_mismatches,
        results=results,
    )

    # Log summary to console
    logger.info(
        LogCategory.STATE,
        f"API Evidence Summary: {successful}/{total} endpoints successful, "
        f"{failed} failed, {status_mismatches} status mismatches",
    )

    if failed > 0:
        failed_endpoints = [r.endpoint_name for r in results if not r.success]
        logger.warn(
            LogCategory.STATE,
            f"Failed endpoints: {', '.join(failed_endpoints)}",
        )

    return summary
