"""Dashboard FastAPI application factory.

Builds the dashboard's FastAPI app with its routes, Jinja2 templates,
and static file serving.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from rich.console import Console
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.templating import Jinja2Templates

from adw.format import (
    format_cost,
    format_duration,
    format_relative_time,
    format_size,
    format_tokens,
)

console = Console()

# Resolve template and static directories relative to this file
_PACKAGE_DIR = Path(__file__).resolve().parent
_TEMPLATE_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"


@asynccontextmanager
async def _dashboard_lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Dashboard startup / shutdown lifecycle."""
    host = getattr(app.state, "dashboard_host", "127.0.0.1")
    port = getattr(app.state, "dashboard_port", 8100)

    console.print()
    console.print("[bold green]ADW Dashboard Server Starting[/]")
    console.print(f"  Host: [cyan]{host}[/]")
    console.print(f"  Port: [cyan]{port}[/]")
    console.print(f"  URL:  [cyan]http://{host}:{port}[/]")

    if host == "0.0.0.0":
        console.print(
            "\n  [bold yellow]⚠ WARNING:[/] Dashboard is exposed on all "
            "network interfaces.\n  Only do this on trusted networks."
        )

    console.print()
    yield

    console.print()
    console.print("[bold yellow]ADW Dashboard Server Shutting Down[/]")
    console.print()


def build_templates() -> Jinja2Templates:
    """Build the dashboard's Jinja environment with its filters registered."""
    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    templates.env.filters.update(
        duration=format_duration,
        tokens=format_tokens,
        relative_time=format_relative_time,
        cost=format_cost,
        filesize=format_size,
    )
    return templates


def create_dashboard_app(
    host: str = "127.0.0.1",
    port: int = 8100,
) -> FastAPI:
    """Create and configure the dashboard FastAPI application.

    Args:
        host: Host the server will bind to (stored in state for lifespan).
        port: Port the server will bind to (stored in state for lifespan).

    Returns:
        Configured FastAPI application for the web dashboard.
    """
    app = FastAPI(
        title="ADW Dashboard",
        description="Web dashboard for ADW run monitoring",
        version="0.1.0",
        lifespan=_dashboard_lifespan,
    )
    app.state.dashboard_host = host
    app.state.dashboard_port = port

    # Jinja2 templates
    templates = build_templates()
    app.state.templates = templates

    # Static files (HTMX, CSS, etc.)
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # Include dashboard routes
    from adw.dashboard.mutations import router as mutations_router
    from adw.dashboard.partials import router as partials_router
    from adw.dashboard.routes import router as pages_router

    app.include_router(pages_router)
    app.include_router(partials_router)
    app.include_router(mutations_router)

    # HTML-only exception handlers – never return JSON from the dashboard
    def _render_error(request: Request, status_code: int, detail: str) -> HTMLResponse:
        context = {
            "request": request,
            "status_code": status_code,
            "error_message": detail,
            "page": "",
            "projects": [],
            "selected_project": None,
            "active_run_count": 0,
            "last_updated_ago": "—",
        }
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=templates.get_template("partials/error_banner.html").render(
                    context
                ),
                status_code=status_code,
            )
        return HTMLResponse(
            content=templates.get_template("pages/error.html").render(context),
            status_code=status_code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> HTMLResponse:
        detail = str(exc.detail) if exc.detail else "An unexpected error occurred."
        return _render_error(request, exc.status_code, detail)

    @app.exception_handler(Exception)
    async def _generic_exception_handler(
        request: Request, exc: Exception
    ) -> HTMLResponse:
        return _render_error(request, 500, "An unexpected error occurred.")

    return app
