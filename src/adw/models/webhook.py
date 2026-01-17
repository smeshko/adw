"""Webhook server configuration and event models.

This module contains Pydantic models for webhook server configuration,
event parsing, run parameter extraction, and event-to-workflow mapping.
"""

from __future__ import annotations

import contextlib
import os
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ProviderConfig(BaseModel):
    """Configuration for a single webhook provider.

    Defines settings for an individual webhook provider such as Linear,
    GitHub, or GitLab. Each provider can be enabled/disabled and configured
    with a secret for signature verification.

    Attributes:
        enabled: Whether this provider is enabled (default: False)
        secret_env: Name of environment variable containing the webhook secret
        command_prefix: Command prefix for triggering ADW (default: "/adw")
        trigger_label: Label name that triggers ADW on issues (default: "adw")

    Example:
        >>> config = ProviderConfig(enabled=True, secret_env="GITHUB_WEBHOOK_SECRET")
        >>> config.enabled
        True
        >>> config.get_secret()  # Returns value of GITHUB_WEBHOOK_SECRET env var
        'secret-value'

    YAML example:
        webhook:
          providers:
            github:
              enabled: true
              secret_env: GITHUB_WEBHOOK_SECRET
              command_prefix: "/adw"
              trigger_label: "adw"
    """

    enabled: bool = Field(
        default=False,
        description="Whether this provider is enabled",
    )
    secret_env: str | None = Field(
        default=None,
        description="Name of environment variable containing the webhook secret",
    )
    command_prefix: str = Field(
        default="/adw",
        description="Command prefix for triggering ADW runs",
    )
    trigger_label: str = Field(
        default="adw",
        description="Label name that triggers ADW on issues",
    )

    def get_secret(self) -> str | None:
        """Get the secret from the configured environment variable.

        Returns:
            The secret value if secret_env is set and the environment
            variable exists, otherwise None.
        """
        if self.secret_env:
            return os.getenv(self.secret_env)
        return None


class WebhookConfig(BaseModel):
    """Configuration for the webhook server.

    Defines server settings including host, port, provider configurations,
    and event-to-workflow mappings.
    This configuration can be specified in the project's adw.yaml file under
    the 'webhook' key.

    Attributes:
        port: Port to run the webhook server on (default: 8000)
        host: Host to bind the server to (default: "0.0.0.0")
        providers: Dictionary mapping provider names to their configurations
        mappings: Event-to-workflow mapping configuration (optional)

    Example:
        >>> config = WebhookConfig(
        ...     port=9000,
        ...     providers={"linear": ProviderConfig(enabled=True)}
        ... )
        >>> config.port
        9000
        >>> config.is_provider_enabled("linear")
        True

    YAML example:
        webhook:
          port: 8000
          host: "0.0.0.0"
          providers:
            linear:
              enabled: true
              secret_env: LINEAR_WEBHOOK_SECRET
            github:
              enabled: false
              secret_env: GITHUB_WEBHOOK_SECRET
          mappings:
            linear:
              issue_created:
                trigger: true
                require_label: "adw:auto"
    """

    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port to run the webhook server on",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to",
    )
    providers: dict[str, ProviderConfig] = Field(
        default_factory=dict,
        description="Provider configurations keyed by provider name",
    )
    mappings: WebhookMappings | None = Field(
        default=None,
        description="Event-to-workflow mapping configuration",
    )

    def get_provider(self, name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider.

        Args:
            name: The provider name (e.g., "linear", "github")

        Returns:
            The provider configuration if found, otherwise None.
        """
        return self.providers.get(name)

    def is_provider_enabled(self, name: str) -> bool:
        """Check if a provider is enabled.

        Args:
            name: The provider name to check

        Returns:
            True if the provider exists and is enabled, False otherwise.
        """
        provider = self.get_provider(name)
        return provider.enabled if provider else False


class WebhookEvent(BaseModel):
    """Structured representation of a parsed webhook event.

    Captures all relevant information from a webhook request in a
    provider-agnostic format for downstream processing.

    Attributes:
        event_type: The type of event (e.g., 'IssueCreate', 'push')
        provider: Name of the webhook provider (e.g., 'linear', 'github')
        payload: The parsed event payload as a dictionary
        headers: Relevant headers from the request
        timestamp: When the event was received (UTC)
        raw_body: Optional raw request body for debugging

    Example:
        >>> event = WebhookEvent(
        ...     event_type="IssueCreate",
        ...     provider="linear",
        ...     payload={"id": "issue-123", "title": "Add feature"},
        ...     headers={"x-linear-event": "IssueCreate"},
        ... )
    """

    event_type: str = Field(
        description="Type of the webhook event",
    )
    provider: str = Field(
        description="Name of the webhook provider",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Parsed event payload",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Relevant request headers",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the event was received (UTC)",
    )
    raw_body: bytes | None = Field(
        default=None,
        description="Optional raw request body for debugging",
    )


class RunParams(BaseModel):
    """Parameters extracted from a webhook event for starting an ADW run.

    Contains all the information needed to initiate an ADW workflow run
    from a webhook trigger.

    Attributes:
        feature_request: The feature description/request to implement
        phases: Optional list of phases to execute (default: all)
        source_info: Information about the webhook source (issue URL, etc.)
        metadata: Additional provider-specific metadata

    Example:
        >>> params = RunParams(
        ...     feature_request="Add dark mode toggle",
        ...     source_info={"issue_url": "https://linear.app/..."},
        ...     metadata={"linear_issue_id": "ABC-123"},
        ... )
    """

    feature_request: str = Field(
        description="The feature description to implement",
    )
    phases: list[str] | None = Field(
        default=None,
        description="Phases to execute (None = all)",
    )
    source_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Information about the webhook source",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific metadata",
    )


# =============================================================================
# Event-to-Workflow Mapping Models (Story 13.4)
# =============================================================================


class EventTriggerConfig(BaseModel):
    """Configuration for a single event type trigger.

    Defines the conditions under which a specific event type should
    trigger an ADW workflow run.

    Attributes:
        trigger: Whether this event type triggers runs (default: True)
        require_label: Label name that must be present to trigger
        require_mention: Mention string that must be present (e.g., "@adw")
        parse_command: Whether to parse command arguments from comment
        phases: Optional list of phases to run (None = all phases)

    Example:
        >>> config = EventTriggerConfig(
        ...     trigger=True,
        ...     require_label="adw:auto",
        ...     phases=["plan", "build"],
        ... )
        >>> config.trigger
        True

    YAML example:
        webhook:
          mappings:
            linear:
              issue_created:
                trigger: true
                require_label: "adw:auto"
                phases: ["plan", "build"]
    """

    trigger: bool = Field(
        default=True,
        description="Whether this event type triggers runs",
    )
    require_label: str | None = Field(
        default=None,
        description="Label name that must be present to trigger",
    )
    require_mention: str | None = Field(
        default=None,
        description="Mention string that must be present (e.g., '@adw')",
    )
    parse_command: bool = Field(
        default=False,
        description="Whether to parse command arguments from comment",
    )
    phases: list[str] | None = Field(
        default=None,
        description="Phases to run (None = all phases)",
    )

    @model_validator(mode="after")
    def validate_conditions(self) -> EventTriggerConfig:
        """Validate that conditions are coherent.

        Ensures that parse_command is only used with require_mention,
        since command parsing only makes sense for comment-based triggers.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If parse_command is True but require_mention is None.
        """
        if self.parse_command and self.require_mention is None:
            raise ValueError(
                "parse_command=True requires require_mention to be set "
                "(command parsing only makes sense for comment triggers)"
            )
        return self


class ProviderEventMapping(BaseModel):
    """Event mappings for a specific provider.

    Maps event types to their trigger configurations. Event types use
    a normalized naming convention across providers.

    Attributes:
        issue_created: Config for issue creation events
        issue_updated: Config for issue update events
        comment_created: Config for comment creation events

    Example:
        >>> mapping = ProviderEventMapping(
        ...     issue_created=EventTriggerConfig(
        ...         trigger=True,
        ...         require_label="adw:auto",
        ...     ),
        ...     issue_updated=EventTriggerConfig(trigger=False),
        ... )
        >>> mapping.get_event_config("issue_created")
        EventTriggerConfig(trigger=True, require_label='adw:auto', ...)

    YAML example:
        webhook:
          mappings:
            linear:
              issue_created:
                trigger: true
                require_label: "adw:auto"
              comment_created:
                trigger: true
                require_mention: "@adw"
                parse_command: true
    """

    issue_created: EventTriggerConfig | None = Field(
        default=None,
        description="Configuration for issue creation events",
    )
    issue_updated: EventTriggerConfig | None = Field(
        default=None,
        description="Configuration for issue update events",
    )
    comment_created: EventTriggerConfig | None = Field(
        default=None,
        description="Configuration for comment creation events",
    )

    def get_event_config(self, event_type: str) -> EventTriggerConfig | None:
        """Get the trigger configuration for a specific event type.

        Uses normalized event type names (issue_created, issue_updated,
        comment_created) rather than provider-specific names.

        Args:
            event_type: The normalized event type name.

        Returns:
            EventTriggerConfig if defined, None otherwise.

        Example:
            >>> mapping.get_event_config("issue_created")
            EventTriggerConfig(trigger=True, ...)
        """
        return getattr(self, event_type, None)


class WebhookMappings(BaseModel):
    """All webhook event mappings across providers.

    Top-level container for provider-specific event mappings. Each
    provider can define its own mapping rules.

    Attributes:
        linear: Event mappings for Linear webhooks
        github: Event mappings for GitHub webhooks

    Example:
        >>> mappings = WebhookMappings(
        ...     linear=ProviderEventMapping(
        ...         issue_created=EventTriggerConfig(trigger=True),
        ...     ),
        ... )
        >>> mappings.get_provider_mapping("linear")
        ProviderEventMapping(...)

    YAML example:
        webhook:
          mappings:
            linear:
              issue_created:
                trigger: true
                require_label: "adw:auto"
            github:
              issue_created:
                trigger: true
                require_label: "adw"
    """

    linear: ProviderEventMapping | None = Field(
        default=None,
        description="Event mappings for Linear webhooks",
    )
    github: ProviderEventMapping | None = Field(
        default=None,
        description="Event mappings for GitHub webhooks",
    )

    def get_provider_mapping(self, provider: str) -> ProviderEventMapping | None:
        """Get the event mapping for a specific provider.

        Args:
            provider: The provider name (e.g., "linear", "github").

        Returns:
            ProviderEventMapping if defined, None otherwise.

        Example:
            >>> mappings.get_provider_mapping("linear")
            ProviderEventMapping(...)
        """
        return getattr(self, provider, None)


class MappingEvaluationResult(BaseModel):
    """Result of evaluating an event against mapping configuration.

    Contains the decision on whether to trigger a run and the
    parameters to use if triggering.

    Attributes:
        should_trigger: Whether the event should trigger a run
        phases: Phases to run if triggering (None = all)
        reason: Human-readable reason for the decision
        matched_condition: Which condition matched (label, mention, etc.)

    Example:
        >>> result = MappingEvaluationResult(
        ...     should_trigger=True,
        ...     phases=["plan", "build"],
        ...     reason="Issue has required label 'adw:auto'",
        ...     matched_condition="require_label",
        ... )
    """

    should_trigger: bool = Field(
        description="Whether the event should trigger a run",
    )
    phases: list[str] | None = Field(
        default=None,
        description="Phases to run if triggering (None = all)",
    )
    reason: str = Field(
        default="",
        description="Human-readable reason for the decision",
    )
    matched_condition: str | None = Field(
        default=None,
        description="Which condition matched (label, mention, etc.)",
    )


# =============================================================================
# GitHub-Specific Models
# =============================================================================


class GitHubUser(BaseModel):
    """GitHub user data.

    Represents a GitHub user or bot that triggered an event.

    Attributes:
        id: The GitHub user ID
        login: The username
        type: The account type ("User" or "Bot")
    """

    id: int = Field(description="GitHub user ID")
    login: str = Field(description="GitHub username")
    type: str = Field(
        default="User",
        description="Account type (User, Bot, Organization)",
    )


class GitHubLabel(BaseModel):
    """GitHub label data.

    Represents a label attached to an issue or pull request.

    Attributes:
        name: The label name
        color: The label color (hex without #)
    """

    name: str = Field(description="Label name")
    color: str = Field(default="", description="Label color (hex)")


class GitHubIssue(BaseModel):
    """GitHub issue data.

    Represents the issue data from a GitHub webhook payload.

    Attributes:
        id: The GitHub issue ID
        number: The issue number (e.g., #42)
        title: The issue title
        body: The issue body/description (may be None)
        state: The issue state ("open" or "closed")
        labels: List of labels attached to the issue
        user: The user who created the issue
        html_url: The URL to view the issue in browser
    """

    id: int = Field(description="GitHub issue ID")
    number: int = Field(description="Issue number")
    title: str = Field(description="Issue title")
    body: str | None = Field(default=None, description="Issue body/description")
    state: str = Field(default="open", description="Issue state (open/closed)")
    labels: list[GitHubLabel] = Field(
        default_factory=list,
        description="Labels attached to the issue",
    )
    user: GitHubUser = Field(description="User who created the issue")
    html_url: str = Field(description="URL to view issue in browser")


class GitHubComment(BaseModel):
    """GitHub comment data.

    Represents a comment on an issue or pull request.

    Attributes:
        id: The GitHub comment ID
        body: The comment text
        user: The user who posted the comment
        html_url: The URL to view the comment in browser
        created_at: When the comment was created
    """

    id: int = Field(description="GitHub comment ID")
    body: str = Field(description="Comment text")
    user: GitHubUser = Field(description="User who posted the comment")
    html_url: str = Field(description="URL to view comment in browser")
    created_at: datetime = Field(description="When comment was created")


class GitHubPullRequest(BaseModel):
    """GitHub pull request data.

    Represents the pull request data from a GitHub webhook payload.

    Attributes:
        id: The GitHub pull request ID
        number: The PR number
        title: The PR title
        body: The PR description (may be None)
        head: The head branch info (ref and sha)
        base: The base branch info (ref and sha)
        html_url: The URL to view the PR in browser
    """

    id: int = Field(description="GitHub pull request ID")
    number: int = Field(description="Pull request number")
    title: str = Field(description="Pull request title")
    body: str | None = Field(default=None, description="Pull request description")
    head: dict[str, Any] = Field(description="Head branch info (ref, sha)")
    base: dict[str, Any] = Field(description="Base branch info (ref, sha)")
    html_url: str = Field(description="URL to view PR in browser")


class GitHubRepository(BaseModel):
    """GitHub repository data.

    Represents the repository where the event occurred.

    Attributes:
        id: The GitHub repository ID
        name: The repository name
        full_name: The full repository name (owner/repo)
        html_url: The URL to view the repository
    """

    id: int = Field(description="GitHub repository ID")
    name: str = Field(description="Repository name")
    full_name: str = Field(description="Full repository name (owner/repo)")
    html_url: str = Field(description="URL to view repository")


class GitHubEvent(BaseModel):
    """Parsed GitHub webhook event.

    Represents a fully parsed GitHub webhook event with typed
    access to common payload fields.

    Attributes:
        event_type: The event type from X-GitHub-Event header
        action: The action that triggered the event
        delivery_id: The unique delivery ID from X-GitHub-Delivery
        issue: The issue data if present
        comment: The comment data if present
        pull_request: The pull request data if present
        sender: The user who triggered the event
        repository: The repository where the event occurred

    Example:
        >>> event = GitHubEvent(
        ...     event_type="issues",
        ...     action="opened",
        ...     delivery_id="abc-123",
        ...     issue=GitHubIssue(...),
        ...     sender=GitHubUser(...),
        ...     repository=GitHubRepository(...),
        ... )
    """

    event_type: str = Field(description="Event type from X-GitHub-Event header")
    action: str = Field(default="", description="Action that triggered event")
    delivery_id: str = Field(default="", description="Unique delivery ID")
    issue: GitHubIssue | None = Field(default=None, description="Issue data if present")
    comment: GitHubComment | None = Field(
        default=None,
        description="Comment data if present",
    )
    pull_request: GitHubPullRequest | None = Field(
        default=None,
        description="Pull request data if present",
    )
    sender: GitHubUser | None = Field(
        default=None,
        description="User who triggered the event",
    )
    repository: GitHubRepository | None = Field(
        default=None,
        description="Repository where event occurred",
    )


# =============================================================================
# Linear-Specific Models (Story 13.3)
# =============================================================================


class LinearLabel(BaseModel):
    """Linear label data structure.

    Represents a label attached to a Linear issue.

    Attributes:
        id: Unique identifier for the label
        name: Display name of the label (e.g., "adw:auto")
        color: Hex color code for the label

    Example:
        >>> label = LinearLabel(id="label-123", name="adw:auto", color="#ff0000")
    """

    id: str = Field(description="Unique identifier for the label")
    name: str = Field(description="Display name of the label")
    color: str | None = Field(default=None, description="Hex color code")


class LinearState(BaseModel):
    """Linear issue state data structure.

    Represents the workflow state of a Linear issue.

    Attributes:
        id: Unique identifier for the state
        name: Display name (e.g., "Todo", "In Progress", "Done")
        color: Hex color code for the state
        type: State type (e.g., "started", "completed", "canceled")

    Example:
        >>> state = LinearState(id="state-1", name="In Progress", type="started")
    """

    id: str = Field(description="Unique identifier for the state")
    name: str = Field(description="Display name of the state")
    color: str | None = Field(default=None, description="Hex color code")
    type: str | None = Field(default=None, description="State type")


class LinearAssignee(BaseModel):
    """Linear issue assignee data structure.

    Represents a user assigned to a Linear issue.

    Attributes:
        id: Unique identifier for the user
        name: Display name of the user
        email: Email address of the user

    Example:
        >>> assignee = LinearAssignee(id="user-1", name="John Doe")
    """

    id: str = Field(description="Unique identifier for the user")
    name: str = Field(description="Display name of the user")
    email: str | None = Field(default=None, description="User email address")


class LinearIssue(BaseModel):
    """Linear issue data structure.

    Represents the full issue data from a Linear webhook payload.
    Used for structured access to issue fields instead of raw dict access.

    Attributes:
        id: Internal UUID for the issue
        identifier: Team-prefixed identifier (e.g., "ENG-123")
        title: Issue title
        description: Issue description (may be null)
        state: Current workflow state
        labels: List of labels attached to the issue
        assignee: Assigned user (may be null)
        url: URL to the issue in Linear

    Example:
        >>> issue = LinearIssue(
        ...     id="uuid",
        ...     identifier="ENG-42",
        ...     title="Add dark mode",
        ...     labels=[LinearLabel(id="1", name="adw:auto")],
        ... )
    """

    id: str = Field(description="Internal UUID for the issue")
    identifier: str = Field(description="Team-prefixed identifier (e.g., ENG-123)")
    title: str = Field(description="Issue title")
    description: str | None = Field(default=None, description="Issue description")
    state: LinearState | None = Field(
        default=None, description="Current workflow state"
    )
    labels: list[LinearLabel] = Field(
        default_factory=list, description="Labels attached to the issue"
    )
    assignee: LinearAssignee | None = Field(default=None, description="Assigned user")
    url: str | None = Field(default=None, description="URL to the issue in Linear")


class LinearComment(BaseModel):
    """Linear comment data structure.

    Represents a comment on a Linear issue.

    Attributes:
        id: Unique identifier for the comment
        body: Comment text content (may contain markdown)
        issue: The issue this comment belongs to

    Example:
        >>> comment = LinearComment(
        ...     id="comment-1",
        ...     body="@adw run --phase build",
        ...     issue=LinearIssue(id="1", identifier="ENG-42", title="Feature"),
        ... )
    """

    id: str = Field(description="Unique identifier for the comment")
    body: str = Field(description="Comment text content")
    issue: LinearIssue | None = Field(
        default=None, description="The issue this comment belongs to"
    )


class LinearEvent(BaseModel):
    """Parsed Linear webhook event with strongly-typed fields.

    Provides structured access to Linear webhook payloads instead of
    raw dictionary access. Can be constructed from a WebhookEvent payload.

    Attributes:
        action: Event action (create, update, remove)
        type: Resource type (Issue, Comment, etc.)
        data: Event-specific payload as dict
        created_at: When the event was created
        webhook_timestamp: Unix timestamp from webhook
        webhook_id: Unique ID for this webhook delivery
        url: Optional URL related to the event

    Example:
        >>> event = LinearEvent(
        ...     action="create",
        ...     type="Issue",
        ...     data={"id": "123", "title": "New feature"},
        ...     created_at=datetime.now(UTC),
        ... )

    Note:
        For type-safe access to issue/comment data, use the helper methods
        `get_issue()` and `get_comment()` which return typed models.
    """

    action: str = Field(description="Event action: create, update, remove")
    type: str = Field(description="Resource type: Issue, Comment, etc.")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific payload"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the event was created",
    )
    webhook_timestamp: int | None = Field(
        default=None, description="Unix timestamp from webhook"
    )
    webhook_id: str | None = Field(
        default=None, description="Unique ID for this webhook delivery"
    )
    url: str | None = Field(default=None, description="Optional URL related to event")

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> LinearEvent:
        """Create a LinearEvent from a raw webhook payload.

        Args:
            payload: The raw webhook payload dictionary.

        Returns:
            Parsed LinearEvent instance.

        Example:
            >>> payload = {"action": "create", "type": "Issue", "data": {...}}
            >>> event = LinearEvent.from_payload(payload)
        """
        # Parse createdAt from Linear's ISO format if present
        created_at_str = payload.get("createdAt")
        created_at: datetime | None = None
        if created_at_str:
            # Linear sends ISO format: "2024-01-15T10:00:00.000Z"
            with contextlib.suppress(ValueError, AttributeError):
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )

        kwargs: dict[str, Any] = {
            "action": payload.get("action", "unknown"),
            "type": payload.get("type", "unknown"),
            "data": payload.get("data", {}),
            "webhook_timestamp": payload.get("webhookTimestamp"),
            "webhook_id": payload.get("webhookId"),
            "url": payload.get("url"),
        }
        if created_at is not None:
            kwargs["created_at"] = created_at

        return cls(**kwargs)

    def get_issue(self) -> LinearIssue | None:
        """Extract typed LinearIssue from event data.

        For Issue events, returns the issue from data.
        For Comment events, returns the issue from data.issue.

        Returns:
            LinearIssue if extractable, None otherwise.
        """
        if self.type == "Issue":
            issue_data = self.data
        elif self.type == "Comment":
            issue_data = self.data.get("issue", {})
        else:
            return None

        if not issue_data:
            return None

        try:
            labels = [LinearLabel(**label) for label in issue_data.get("labels", [])]
            state_data = issue_data.get("state")
            state = LinearState(**state_data) if state_data else None
            assignee_data = issue_data.get("assignee")
            assignee = LinearAssignee(**assignee_data) if assignee_data else None

            return LinearIssue(
                id=issue_data.get("id", ""),
                identifier=issue_data.get("identifier", ""),
                title=issue_data.get("title", ""),
                description=issue_data.get("description"),
                state=state,
                labels=labels,
                assignee=assignee,
                url=issue_data.get("url"),
            )
        except (TypeError, ValueError):
            return None

    def get_comment(self) -> LinearComment | None:
        """Extract typed LinearComment from event data.

        Only valid for Comment events.

        Returns:
            LinearComment if this is a Comment event, None otherwise.
        """
        if self.type != "Comment":
            return None

        try:
            issue = self.get_issue()
            return LinearComment(
                id=self.data.get("id", ""),
                body=self.data.get("body", ""),
                issue=issue,
            )
        except (TypeError, ValueError):
            return None
