"""Linear GraphQL API client.

This module provides a low-level client for interacting with
Linear's GraphQL API.
"""

import logging
from typing import Any

import httpx

from adw.exceptions import TaskError

logger = logging.getLogger(__name__)

# ADW label color - purple to distinguish automation labels
ADW_LABEL_COLOR = "#9333EA"


# GraphQL Queries and Mutations
# Note: Linear's issue(id:) query requires internal UUID, not the human-readable
# identifier like "RULE-151". We use a filter query instead to fetch by identifier.
FETCH_ISSUE_QUERY = """
query FetchIssue($teamKey: String!, $number: Float!) {
  issues(filter: {
    team: { key: { eq: $teamKey } },
    number: { eq: $number }
  }, first: 1) {
    nodes {
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

GET_TEAM_LABELS_QUERY = """
query TeamLabels($teamId: String!) {
  team(id: $teamId) {
    labels { nodes { id name color } }
  }
}
"""

CREATE_LABEL_MUTATION = """
mutation CreateLabel($teamId: String!, $name: String!, $color: String!) {
  issueLabelCreate(input: {teamId: $teamId, name: $name, color: $color}) {
    success
    issueLabel { id name }
  }
}
"""

ADD_LABEL_MUTATION = """
mutation AddLabelToIssue($issueId: String!, $labelId: String!) {
  issueAddLabel(id: $issueId, labelId: $labelId) {
    success
  }
}
"""

REMOVE_LABEL_MUTATION = """
mutation RemoveLabelFromIssue($issueId: String!, $labelId: String!) {
  issueRemoveLabel(id: $issueId, labelId: $labelId) {
    success
  }
}
"""

CREATE_COMMENT_MUTATION = """
mutation CreateComment($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment { id }
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
        # Label cache: team_id -> {label_name -> label_id}
        self._label_cache: dict[str, dict[str, str]] = {}

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Linear API keys are passed directly without Bearer prefix.

        Returns:
            Headers dict with Authorization and Content-Type.
        """
        return {
            "Authorization": self._api_key,
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
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        return self._client.post(
            self._base_url,
            json=payload,
            headers=self._get_headers(),
        )

    def fetch_issue(self, identifier: str) -> dict[str, Any] | None:
        """Fetch an issue by identifier (e.g., RULE-123).

        Parses the identifier into team key and issue number, then queries
        Linear's API using a filter. This is more reliable than using the
        issue(id:) query which requires the internal UUID.

        Args:
            identifier: The issue identifier (e.g., "RULE-123").

        Returns:
            Issue data dict if found, None otherwise.

        Raises:
            TaskError: If the API request fails or identifier format is invalid.
        """
        # Parse identifier (e.g., "RULE-151" -> team_key="RULE", number=151)
        parts = identifier.rsplit("-", 1)
        if len(parts) != 2:
            raise TaskError(
                code="INVALID_TASK_ID",
                message=f"Invalid task identifier format: '{identifier}'",
                suggestion="Use format like 'TEAM-123' (e.g., 'RULE-151')",
                task_id=identifier,
                recoverable=False,
            )

        team_key, number_str = parts
        try:
            number = int(number_str)
        except ValueError as e:
            raise TaskError(
                code="INVALID_TASK_ID",
                message=f"Invalid issue number in identifier: '{identifier}'",
                suggestion="Issue number must be numeric (e.g., 'RULE-151')",
                task_id=identifier,
                recoverable=False,
            ) from e

        try:
            response = self._request(
                FETCH_ISSUE_QUERY,
                variables={"teamKey": team_key, "number": float(number)},
            )
            self._handle_response_errors(response, identifier)

            data: dict[str, Any] = response.json()
            nodes: list[dict[str, Any]] = (
                data.get("data", {}).get("issues", {}).get("nodes", [])
            )
            if nodes:
                return nodes[0]
            return None
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

        Raises:
            TaskError: If the API request fails.
        """
        response = self._request(
            UPDATE_ISSUE_MUTATION,
            variables={"id": issue_id, "input": input_data},
        )
        self._handle_response_errors(response, issue_id)

        data: dict[str, Any] = response.json()
        result: dict[str, Any] | None = data.get("data", {}).get("issueUpdate")
        if result and result.get("success"):
            return result
        return None

    def get_team_states(self, team_id: str) -> list[dict[str, Any]]:
        """Get workflow states for a team.

        Args:
            team_id: The team UUID.

        Returns:
            List of state dicts with id, name, and type.

        Raises:
            TaskError: If the API request fails.
        """
        response = self._request(
            GET_TEAM_STATES_QUERY,
            variables={"teamId": team_id},
        )
        self._handle_response_errors(response, team_id)

        data: dict[str, Any] = response.json()
        team: dict[str, Any] | None = data.get("data", {}).get("team")
        if team:
            states: list[dict[str, Any]] = team.get("states", {}).get("nodes", [])
            return states
        return []

    def get_team_labels(self, team_id: str) -> list[dict[str, Any]]:
        """Get all labels for a team.

        Args:
            team_id: The team UUID.

        Returns:
            List of label dicts with id, name, and color.
        """
        response = self._request(
            GET_TEAM_LABELS_QUERY,
            variables={"teamId": team_id},
        )
        self._handle_response_errors(response, team_id)

        data: dict[str, Any] = response.json()
        team: dict[str, Any] | None = data.get("data", {}).get("team")
        if team:
            labels: list[dict[str, Any]] = team.get("labels", {}).get("nodes", [])
            return labels
        return []

    def create_label(
        self, team_id: str, name: str, color: str = ADW_LABEL_COLOR
    ) -> str | None:
        """Create a new label for a team.

        Args:
            team_id: The team UUID.
            name: The label name.
            color: The label color (hex). Defaults to ADW purple.

        Returns:
            The new label ID if successful, None otherwise.
        """
        response = self._request(
            CREATE_LABEL_MUTATION,
            variables={"teamId": team_id, "name": name, "color": color},
        )
        self._handle_response_errors(response, team_id)

        data: dict[str, Any] = response.json()
        result: dict[str, Any] | None = data.get("data", {}).get("issueLabelCreate")
        if result and result.get("success"):
            label: dict[str, Any] | None = result.get("issueLabel")
            if label:
                label_id: str | None = label.get("id")
                return label_id
        return None

    def add_label_to_issue(self, issue_id: str, label_id: str) -> bool:
        """Add a label to an issue by IDs.

        Args:
            issue_id: The internal issue UUID.
            label_id: The label UUID.

        Returns:
            True if successful, False otherwise.
        """
        response = self._request(
            ADD_LABEL_MUTATION,
            variables={"issueId": issue_id, "labelId": label_id},
        )
        self._handle_response_errors(response, issue_id)

        data = response.json()
        result = data.get("data", {}).get("issueAddLabel")
        return result.get("success", False) if result else False

    def remove_label_from_issue(self, issue_id: str, label_id: str) -> bool:
        """Remove a label from an issue by IDs.

        Args:
            issue_id: The internal issue UUID.
            label_id: The label UUID.

        Returns:
            True if successful, False otherwise.
        """
        response = self._request(
            REMOVE_LABEL_MUTATION,
            variables={"issueId": issue_id, "labelId": label_id},
        )
        self._handle_response_errors(response, issue_id)

        data = response.json()
        result = data.get("data", {}).get("issueRemoveLabel")
        return result.get("success", False) if result else False

    def _get_or_create_label_id(self, team_id: str, label_name: str) -> str | None:
        """Get label ID from cache or fetch/create.

        Args:
            team_id: The team UUID.
            label_name: The label name.

        Returns:
            The label ID if found/created, None on failure.
        """
        # Check cache first
        if team_id in self._label_cache:
            if label_name in self._label_cache[team_id]:
                return self._label_cache[team_id][label_name]
        else:
            self._label_cache[team_id] = {}

        # Fetch team labels and populate cache
        labels = self.get_team_labels(team_id)
        for label in labels:
            name = label.get("name")
            label_id = label.get("id")
            if name and label_id:
                self._label_cache[team_id][name] = label_id

        # Check if label now in cache
        if label_name in self._label_cache[team_id]:
            return self._label_cache[team_id][label_name]

        # Label doesn't exist - create it
        new_label_id = self.create_label(team_id, label_name)
        if new_label_id:
            self._label_cache[team_id][label_name] = new_label_id
        return new_label_id

    def _get_label_id(self, team_id: str, label_name: str) -> str | None:
        """Get label ID from cache or fetch (no create).

        Args:
            team_id: The team UUID.
            label_name: The label name.

        Returns:
            The label ID if found, None if not found.
        """
        # Check cache first
        if team_id in self._label_cache:
            if label_name in self._label_cache[team_id]:
                return self._label_cache[team_id][label_name]
        else:
            self._label_cache[team_id] = {}

        # Fetch team labels and populate cache
        labels = self.get_team_labels(team_id)
        for label in labels:
            name = label.get("name")
            label_id = label.get("id")
            if name and label_id:
                self._label_cache[team_id][name] = label_id

        # Return label ID if found
        return self._label_cache[team_id].get(label_name)

    def add_label(self, issue_id: str, label_name: str, team_id: str) -> None:
        """Add a label to an issue.

        Gets or creates the label, then adds it to the issue.

        Args:
            issue_id: The internal issue UUID.
            label_name: The label name to add.
            team_id: The team UUID for label creation.
        """
        label_id = self._get_or_create_label_id(team_id, label_name)
        if label_id:
            self.add_label_to_issue(issue_id, label_id)

    def remove_label(self, issue_id: str, label_name: str, team_id: str) -> None:
        """Remove a label from an issue.

        Looks up the label ID and removes it from the issue.

        Args:
            issue_id: The internal issue UUID.
            label_name: The label name to remove.
            team_id: The team UUID for label lookup.
        """
        label_id = self._get_label_id(team_id, label_name)
        if label_id:
            self.remove_label_from_issue(issue_id, label_id)

    def post_comment(self, issue_id: str, body: str) -> bool:
        """Post a comment to an issue.

        Args:
            issue_id: The internal issue UUID.
            body: The comment body (supports markdown).

        Returns:
            True if successful, False otherwise.
        """
        response = self._request(
            CREATE_COMMENT_MUTATION,
            variables={"issueId": issue_id, "body": body},
        )
        self._handle_response_errors(response, issue_id)

        data = response.json()
        result = data.get("data", {}).get("commentCreate")
        return result.get("success", False) if result else False

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "LinearClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close client."""
        self.close()
