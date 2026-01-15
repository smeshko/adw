"""Webhook server configuration handling.

Re-exports configuration models from adw.models.webhook for convenience.
"""

from adw.models.webhook import ProviderConfig, WebhookConfig

__all__ = [
    "ProviderConfig",
    "WebhookConfig",
]
