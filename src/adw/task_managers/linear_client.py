"""Linear GraphQL API client.

This module provides a low-level client for interacting with
Linear's GraphQL API.
"""

import logging
from typing import Any

import httpx

from adw.exceptions import TaskError

logger = logging.getLogger(__name__)


# GraphQL Queries and Mutations
FETCH_ISSUE_QUERY = """
query FetchIssue($identifier: String!) {
  issue(id: $identifier) {
    id
    identifier
    title
    description
    state { id name }
    priority
    labels { nodes { name } }
    assignee { name email }
    project { name }
    parent { identifier title }
  }
}
"""

UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue { id state { name } }
  }
}
"""

GET_TEAM_STATES_QUERY = """
query TeamWorkflowStates($teamId: String!) {
  team(id: $teamId) {
    states { nodes { id name type } }
  }
}
"""


class LinearClient:
    """Low-level client for Linear's GraphQL API.

    This client handles the HTTP communication with Linear's API,
    including authentication, request formatting, and response parsing.

    Example:
        >>> client = LinearClient(api_key="lin_api_xxx")
        >>> issue = client.fetch_issue("RULE-123")
        >>> issue["title"]
        'Add user authentication'
    """

    def __init__(self, api_key: str) -> None:
        """Initialize LinearClient with API key.

        Args:
            api_key: Linear API key for authentication.
        """
        self._api_key = api_key
        self._base_url = "https://api.linear.app/graphql"
        self._client = httpx.Client(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Headers dict with Authorization and Content-Type.
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send a GraphQL request to Linear API.

        Args:
            query: GraphQL query or mutation string.
            variables: Optional variables for the query.

        Returns:
            The HTTP response from the API.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        return self._client.post(
            self._base_url,
            json=payload,
            headers=self._get_headers(),
        )

    def fetch_issue(self, identifier: str) -> dict[str, Any] | None:
        """Fetch an issue by identifier (e.g., RULE-123).

        Args:
            identifier: The issue identifier.

        Returns:
            Issue data dict if found, None otherwise.

        Raises:
            TaskError: If the API request fails.
        """
        try:
            response = self._request(
                FETCH_ISSUE_QUERY,
                variables={"identifier": identifier},
            )
            self._handle_response_errors(response, identifier)

            data = response.json()
            issue = data.get("data", {}).get("issue")
            return issue
        except TaskError:
            raise
        except httpx.TimeoutException as e:
            raise TaskError(
                code="TASK_API_TIMEOUT",
                message=f"Linear API request timed out for '{identifier}'",
                suggestion="Try again or check your network connection",
                task_id=identifier,
                recoverable=True,
            ) from e
        except httpx.ConnectError as e:
            raise TaskError(
                code="TASK_API_ERROR",
                message=f"Connection error to Linear API: {e}",
                suggestion="Check your network connection",
                task_id=identifier,
                recoverable=True,
            ) from e
        except httpx.HTTPError as e:
            raise TaskError(
                code="TASK_API_ERROR",
                message=f"HTTP error from Linear API: {e}",
                suggestion="Try again later",
                task_id=identifier,
                recoverable=True,
            ) from e

    def _handle_response_errors(self, response: httpx.Response, task_id: str) -> None:
        """Check response for errors and raise appropriate TaskError.

        Args:
            response: The HTTP response to check.
            task_id: The task ID for error context.

        Raises:
            TaskError: If the response indicates an error.
        """
        if response.status_code == 429:
            raise TaskError(
                code="TASK_RATE_LIMITED",
                message="Linear API rate limit exceeded",
                suggestion="Wait a moment and try again",
                task_id=task_id,
                recoverable=True,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise TaskError(
                code="TASK_API_ERROR",
                message=f"Linear API returned error {response.status_code}",
                suggestion="Check Linear API status or try again later",
                task_id=task_id,
                recoverable=response.status_code >= 500,
            ) from e

    def update_issue(
        self,
        issue_id: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an issue.

        Args:
            issue_id: The internal issue UUID (not identifier).
            input_data: Update input (e.g., {"stateId": "xxx"}).

        Returns:
            Update result if successful, None otherwise.
        """
        response = self._request(
            UPDATE_ISSUE_MUTATION,
            variables={"id": issue_id, "input": input_data},
        )
        response.raise_for_status()

        data = response.json()
        result = data.get("data", {}).get("issueUpdate")
        if result and result.get("success"):
            return result
        return None

    def get_team_states(self, team_id: str) -> list[dict[str, Any]]:
        """Get workflow states for a team.

        Args:
            team_id: The team UUID.

        Returns:
            List of state dicts with id, name, and type.
        """
        response = self._request(
            GET_TEAM_STATES_QUERY,
            variables={"teamId": team_id},
        )
        response.raise_for_status()

        data = response.json()
        team = data.get("data", {}).get("team")
        if team:
            return team.get("states", {}).get("nodes", [])
        return []

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "LinearClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close client."""
        self.close()
