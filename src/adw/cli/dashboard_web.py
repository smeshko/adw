"""Web dashboard CLI commands.

Provides the ``adw dashboard web`` command to launch the browser-based
dashboard server. Follows existing CLI patterns (Typer, consistent flags).
"""

from __future__ import annotations

import webbrowser

import typer
from rich.console import Console

console = Console()

dashboard_web_app = typer.Typer(
    name="dashboard",
    help="Dashboard commands for monitoring ADW runs",
    invoke_without_command=True,
)


@dashboard_web_app.callback()
def dashboard_callback(ctx: typer.Context) -> None:
    """Dashboard commands."""
    if ctx.invoked_subcommand is None:
        console.print("Use [cyan]adw dashboard --help[/] for available commands")
        raise typer.Exit()


@dashboard_web_app.command("web")
def web_command(
    port: int = typer.Option(
        8100,
        "--port",
        "-p",
        help="Port to run the dashboard on (default: 8100)",
        min=1,
        max=65535,
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-H",
        help="Host to bind to (default: 127.0.0.1)",
    ),
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Don't open the browser automatically",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable auto-reload for development",
    ),
) -> None:
    """Launch the web dashboard in the browser.

    Starts a FastAPI server serving the HTMX-based dashboard. By default
    binds to 127.0.0.1:8100 and opens the browser automatically.

    The dashboard runs independently of the webhook server (port 8000)
    and both can run concurrently without conflicts.

    Examples:
        adw dashboard web                    # Start on localhost:8100
        adw dashboard web --port 9000        # Custom port
        adw dashboard web --host 0.0.0.0     # Expose on LAN (warning shown)
        adw dashboard web --no-browser       # Don't auto-open browser
        adw dashboard web --reload           # Development mode
    """
    import uvicorn

    # Show startup info
    console.print()
    console.print("[bold]Starting ADW Web Dashboard[/]")
    console.print(f"  Host: [cyan]{host}[/]")
    console.print(f"  Port: [cyan]{port}[/]")
    console.print(f"  URL:  [cyan]http://{host}:{port}[/]")

    # LAN exposure warning (NFR12)
    if host == "0.0.0.0":
        console.print()
        console.print(
            "  [bold yellow]⚠ WARNING:[/] Dashboard is exposed on all "
            "network interfaces."
        )
        console.print("  Only do this on trusted networks.")

    console.print()

    # Auto-open browser (FR45, FR46)
    if not no_browser:
        # Use 127.0.0.1 for browser even if binding to 0.0.0.0
        browser_host = "127.0.0.1" if host == "0.0.0.0" else host
        url = f"http://{browser_host}:{port}"
        console.print(f"  Opening browser: [cyan]{url}[/]")
        try:
            webbrowser.open(url)
        except Exception:
            console.print("  [dim]Could not open browser automatically[/]")

    # Start the server
    if reload:
        uvicorn.run(
            "adw.dashboard.server:create_dashboard_app",
            host=host,
            port=port,
            reload=True,
            factory=True,
        )
    else:
        from adw.dashboard.server import create_dashboard_app

        app = create_dashboard_app(host=host, port=port)
        uvicorn.run(app, host=host, port=port)
