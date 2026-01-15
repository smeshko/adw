"""Provider loading utilities.

This module provides functionality for loading and registering
webhook providers based on project configuration.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from adw.webhook.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from adw.models.webhook import WebhookConfig
    from adw.webhook.providers.base import WebhookProvider

logger = logging.getLogger(__name__)

# Registry of available provider implementations
# Format: {"provider_name": factory_function}
# Factory functions take WebhookConfig and return a provider instance
_PROVIDER_FACTORIES: dict[str, Callable[[WebhookConfig], WebhookProvider]] = {
    # Providers will be registered here as they are implemented:
    # "linear": lambda config: LinearProvider(config),
    # "github": lambda config: GitHubProvider(config),
}


def get_available_providers() -> dict[str, Callable[[WebhookConfig], WebhookProvider]]:
    """Get the mapping of available provider implementations.

    Returns:
        Dictionary mapping provider names to their factory functions.

    Note:
        This returns the internal registry. Providers are added to this
        registry as they are implemented in future stories.
    """
    return _PROVIDER_FACTORIES.copy()


def load_providers_from_config(config: WebhookConfig | None) -> ProviderRegistry:
    """Load and register providers based on configuration.

    Iterates through enabled providers in the config and registers
    any that have available implementations.

    Args:
        config: The webhook configuration, or None.

    Returns:
        A ProviderRegistry with available providers registered.

    Note:
        Providers that are enabled in config but don't have implementations
        will be logged but not registered. This allows graceful degradation.
    """
    registry = ProviderRegistry()

    if config is None:
        logger.debug("No webhook config provided, returning empty registry")
        return registry

    for provider_name, provider_config in config.providers.items():
        if not provider_config.enabled:
            logger.debug("Provider '%s' is disabled, skipping", provider_name)
            continue

        # Check if implementation is available
        factory = _PROVIDER_FACTORIES.get(provider_name)
        if factory is None:
            logger.info(
                "Provider '%s' is enabled but implementation not available",
                provider_name,
            )
            continue

        try:
            provider = factory(config)
            registry.register(provider)
            logger.info("Registered provider: %s", provider_name)
        except Exception:
            logger.exception("Failed to initialize provider: %s", provider_name)

    return registry


def register_provider_factory(
    name: str,
    factory: Callable[[WebhookConfig], WebhookProvider],
) -> None:
    """Register a provider factory function.

    This is used by provider implementations to register themselves
    so they can be loaded from configuration.

    Args:
        name: The provider name (e.g., "linear", "github").
        factory: A function that takes WebhookConfig and returns a provider.

    Example:
        >>> def create_linear_provider(config):
        ...     return LinearProvider(config)
        >>> register_provider_factory("linear", create_linear_provider)
    """
    _PROVIDER_FACTORIES[name] = factory
    logger.debug("Registered provider factory: %s", name)
