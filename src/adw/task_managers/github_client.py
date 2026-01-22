"""GitHub API client for PR merge detection.

This module provides a lightweight GitHub API client focused on
checking PR merge status for the issue closing workflow.
"""

import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Timeout for GitHub API requests (in seconds)
GITHUB_API_TIMEOUT = 10.0


class GitHubClient:
    """Lightweight GitHub API client for PR status checks.

    This client is focused on checking PR merge status for the
    issue closing workflow. It handles missing tokens gracefully
    and caches results to avoid repeated API calls.

    Example:
        >>> client = GitHubClient()
        >>> client.is_pr_merged("https://github.com/owner/repo/pull/123")
        True
    """

    def __init__(self) -> None:
        """Initialize GitHubClient.

        Note: Does NOT raise if GITHUB_TOKEN is missing. Methods that
        require authentication will return conservative defaults.
        """
        self._token = os.environ.get("GITHUB_TOKEN")
        self._client: httpx.Client | None = None
        self._cache: dict[str, bool] = {}  # pr_url -> is_merged

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            self._client = httpx.Client(
                base_url=GITHUB_API_BASE,
                headers=headers,
                timeout=GITHUB_API_TIMEOUT,
            )
        return self._client

    def is_pr_merged(self, pr_url: str) -> bool:
        """Check if a pull request has been merged.

        This method:
        1. Parses the PR URL to extract owner/repo/number
        2. Checks the cache for a previous result
        3. Queries GitHub API if not cached
        4. Returns False if token is missing or any error occurs

        Args:
            pr_url: The full URL to the pull request.
                Example: "https://github.com/owner/repo/pull/123"

        Returns:
            True if the PR is merged, False otherwise or if detection
            fails (missing token, network error, invalid URL, etc.).
        """
        # Check cache first
        if pr_url in self._cache:
            logger.debug("PR merge status from cache: %s", pr_url)
            return self._cache[pr_url]

        # Parse PR URL
        parsed = self._parse_pr_url(pr_url)
        if parsed is None:
            logger.warning("Could not parse PR URL: %s", pr_url)
            self._cache[pr_url] = False
            return False

        owner, repo, number = parsed

        # Check if we have a token (required for private repos, helpful for rate limits)
        if not self._token:
            logger.debug("No GITHUB_TOKEN set, assuming PR not merged: %s", pr_url)
            self._cache[pr_url] = False
            return False

        # Query GitHub API
        try:
            result = self._check_pr_merged(owner, repo, number)
            self._cache[pr_url] = result
            return result
        except Exception as e:
            logger.warning("Error checking PR merge status for %s: %s", pr_url, e)
            self._cache[pr_url] = False
            return False

    def _parse_pr_url(self, pr_url: str) -> tuple[str, str, int] | None:
        """Parse a GitHub PR URL to extract owner, repo, and PR number.

        Supports URLs in the format:
        - https://github.com/owner/repo/pull/123
        - http://github.com/owner/repo/pull/123

        Args:
            pr_url: The PR URL to parse.

        Returns:
            Tuple of (owner, repo, number) if valid, None otherwise.
        """
        if not pr_url:
            return None

        pattern = r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, pr_url)

        if not match:
            return None

        owner, repo, number_str = match.groups()
        return owner, repo, int(number_str)

    def _check_pr_merged(self, owner: str, repo: str, number: int) -> bool:
        """Check if a specific PR is merged via GitHub API.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: PR number.

        Returns:
            True if merged, False otherwise.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        client = self._get_client()

        # Use the merge status endpoint which returns 204 if merged, 404 if not
        # https://docs.github.com/en/rest/pulls/pulls#check-if-a-pull-request-has-been-merged
        response = client.get(f"/repos/{owner}/{repo}/pulls/{number}/merge")

        if response.status_code == 204:
            logger.debug("PR is merged: %s/%s#%d", owner, repo, number)
            return True
        elif response.status_code == 404:
            logger.debug("PR is not merged: %s/%s#%d", owner, repo, number)
            return False
        else:
            # Unexpected status code - treat as not merged
            logger.warning(
                "Unexpected GitHub API response %d for %s/%s#%d",
                response.status_code,
                owner,
                repo,
                number,
            )
            return False

    def clear_cache(self) -> None:
        """Clear the PR merge status cache."""
        self._cache.clear()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "GitHubClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - close client."""
        self.close()


# Module-level singleton for convenience
_default_client: GitHubClient | None = None


def get_github_client() -> GitHubClient:
    """Get the module-level GitHubClient singleton.

    Returns:
        The shared GitHubClient instance.
    """
    global _default_client
    if _default_client is None:
        _default_client = GitHubClient()
    return _default_client


def is_pr_merged(pr_url: str) -> bool:
    """Convenience function to check if a PR is merged.

    Uses the module-level GitHubClient singleton.

    Args:
        pr_url: The full URL to the pull request.

    Returns:
        True if the PR is merged, False otherwise.
    """
    return get_github_client().is_pr_merged(pr_url)
