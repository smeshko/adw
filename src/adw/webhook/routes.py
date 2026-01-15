"""Webhook route handlers."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from adw.webhook.config import WebhookConfig

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@router.post("/webhook/{provider}")
async def receive_webhook(
    provider: str,
    request: Request,
) -> JSONResponse:
    """Receive and process webhook from a provider.

    This is a skeleton implementation that logs the request
    and returns 404 for unknown providers. Provider-specific
    handlers will be implemented in future stories.
    """
    # Get config from app state
    config: WebhookConfig = request.app.state.webhook_config

    # Check if provider is configured and enabled
    if not config.is_provider_enabled(provider):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' is not configured or not enabled",
        )

    # Reuse request ID from middleware for consistent tracing
    # Falls back to new UUID if middleware hasn't set one
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    # Get request body
    body = await request.body()

    # Get event type from headers (provider-specific)
    event_type = _get_event_type(provider, request.headers)

    # Log the webhook (using structured logging in Step 6)
    # For now, store metadata for logging middleware
    request.state.webhook_metadata = {
        "request_id": request_id,
        "provider": provider,
        "event_type": event_type,
        "payload_size": len(body),
        "timestamp": time.time(),
    }

    # Return acknowledgment
    # Future stories will add actual event processing
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "received",
            "request_id": request_id,
        },
    )


def _get_event_type(provider: str, headers: Mapping[str, str]) -> str | None:
    """Extract event type from provider-specific headers."""
    # Common patterns for webhook event type headers
    header_mappings = {
        "linear": "x-linear-event",
        "github": "x-github-event",
        "gitlab": "x-gitlab-event",
        "stripe": "stripe-event-type",
    }

    header_name = header_mappings.get(provider.lower())
    if header_name:
        return headers.get(header_name)

    return None
