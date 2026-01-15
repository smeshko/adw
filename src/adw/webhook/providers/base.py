"""WebhookProvider Protocol definition.

This module defines the Protocol for webhook provider implementations,
providing a consistent interface for different webhook sources (Linear,
GitHub, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import Request

    from adw.models.webhook import RunParams, WebhookEvent


@runtime_checkable
class WebhookProvider(Protocol):
    """Protocol for webhook provider implementations.

    Each provider handles webhooks from a specific external service
    (Linear, GitHub, etc.) and knows how to verify, parse, and
    process events from that service.

    This Protocol uses structural subtyping - any class implementing
    these methods will satisfy the Protocol without explicit inheritance.

    Example:
        >>> class LinearProvider:
        ...     @property
        ...     def name(self) -> str:
        ...         return "linear"
        ...
        ...     def verify_signature(self, request: Request) -> bool:
        ...         # Verify Linear-specific signature
        ...         return True
        ...
        ...     def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
        ...         # Parse Linear webhook payload
        ...         return WebhookEvent(...)
        ...
        ...     def should_trigger_run(self, event: WebhookEvent) -> bool:
        ...         # Check Linear-specific trigger conditions
        ...         return event.event_type == "IssueCreate"
        ...
        ...     def extract_run_params(self, event: WebhookEvent) -> RunParams:
        ...         # Extract params from Linear issue
        ...         return RunParams(...)
        >>>
        >>> provider: WebhookProvider = LinearProvider()  # Type checks!
    """

    @property
    def name(self) -> str:
        """Unique provider identifier.

        Used for routing webhooks to the correct provider and
        for logging/debugging purposes.

        Returns:
            Provider name (e.g., 'linear', 'github').
        """
        ...

    def verify_signature(self, request: Request) -> bool:
        """Verify the request came from the claimed provider.

        Each provider has its own signature verification mechanism:
        - Linear: HMAC-SHA256 with X-Linear-Signature header
        - GitHub: HMAC-SHA256 with X-Hub-Signature-256 header
        - etc.

        Args:
            request: The incoming FastAPI Request object.

        Returns:
            True if signature is valid, False otherwise.

        Note:
            Implementations should use constant-time comparison
            to prevent timing attacks.
        """
        ...

    def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
        """Parse the raw request into a structured WebhookEvent.

        Extracts provider-specific event information from the request
        headers and payload.

        Args:
            request: The incoming FastAPI Request object.
            body: The raw request body bytes.

        Returns:
            Parsed WebhookEvent with provider-specific details.

        Raises:
            ValueError: If request cannot be parsed.
        """
        ...

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        """Determine if this event should trigger an ADW run.

        Considers event type, labels, configuration rules, etc.
        Each provider defines its own trigger logic.

        Examples:
            - Linear: Issue created with 'adw' label
            - GitHub: Issue opened in monitored repo

        Args:
            event: The parsed webhook event.

        Returns:
            True if run should be triggered, False otherwise.
        """
        ...

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        """Extract parameters needed to start an ADW run.

        Transforms provider-specific event data into the common
        RunParams format used by the ADW pipeline.

        Args:
            event: The parsed webhook event.

        Returns:
            RunParams with feature_request, phases, and metadata.
        """
        ...
