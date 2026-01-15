"""Webhook server configuration and event models.

This module contains Pydantic models for webhook server configuration,
event parsing, and run parameter extraction.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Configuration for a single webhook provider.

    Defines settings for an individual webhook provider such as Linear,
    GitHub, or GitLab. Each provider can be enabled/disabled and configured
    with a secret for signature verification.

    Attributes:
        enabled: Whether this provider is enabled (default: False)
        secret_env: Name of environment variable containing the webhook secret

    Example:
        >>> config = ProviderConfig(enabled=True, secret_env="LINEAR_WEBHOOK_SECRET")
        >>> config.enabled
        True
        >>> config.get_secret()  # Returns value of LINEAR_WEBHOOK_SECRET env var
        'secret-value'

    YAML example:
        webhook:
          providers:
            linear:
              enabled: true
              secret_env: LINEAR_WEBHOOK_SECRET
    """

    enabled: bool = Field(
        default=False,
        description="Whether this provider is enabled",
    )
    secret_env: str | None = Field(
        default=None,
        description="Name of environment variable containing the webhook secret",
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

    Defines server settings including host, port, and provider configurations.
    This configuration can be specified in the project's adw.yaml file under
    the 'webhook' key.

    Attributes:
        port: Port to run the webhook server on (default: 8000)
        host: Host to bind the server to (default: "0.0.0.0")
        providers: Dictionary mapping provider names to their configurations

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
        default_factory=lambda: datetime.now(tz=timezone.utc),
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
