"""FastAPI webhook server application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from adw.webhook.config import WebhookConfig
from adw.webhook.routes import router

if TYPE_CHECKING:
    pass


def create_app(config: WebhookConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Webhook configuration. If None, uses default config.

    Returns:
        Configured FastAPI application instance.
    """
    webhook_app = FastAPI(
        title="ADW Webhook Server",
        description="Webhook receiver for ADW external integrations",
        version="0.1.0",
    )

    # Store config in app state for access in routes
    webhook_app.state.webhook_config = config or WebhookConfig()

    # Include routes
    webhook_app.include_router(router)

    return webhook_app


# Default app instance for uvicorn
app = create_app()
