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


class TestLinearClientLabelOperations:
    """Tests for LinearClient label operations (Story 12.7 Task 2)."""

    def test_get_team_labels_returns_labels(self) -> None:
        """get_team_labels returns list of label data from team."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "team": {
                    "labels": {
                        "nodes": [
                            {"id": "label-1", "name": "adw:running", "color": "#9333EA"},
                            {"id": "label-2", "name": "adw:completed", "color": "#9333EA"},
                        ]
                    }
                }
            }
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.get_team_labels("team-uuid")

        assert len(result) == 2
        assert result[0]["name"] == "adw:running"
        assert result[1]["name"] == "adw:completed"

    def test_get_team_labels_returns_empty_list_when_no_labels(self) -> None:
        """get_team_labels returns empty list when team has no labels."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"team": {"labels": {"nodes": []}}}
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.get_team_labels("team-uuid")

        assert result == []

    def test_create_label_sends_mutation(self) -> None:
        """create_label sends labelCreate mutation and returns label ID."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "labelCreate": {
                    "success": True,
                    "label": {"id": "new-label-id", "name": "adw:running"},
                }
            }
        }

        with patch.object(client, "_request", return_value=mock_response) as mock_req:
            result = client.create_label("team-uuid", "adw:running", "#9333EA")

        assert result == "new-label-id"
        mock_req.assert_called_once()

    def test_create_label_returns_none_on_failure(self) -> None:
        """create_label returns None when creation fails."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"labelCreate": {"success": False, "label": None}}
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.create_label("team-uuid", "adw:running", "#9333EA")

        assert result is None

    def test_add_label_to_issue_sends_mutation(self) -> None:
        """add_label_to_issue sends issueAddLabel mutation."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"issueAddLabel": {"success": True}}
        }

        with patch.object(client, "_request", return_value=mock_response) as mock_req:
            result = client.add_label_to_issue("issue-uuid", "label-uuid")

        assert result is True
        mock_req.assert_called_once()

    def test_add_label_to_issue_returns_false_on_failure(self) -> None:
        """add_label_to_issue returns False when operation fails."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"issueAddLabel": {"success": False}}
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.add_label_to_issue("issue-uuid", "label-uuid")

        assert result is False

    def test_remove_label_from_issue_sends_mutation(self) -> None:
        """remove_label_from_issue sends issueRemoveLabel mutation."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"issueRemoveLabel": {"success": True}}
        }

        with patch.object(client, "_request", return_value=mock_response) as mock_req:
            result = client.remove_label_from_issue("issue-uuid", "label-uuid")

        assert result is True
        mock_req.assert_called_once()

    def test_remove_label_from_issue_returns_false_on_failure(self) -> None:
        """remove_label_from_issue returns False when operation fails."""
        client = LinearClient(api_key="lin_api_test123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"issueRemoveLabel": {"success": False}}
        }

        with patch.object(client, "_request", return_value=mock_response):
            result = client.remove_label_from_issue("issue-uuid", "label-uuid")

        assert result is False


class TestLinearClientAddLabelIntegration:
    """Tests for LinearClient.add_label high-level integration (Story 12.7 Task 2)."""

    def test_add_label_gets_or_creates_label_and_adds_to_issue(self) -> None:
        """add_label looks up label, creates if needed, and adds to issue."""
        client = LinearClient(api_key="lin_api_test123")

        # Mock get_team_labels to return empty (label doesn't exist)
        # Mock create_label to return new label ID
        # Mock add_label_to_issue to succeed
        with patch.object(
            client, "get_team_labels", return_value=[]
        ) as mock_get_labels:
            with patch.object(
                client, "create_label", return_value="new-label-id"
            ) as mock_create:
                with patch.object(
                    client, "add_label_to_issue", return_value=True
                ) as mock_add:
                    client.add_label("issue-uuid", "adw:running", "team-uuid")

        mock_get_labels.assert_called_once_with("team-uuid")
        mock_create.assert_called_once()
        mock_add.assert_called_once_with("issue-uuid", "new-label-id")

    def test_add_label_uses_existing_label_id(self) -> None:
        """add_label uses existing label ID if label exists."""
        client = LinearClient(api_key="lin_api_test123")

        # Mock get_team_labels to return existing label
        existing_labels = [{"id": "existing-label-id", "name": "adw:running", "color": "#9333EA"}]

        with patch.object(
            client, "get_team_labels", return_value=existing_labels
        ):
            with patch.object(
                client, "create_label"
            ) as mock_create:
                with patch.object(
                    client, "add_label_to_issue", return_value=True
                ) as mock_add:
                    client.add_label("issue-uuid", "adw:running", "team-uuid")

        # create_label should NOT be called since label exists
        mock_create.assert_not_called()
        mock_add.assert_called_once_with("issue-uuid", "existing-label-id")

    def test_add_label_caches_label_ids(self) -> None:
        """add_label caches label IDs to reduce API calls."""
        client = LinearClient(api_key="lin_api_test123")

        existing_labels = [{"id": "cached-label-id", "name": "adw:running", "color": "#9333EA"}]

        with patch.object(
            client, "get_team_labels", return_value=existing_labels
        ) as mock_get_labels:
            with patch.object(
                client, "add_label_to_issue", return_value=True
            ):
                # First call should populate cache
                client.add_label("issue-1", "adw:running", "team-uuid")
                # Second call should use cache
                client.add_label("issue-2", "adw:running", "team-uuid")

        # get_team_labels should only be called once (cached)
        assert mock_get_labels.call_count == 1


class TestLinearClientRemoveLabelIntegration:
    """Tests for LinearClient.remove_label high-level integration."""

    def test_remove_label_looks_up_and_removes(self) -> None:
        """remove_label looks up label ID and removes from issue."""
        client = LinearClient(api_key="lin_api_test123")

        existing_labels = [{"id": "label-to-remove", "name": "adw:running", "color": "#9333EA"}]

        with patch.object(
            client, "get_team_labels", return_value=existing_labels
        ):
            with patch.object(
                client, "remove_label_from_issue", return_value=True
            ) as mock_remove:
                client.remove_label("issue-uuid", "adw:running", "team-uuid")

        mock_remove.assert_called_once_with("issue-uuid", "label-to-remove")

    def test_remove_label_does_nothing_if_label_not_found(self) -> None:
        """remove_label does nothing if label doesn't exist."""
        client = LinearClient(api_key="lin_api_test123")

        # No labels exist
        with patch.object(
            client, "get_team_labels", return_value=[]
        ):
            with patch.object(
                client, "remove_label_from_issue"
            ) as mock_remove:
                # Should not raise
                client.remove_label("issue-uuid", "nonexistent:label", "team-uuid")

        # remove_label_from_issue should not be called
        mock_remove.assert_not_called()
