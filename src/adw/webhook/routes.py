"""Webhook route handlers."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from adw.webhook.config import WebhookConfig
    from adw.webhook.mapping import EventMapper
    from adw.webhook.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

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

    Uses the provider registry to route requests to the appropriate
    provider implementation for signature verification and event parsing.
    Evaluates events against configured mappings to determine if a run
    should be triggered.
    """
    # Get config, registry, and event mapper from app state
    config: WebhookConfig = request.app.state.webhook_config
    registry: ProviderRegistry = request.app.state.provider_registry
    event_mapper: EventMapper = request.app.state.event_mapper

    # Get provider implementation from registry
    provider_impl = registry.get(provider)

    # Check if provider is in registry
    if provider_impl is None:
        # Provider not in registry - check if it's enabled in config
        if not config.is_provider_enabled(provider):
            # Return 404 with list of available providers
            available = registry.list_providers()
            if available:
                available_str = ", ".join(sorted(available))
                detail = (
                    f"Provider '{provider}' not found. "
                    f"Available providers: {available_str}"
                )
            else:
                detail = f"Provider '{provider}' is not configured or not enabled"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )
        # Provider enabled in config but not in registry - use legacy fallback
        return await _legacy_webhook_handler(provider, request)

    # Provider found in registry - use provider implementation
    # Reuse request ID from middleware for consistent tracing
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    # Get request body (needed for both signature verification and parsing)
    body = await request.body()

    # Verify signature using provider
    if not provider_impl.verify_signature(request, body):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse event using provider
    try:
        event = provider_impl.parse_event(request, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook payload: {e}",
        ) from e

    # Store metadata for logging middleware
    request.state.webhook_metadata = {
        "request_id": request_id,
        "provider": provider,
        "event_type": event.event_type,
        "payload_size": len(body),
        "timestamp": time.time(),
    }

    # Evaluate event against mapping configuration (Story 13.4)
    mapping_result = event_mapper.evaluate(provider, event.event_type, event)

    logger.info(
        "Event evaluation complete",
        extra={
            "request_id": request_id,
            "provider": provider,
            "event_type": event.event_type,
            "should_trigger": mapping_result.should_trigger,
            "reason": mapping_result.reason,
        },
    )

    # If event should trigger a run, extract params and trigger
    trigger_result = None
    if mapping_result.should_trigger:
        # Extract run parameters from provider
        run_params = provider_impl.extract_run_params(event)

        # Override phases from mapping if specified
        if mapping_result.phases is not None:
            run_params = run_params.model_copy(update={"phases": mapping_result.phases})

        logger.info(
            "Triggering ADW run",
            extra={
                "request_id": request_id,
                "feature_request": run_params.feature_request[:100],
                "phases": run_params.phases,
                "source_info": run_params.source_info,
            },
        )

        # Trigger run asynchronously in background
        from adw.webhook.runner import trigger_from_params_async

        trigger_result = await trigger_from_params_async(run_params)

        if trigger_result.success:
            logger.info(
                "Run triggered successfully",
                extra={
                    "request_id": request_id,
                    "run_id": trigger_result.run_id,
                    "process_id": trigger_result.process_id,
                },
            )
        else:
            logger.error(
                "Failed to trigger run",
                extra={
                    "request_id": request_id,
                    "error": trigger_result.error,
                },
            )

    # Build response
    response_content: dict[str, str | bool | None] = {
        "status": "received",
        "request_id": request_id,
        "trigger_evaluation": mapping_result.should_trigger,
    }

    if trigger_result:
        response_content["run_triggered"] = trigger_result.success
        if trigger_result.run_id:
            response_content["run_id"] = trigger_result.run_id

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response_content,
    )


async def _legacy_webhook_handler(
    provider: str,
    request: Request,
) -> JSONResponse:
    """Legacy webhook handler for providers not in registry.

    This preserves backward compatibility for providers that are
    enabled in config but don't have a registry implementation yet.
    """
    # Reuse request ID from middleware for consistent tracing
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    # Get request body
    body = await request.body()

    # Get event type from headers (provider-specific)
    event_type = _get_event_type(provider, request.headers)

    # Store metadata for logging middleware
    request.state.webhook_metadata = {
        "request_id": request_id,
        "provider": provider,
        "event_type": event_type,
        "payload_size": len(body),
        "timestamp": time.time(),
    }

    # Return acknowledgment
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
