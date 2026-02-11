"""Shared FastAPI application factory for ADW web services.

Provides a common server factory used by both the webhook server and
the web dashboard. Each service composes its own APIRouters and
middleware on top of the shared base.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Global middleware that assigns a unique request ID to every request.

    Generates a UUID-based request ID for each incoming request and stores
    it in ``request.state.request_id``. The ID is also returned in the
    ``x-request-id`` response header for client-side correlation.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def create_app(
    *,
    title: str = "ADW Server",
    description: str = "",
    version: str = "0.1.0",
    lifespan: Any | None = None,
    state: dict[str, Any] | None = None,
) -> FastAPI:
    """Create a FastAPI application with shared infrastructure.

    This factory provides the common base that both the webhook server
    and the dashboard server build upon. It wires up the global
    ``RequestIDMiddleware`` and optionally accepts a lifespan handler
    and initial state values.

    Args:
        title: OpenAPI title for the application.
        description: OpenAPI description.
        version: API version string.
        lifespan: Optional lifespan context manager for startup/shutdown.
        state: Optional dict of key/value pairs to set on ``app.state``.

    Returns:
        A configured FastAPI application with RequestIDMiddleware.
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
    )

    # Global middleware — applies to all services
    app.add_middleware(RequestIDMiddleware)

    # Seed application state
    if state:
        for key, value in state.items():
            setattr(app.state, key, value)

    return app
