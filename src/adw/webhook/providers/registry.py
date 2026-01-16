"""Provider Registry for webhook provider management.

This module implements a registry pattern for webhook providers,
allowing dynamic registration and lookup of provider implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adw.webhook.providers.base import WebhookProvider


class ProviderRegistry:
    """Registry for webhook provider implementations.

    Provides a central location for registering and retrieving
    webhook providers. Providers are registered by name and can
    be looked up dynamically at runtime.

    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register(LinearProvider())
        >>> provider = registry.get("linear")
        >>> if provider:
        ...     event = provider.parse_event(request, body)
    """

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._providers: dict[str, WebhookProvider] = {}

    def register(self, provider: WebhookProvider) -> None:
        """Register a provider instance.

        The provider is registered using its `name` property as the key.
        If a provider with the same name already exists, it will be replaced.

        Args:
            provider: The provider instance to register.
        """
        self._providers[provider.name] = provider

    def get(self, name: str) -> WebhookProvider | None:
        """Get a provider by name.

        Args:
            name: The provider name (e.g., 'linear', 'github').

        Returns:
            The provider instance if found, None otherwise.
        """
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names in no particular order.
        """
        return list(self._providers.keys())
