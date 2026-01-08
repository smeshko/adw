"""Unit tests for LinearClient.

Tests for the Linear GraphQL API client.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from adw.exceptions import TaskError
from adw.task_managers.linear_client import LinearClient


class TestLinearClient:
    """Tests for LinearClient."""

    def test_init_sets_api_key_and_base_url(self) -> None:
        """LinearClient initializes with API key and base URL."""
        client = LinearClient(api_key="lin_api_test123")

        assert client._api_key == "lin_api_test123"
        assert client._base_url == "https://api.linear.app/graphql"

    def test_headers_include_authorization(self) -> None:
        """Headers include Authorization Bearer token."""
        client = LinearClient(api_key="lin_api_test123")

        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer lin_api_test123"
        assert headers["Content-Type"] == "application/json"


class TestLinearClientFetchIssue:
    """Tests for LinearClient.fetch_issue."""

    def test_fetch_issue_returns_issue_data(self) -> None:
        """fetch_issue returns issue data from API response."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "issue": {
                    "id": "abc123",
                    "identifier": "RULE-123",
                    "title": "Test Issue",
                    "description": "Test description",
                }
            }
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.fetch_issue("RULE-123")

        assert result["id"] == "abc123"
        assert result["identifier"] == "RULE-123"
        assert result["title"] == "Test Issue"

    def test_fetch_issue_returns_none_when_not_found(self) -> None:
        """fetch_issue returns None when issue doesn't exist."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"issue": None}}

        with patch.object(client, "_request", return_value=mock_response):
            result = client.fetch_issue("NONEXISTENT-999")

        assert result is None


class TestLinearClientUpdateIssue:
    """Tests for LinearClient.update_issue."""

    def test_update_issue_sends_mutation(self) -> None:
        """update_issue sends issueUpdate mutation."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {"id": "abc123", "state": {"name": "Done"}},
                }
            }
        }

        with patch.object(client, "_request", return_value=mock_response) as mock_req:
            result = client.update_issue("abc123", {"stateId": "state-id-456"})

        assert result["success"] is True
        # Verify _request was called with mutation
        mock_req.assert_called_once()

    def test_update_issue_returns_none_on_failure(self) -> None:
        """update_issue returns None when update fails."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"issueUpdate": {"success": False, "issue": None}}
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.update_issue("abc123", {"stateId": "invalid-state"})

        assert result is None or result.get("success") is False


class TestLinearClientErrorHandling:
    """Tests for LinearClient error handling."""

    def test_fetch_issue_raises_task_error_on_network_error(self) -> None:
        """fetch_issue raises TaskError on network errors."""
        client = LinearClient(api_key="lin_api_test123")

        with patch.object(
            client._client,
            "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(TaskError) as exc_info:
                client.fetch_issue("RULE-123")

            assert exc_info.value.code == "TASK_API_ERROR"
            assert "Connection" in exc_info.value.message

    def test_fetch_issue_raises_task_error_on_timeout(self) -> None:
        """fetch_issue raises TaskError on timeout."""
        client = LinearClient(api_key="lin_api_test123")

        with patch.object(
            client._client,
            "post",
            side_effect=httpx.TimeoutException("Request timed out"),
        ):
            with pytest.raises(TaskError) as exc_info:
                client.fetch_issue("RULE-123")

            assert exc_info.value.code == "TASK_API_TIMEOUT"

    def test_fetch_issue_raises_task_error_on_http_error(self) -> None:
        """fetch_issue raises TaskError on HTTP errors."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "post", return_value=mock_response):
            with pytest.raises(TaskError) as exc_info:
                client.fetch_issue("RULE-123")

            assert exc_info.value.code == "TASK_API_ERROR"

    def test_fetch_issue_raises_task_error_on_rate_limit(self) -> None:
        """fetch_issue raises TaskError with recoverable=True on rate limit."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limited",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "post", return_value=mock_response):
            with pytest.raises(TaskError) as exc_info:
                client.fetch_issue("RULE-123")

            assert exc_info.value.code == "TASK_RATE_LIMITED"
            assert exc_info.value.recoverable is True
