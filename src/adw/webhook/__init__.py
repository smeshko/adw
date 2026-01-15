"""ADW Webhook Server package.

Provides HTTP webhook infrastructure for receiving external events
from providers like Linear, GitHub, and others.
"""

from adw.webhook.config import WebhookConfig
from adw.webhook.server import app, create_app

__all__ = [
    "app",
    "create_app",
    "WebhookConfig",
]
