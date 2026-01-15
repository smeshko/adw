"""Webhook server middleware for request logging."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Module logger - wired to ADW LogManager via Python logging integration
logger = logging.getLogger(__name__)


class WebhookLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all webhook requests with structured data.

    Logs include timestamp, provider, event_type, and payload_size
    for webhook endpoints. Non-webhook requests get basic logging.

    When a log_func is provided, it will be called with the structured
    log data. Otherwise, Python's logging module is used which integrates
    with ADW's LogManager when configured.
    """

    def __init__(self, app: ASGIApp, log_func: Callable[..., None] | None = None):
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
            log_func: Optional logging function. If None, uses Python logging.
        """
        super().__init__(app)
        self._log_func = log_func

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        """Process the request and log webhook details.

        Args:
            request: The incoming request.
            call_next: The next handler in the chain.

        Returns:
            The response from the handler.
        """
        # Generate request ID if not already present
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log the request
        self._log_request(request, response, request_id, duration_ms)

        # Add request ID to response headers
        response.headers["x-request-id"] = request_id

        return response

    def _log_request(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: float,
    ) -> None:
        """Log request details using structured logging.

        Args:
            request: The incoming request.
            response: The outgoing response.
            request_id: The request ID for tracing.
            duration_ms: Request duration in milliseconds.
        """
        # Extract webhook metadata if present
        webhook_metadata = getattr(request.state, "webhook_metadata", None)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        # Add webhook-specific fields if this is a webhook request
        if webhook_metadata:
            log_data.update(
                {
                    "provider": webhook_metadata.get("provider"),
                    "event_type": webhook_metadata.get("event_type"),
                    "payload_size": webhook_metadata.get("payload_size"),
                    "timestamp": webhook_metadata.get("timestamp"),
                }
            )

        # Use the provided log function or Python logging
        if self._log_func:
            self._log_func(**log_data)
        else:
            # Use Python logging with structured extra data
            # This integrates with ADW's LogManager when configured
            if webhook_metadata:
                logger.info(
                    "webhook request: %s %s provider=%s event=%s size=%d status=%d duration=%.2fms",
                    log_data["method"],
                    log_data["path"],
                    log_data.get("provider"),
                    log_data.get("event_type"),
                    log_data.get("payload_size", 0),
                    log_data["status_code"],
                    log_data["duration_ms"],
                    extra=log_data,
                )
            else:
                logger.info(
                    "request: %s %s status=%d duration=%.2fms",
                    log_data["method"],
                    log_data["path"],
                    log_data["status_code"],
                    log_data["duration_ms"],
                    extra=log_data,
                )
