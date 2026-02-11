"""FastAPI webhook server application.

Uses the shared ``server.app.create_app`` factory and layers on
webhook-specific routes, middleware, and provider configuration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from rich.console import Console

from adw.server.app import create_app as _create_base_app
from adw.webhook.config import WebhookConfig
from adw.webhook.mapping import EventMapper
from adw.webhook.middleware import WebhookLoggingMiddleware

# Import providers package to trigger factory registration via __init__.py
# This ensures LinearProvider and other providers are registered before loading
from adw.webhook.providers import load_providers_from_config
from adw.webhook.providers.registry import ProviderRegistry
from adw.webhook.routes import router

# Rich console for CLI output
console = Console()


def _load_config_from_project() -> WebhookConfig:
    """Load webhook config from project project.yaml.

    Returns:
        WebhookConfig from project config, or default config if not available.

    Note:
        This function is used when creating the default app instance
        (e.g., for uvicorn reload mode) to ensure project config is honored.
    """
    try:
        from adw.config.loader import ConfigLoader
        from adw.exceptions import ConfigError

        config = ConfigLoader().load()
        return config.webhook
    except (ConfigError, FileNotFoundError):
        # No config file or .adw directory - use defaults
        # This is expected when running outside a project context
        return WebhookConfig()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage server startup and shutdown events.

    Displays Rich console output for server lifecycle events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during server runtime.
    """
    # Startup
    config: WebhookConfig = app.state.webhook_config
    enabled_providers = [
        name for name, prov in config.providers.items() if prov.enabled
    ]

    console.print()
    console.print("[bold green]ADW Webhook Server Starting[/]")
    console.print(f"  Host: [cyan]{config.host}[/]")
    console.print(f"  Port: [cyan]{config.port}[/]")
    if enabled_providers:
        console.print(f"  Providers: [cyan]{', '.join(enabled_providers)}[/]")
    else:
        console.print("  Providers: [yellow]none configured[/]")
    console.print()

    yield

    # Shutdown
    console.print()
    console.print("[bold yellow]ADW Webhook Server Shutting Down[/]")
    console.print()


def create_app(
    config: WebhookConfig | None = None,
    log_func: Callable[..., None] | None = None,
    registry: ProviderRegistry | None = None,
    event_mapper: EventMapper | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Uses the shared ``server.app.create_app`` factory for common
    infrastructure (RequestIDMiddleware, state seeding) and layers on
    webhook-specific routes, middleware, and provider configuration.

    Args:
        config: Webhook configuration. If None, uses default config.
        log_func: Optional logging function for the middleware.
            If None, logging is disabled in middleware.
        registry: Optional provider registry. If None, creates empty registry.
        event_mapper: Optional event mapper. If None, creates from config mappings.

    Returns:
        Configured FastAPI application instance.
    """
    webhook_config = config or WebhookConfig()
    # Load providers from config if no registry provided
    provider_registry = registry or load_providers_from_config(webhook_config)
    # Create event mapper from config mappings if not provided
    mapper = event_mapper or EventMapper(webhook_config.mappings)

    webhook_app = _create_base_app(
        title="ADW Webhook Server",
        description="Webhook receiver for ADW external integrations",
        version="0.1.0",
        lifespan=lifespan,
        state={
            "webhook_config": webhook_config,
            "provider_registry": provider_registry,
            "event_mapper": mapper,
        },
    )

    # Add request logging middleware (runs after RequestIDMiddleware)
    webhook_app.add_middleware(WebhookLoggingMiddleware, log_func=log_func)

    # Include routes
    webhook_app.include_router(router)

    return webhook_app


# Default app instance for uvicorn (reload mode)
# Loads config from project project.yaml so reload mode honors project settings
app = create_app(config=_load_config_from_project())
