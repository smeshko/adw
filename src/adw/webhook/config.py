"""Webhook server configuration handling."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class ProviderConfig(BaseModel):
    """Configuration for a single webhook provider."""

    enabled: bool = False
    secret_env: str | None = None

    def get_secret(self) -> str | None:
        """Get the secret from environment variable."""
        if self.secret_env:
            return os.getenv(self.secret_env)
        return None


class WebhookConfig(BaseModel):
    """Configuration for the webhook server."""

    port: int = Field(default=8000, ge=1, le=65535)
    host: str = "0.0.0.0"
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    def get_provider(self, name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider."""
        return self.providers.get(name)

    def is_provider_enabled(self, name: str) -> bool:
        """Check if a provider is enabled."""
        provider = self.get_provider(name)
        return provider.enabled if provider else False
