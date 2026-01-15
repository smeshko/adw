"""Webhook providers package.

This package contains the WebhookProvider protocol and provider implementations
for handling webhooks from external services.

Exports:
    WebhookProvider: Protocol defining the webhook provider interface.
    BaseWebhookProvider: Optional base class with common utilities.
    ProviderRegistry: Registry for managing provider implementations.
    load_providers_from_config: Load providers from WebhookConfig.
    register_provider_factory: Register a provider implementation.
"""

from adw.webhook.providers.base import BaseWebhookProvider, WebhookProvider
from adw.webhook.providers.loader import (
    load_providers_from_config,
    register_provider_factory,
)
from adw.webhook.providers.registry import ProviderRegistry

__all__ = [
    "BaseWebhookProvider",
    "ProviderRegistry",
    "WebhookProvider",
    "load_providers_from_config",
    "register_provider_factory",
]
