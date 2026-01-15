"""FastAPI webhook server application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator, Callable

from fastapi import FastAPI
from rich.console import Console

from adw.webhook.config import WebhookConfig
from adw.webhook.middleware import WebhookLoggingMiddleware
from adw.webhook.routes import router

if TYPE_CHECKING:
    pass

# Rich console for CLI output
console = Console()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Webhook configuration. If None, uses default config.
        log_func: Optional logging function for the middleware.
            If None, logging is disabled in middleware.

    Returns:
        Configured FastAPI application instance.
    """
    webhook_config = config or WebhookConfig()

    webhook_app = FastAPI(
        title="ADW Webhook Server",
        description="Webhook receiver for ADW external integrations",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store config in app state for access in routes
    webhook_app.state.webhook_config = webhook_config

    # Add request logging middleware
    webhook_app.add_middleware(WebhookLoggingMiddleware, log_func=log_func)

    # Include routes
    webhook_app.include_router(router)

    return webhook_app


# Default app instance for uvicorn
app = create_app()
