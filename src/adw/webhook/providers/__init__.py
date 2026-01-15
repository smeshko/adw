"""Webhook providers package.

This package contains the WebhookProvider protocol and provider implementations
for handling webhooks from external services.

Exports:
    WebhookProvider: Protocol defining the webhook provider interface.
"""

from adw.webhook.providers.base import WebhookProvider

__all__ = ["WebhookProvider"]
