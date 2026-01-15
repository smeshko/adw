"""Webhook providers package.

This package contains the WebhookProvider protocol and provider implementations
for handling webhooks from external services.

Exports:
    WebhookProvider: Protocol defining the webhook provider interface.
    BaseWebhookProvider: Optional base class with common utilities.
    ProviderRegistry: Registry for managing provider implementations.
"""

from adw.webhook.providers.base import BaseWebhookProvider, WebhookProvider
from adw.webhook.providers.registry import ProviderRegistry

__all__ = ["BaseWebhookProvider", "ProviderRegistry", "WebhookProvider"]
