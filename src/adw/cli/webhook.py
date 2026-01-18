"""Webhook server CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console

from adw.config.loader import ConfigLoader
from adw.exceptions import ConfigError
from adw.models.webhook import WebhookConfig

console = Console()

webhook_app = typer.Typer(
    name="webhook",
    help="Webhook server commands for receiving external events",
    invoke_without_command=True,
)


@webhook_app.callback()
def webhook_callback(ctx: typer.Context) -> None:
    """Webhook server management commands."""
    if ctx.invoked_subcommand is None:
        console.print("Use [cyan]adw webhook --help[/] for available commands")
        raise typer.Exit()


@webhook_app.command("start")
def start_server(
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="Port to run the server on (default: 8000 or from config)",
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        "-H",
        help="Host to bind to (default: 0.0.0.0 or from config)",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable auto-reload for development",
    ),
) -> None:
    """Start the webhook server.

    Starts a FastAPI server that receives webhooks from configured providers.
    Server settings are read from project.yaml's webhook section, or can be
    overridden with command-line options.

    Examples:
        adw webhook start
        adw webhook start --port 9000
        adw webhook start --reload  # Development mode
        adw webhook start --host 127.0.0.1 --port 8080
    """
    import uvicorn

    # Load config from project.yaml if available
    webhook_config = _load_webhook_config()

    # Apply command-line overrides
    effective_host = host if host is not None else webhook_config.host
    effective_port = port if port is not None else webhook_config.port

    # Show configuration
    console.print()
    console.print("[bold]Starting ADW Webhook Server[/]")
    console.print(f"  Host: [cyan]{effective_host}[/]")
    console.print(f"  Port: [cyan]{effective_port}[/]")
    console.print(f"  Reload: [cyan]{reload}[/]")

    enabled_providers = [
        name for name, prov in webhook_config.providers.items() if prov.enabled
    ]
    if enabled_providers:
        console.print(f"  Providers: [cyan]{', '.join(enabled_providers)}[/]")
    else:
        console.print("  Providers: [yellow]none enabled[/]")

    console.print()

    # Create app with config
    # Note: We use the string import path so uvicorn can reload the module
    # For reload mode, config is re-read on each reload
    if reload:
        # In reload mode, use string import path
        uvicorn.run(
            "adw.webhook.server:app",
            host=effective_host,
            port=effective_port,
            reload=True,
        )
    else:
        # In production mode, create app with config directly for proper setup
        from adw.webhook.server import create_app

        app = create_app(config=webhook_config)
        uvicorn.run(app, host=effective_host, port=effective_port)


@webhook_app.command("status")
def server_status() -> None:
    """Show webhook server status (placeholder).

    This is a placeholder command that will be implemented in a future story
    to show the status of a running webhook server.

    Examples:
        adw webhook status
    """
    console.print("[yellow]Webhook status command not yet implemented[/]")
    console.print()
    console.print("This will show:")
    console.print("  - Whether the server is running")
    console.print("  - Configured providers and their status")
    console.print("  - Recent webhook activity")


def _load_webhook_config() -> WebhookConfig:
    """Load webhook configuration from project.yaml.

    Returns:
        WebhookConfig from project config, or default config if not available.
    """
    try:
        config = ConfigLoader().load()
        return config.webhook
    except ConfigError:
        # No config or invalid - use defaults
        console.print(
            "[dim]Note: No project.yaml found, using default webhook configuration[/]"
        )
        return WebhookConfig()
    except FileNotFoundError:
        # No .adw directory
        console.print(
            "[dim]Note: No .adw directory found, using default webhook configuration[/]"
        )
        return WebhookConfig()
