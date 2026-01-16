"""ADW Webhook Server package.

Provides HTTP webhook infrastructure for receiving external events
from providers like Linear, GitHub, and others.
"""

from adw.webhook.config import ProviderConfig, WebhookConfig
from adw.webhook.middleware import WebhookLoggingMiddleware
from adw.webhook.security import (
    ENV_GITHUB_WEBHOOK_SECRET,
    ENV_LINEAR_WEBHOOK_SECRET,
    HEADER_GITHUB_SIGNATURE_256,
    HEADER_LINEAR_SIGNATURE,
    SignatureVerificationError,
    verify_github_signature,
    verify_hmac_signature,
    verify_linear_signature,
)
from adw.webhook.server import app, create_app

__all__ = [
    # Server
    "app",
    "create_app",
    # Config
    "ProviderConfig",
    "WebhookConfig",
    # Middleware
    "WebhookLoggingMiddleware",
    # Security
    "ENV_GITHUB_WEBHOOK_SECRET",
    "ENV_LINEAR_WEBHOOK_SECRET",
    "HEADER_GITHUB_SIGNATURE_256",
    "HEADER_LINEAR_SIGNATURE",
    "SignatureVerificationError",
    "verify_github_signature",
    "verify_hmac_signature",
    "verify_linear_signature",
]
