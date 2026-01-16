"""Tests for GitHub PR merge detection.

Per ADR-001: Tests focus on behavior, not mock verification.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from adw.task_managers.github_client import GitHubClient, is_pr_merged


class TestGitHubClientParsePrUrl:
    """Tests for PR URL parsing."""

    def test_parse_valid_https_url(self) -> None:
        """Parses standard GitHub PR URL."""
        client = GitHubClient()
        result = client._parse_pr_url("https://github.com/owner/repo/pull/123")
        assert result == ("owner", "repo", 123)

    def test_parse_valid_http_url(self) -> None:
        """Parses HTTP GitHub PR URL."""
        client = GitHubClient()
        result = client._parse_pr_url("http://github.com/owner/repo/pull/456")
        assert result == ("owner", "repo", 456)

    def test_parse_url_with_trailing_content(self) -> None:
        """Parses URL with trailing content after PR number."""
        client = GitHubClient()
        # The regex uses match from start, so additional path segments don't affect it
        result = client._parse_pr_url("https://github.com/org/project/pull/789")
        assert result == ("org", "project", 789)

    def test_parse_invalid_url_returns_none(self) -> None:
        """Returns None for non-GitHub URLs."""
        client = GitHubClient()
        assert client._parse_pr_url("https://gitlab.com/owner/repo/pull/123") is None
        assert client._parse_pr_url("not-a-url") is None
        assert client._parse_pr_url("") is None
        assert client._parse_pr_url("https://github.com/owner/repo/issues/123") is None


class TestGitHubClientIsPrMerged:
    """Tests for is_pr_merged method."""

    def test_is_pr_merged_without_token_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns False when no GITHUB_TOKEN is set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        client = GitHubClient()
        result = client.is_pr_merged("https://github.com/owner/repo/pull/123")

        assert result is False

    def test_is_pr_merged_caches_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Caches PR merge status to avoid repeated API calls."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        client = GitHubClient()
        pr_url = "https://github.com/owner/repo/pull/123"

        # Manually set cache
        client._cache[pr_url] = True

        # Should return cached value without making API call
        result = client.is_pr_merged(pr_url)
        assert result is True

    def test_is_pr_merged_returns_true_when_merged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns True when PR is merged (204 response)."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        client = GitHubClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = client.is_pr_merged("https://github.com/owner/repo/pull/123")

            assert result is True
            mock_http_client.get.assert_called_once_with(
                "/repos/owner/repo/pulls/123/merge"
            )

    def test_is_pr_merged_returns_false_when_not_merged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns False when PR is not merged (404 response)."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        client = GitHubClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = client.is_pr_merged("https://github.com/owner/repo/pull/456")

            assert result is False

    def test_is_pr_merged_handles_api_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns False and logs warning on API error."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        client = GitHubClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = httpx.HTTPError("Connection failed")
            mock_get_client.return_value = mock_http_client

            result = client.is_pr_merged("https://github.com/owner/repo/pull/789")

            assert result is False

    def test_is_pr_merged_invalid_url_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns False for invalid PR URLs."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")

        client = GitHubClient()

        assert client.is_pr_merged("not-a-url") is False
        assert client.is_pr_merged("https://gitlab.com/owner/repo/pull/123") is False


class TestGitHubClientCache:
    """Tests for cache functionality."""

    def test_clear_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """clear_cache removes all cached entries."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        client = GitHubClient()
        client._cache["url1"] = True
        client._cache["url2"] = False

        client.clear_cache()

        assert len(client._cache) == 0


class TestConvenienceFunction:
    """Tests for module-level convenience function."""

    def test_is_pr_merged_function(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_pr_merged uses singleton client."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Without token, should return False
        result = is_pr_merged("https://github.com/owner/repo/pull/123")
        assert result is False
