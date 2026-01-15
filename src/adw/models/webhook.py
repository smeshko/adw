"""Webhook server configuration models.

This module contains Pydantic models for webhook server configuration,
including provider-specific settings and server options.
"""

from __future__ import annotations

import os

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
