"""Linear webhook provider implementation.

This module implements the WebhookProvider protocol for Linear webhooks,
handling signature verification, event parsing, trigger logic, and
run parameter extraction.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from typing import TYPE_CHECKING, Any

from adw.models.webhook import RunParams, WebhookConfig, WebhookEvent
from adw.webhook.providers.base import BaseWebhookProvider
from adw.webhook.providers.loader import register_provider_factory

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)

# Pattern to match @adw run command in comments
ADW_COMMAND_PATTERN = re.compile(r"@adw\s+run\s*(.*)", re.IGNORECASE)

# Default label that triggers automatic runs
DEFAULT_AUTO_LABEL = "adw:auto"


class LinearProvider:
    """Webhook provider for Linear.

    Implements the WebhookProvider protocol to handle webhooks from Linear,
    including signature verification, event parsing, trigger detection,
    and run parameter extraction.

    Attributes:
        _config: The webhook configuration containing provider settings.
        _secret: The webhook secret for signature verification.
        _auto_label: Label that triggers automatic runs.
        _mention_pattern: Pattern to detect @adw run commands.

    Example:
        >>> config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        >>> provider = LinearProvider(config)
        >>> event = provider.parse_event(request, body)
        >>> if provider.should_trigger_run(event):
        ...     params = provider.extract_run_params(event)
    """

    def __init__(
        self,
        config: WebhookConfig,
        *,
        secret: str | None = None,
        auto_label: str = DEFAULT_AUTO_LABEL,
    ) -> None:
        """Initialize the Linear provider.

        Args:
            config: The webhook configuration.
            secret: The webhook secret for signature verification.
                   If not provided, will attempt to get from config.
            auto_label: Label that triggers automatic runs.
        """
        self._config = config
        self._auto_label = auto_label

        # Get secret from parameter or config
        if secret is not None:
            self._secret = secret
        else:
            linear_config = config.get_provider("linear")
            self._secret = linear_config.get_secret() if linear_config else None

        logger.debug(
            "LinearProvider initialized",
            extra={
                "has_secret": self._secret is not None,
                "auto_label": self._auto_label,
            },
        )

    @property
    def name(self) -> str:
        """Return the provider name.

        Returns:
            The string 'linear'.
        """
        return "linear"

    def verify_signature(self, request: Request, body: bytes) -> bool:
        """Verify the Linear webhook signature.

        Linear uses HMAC-SHA256 for signature verification. The signature
        is passed in the X-Linear-Signature header.

        Args:
            request: The incoming FastAPI request.
            body: The raw request body bytes.

        Returns:
            True if signature is valid or no secret configured.
            False if signature is invalid or missing.
        """
        # If no secret configured, skip verification
        if not self._secret:
            logger.warning(
                "No webhook secret configured for Linear - skipping signature verification"
            )
            return True

        # Get signature from header
        signature = BaseWebhookProvider.get_header(request, "x-linear-signature")
        if not signature:
            logger.warning("Missing X-Linear-Signature header")
            return False

        # Compute expected signature
        expected = hmac.new(
            self._secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected, signature)

        if not is_valid:
            logger.warning("Invalid Linear webhook signature")

        return is_valid

    def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
        """Parse a Linear webhook payload into a WebhookEvent.

        Linear webhooks have the structure:
        {
            "action": "create" | "update" | "remove",
            "type": "Issue" | "Comment" | ...,
            "data": { ... },
            "createdAt": "2024-01-15T10:00:00.000Z"
        }

        Args:
            request: The incoming FastAPI request.
            body: The raw request body bytes.

        Returns:
            Parsed WebhookEvent.

        Raises:
            ValueError: If the body cannot be parsed.
        """
        # Parse JSON body
        payload = BaseWebhookProvider.parse_json_body(body)

        # Extract event info
        action = payload.get("action", "unknown")
        event_type = payload.get("type", "unknown")

        # Create compound event type (e.g., "Issue.create")
        compound_type = f"{event_type}.{action}"

        # Extract relevant headers
        headers = {
            "x-linear-event": BaseWebhookProvider.get_header(
                request, "x-linear-event", ""
            )
            or "",
        }

        logger.debug(
            "Parsed Linear event",
            extra={
                "event_type": compound_type,
                "action": action,
            },
        )

        return WebhookEvent(
            event_type=compound_type,
            provider="linear",
            payload=payload,
            headers=headers,
            raw_body=body,
        )

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        """Determine if this event should trigger an ADW run.

        Triggers are:
        1. Issue created with adw:auto label
        2. Comment created containing @adw run command

        Args:
            event: The parsed webhook event.

        Returns:
            True if run should be triggered.
        """
        event_type = event.event_type
        data = event.payload.get("data", {})

        # Check for issue creation with auto label
        if event_type == "Issue.create":
            return self._has_auto_label(data)

        # Check for comment with @adw run command
        if event_type == "Comment.create":
            return self._has_adw_command(data)

        return False

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        """Extract run parameters from a Linear event.

        Builds feature_request from issue title + description,
        extracts phases from comment command if present.

        Args:
            event: The parsed webhook event.

        Returns:
            RunParams ready to start an ADW run.
        """
        event_type = event.event_type
        data = event.payload.get("data", {})

        # Extract issue data (directly or from comment's issue)
        if event_type == "Comment.create":
            issue_data = data.get("issue", {})
            triggered_by = "comment"
            comment_body = data.get("body", "")
            phases = self._parse_phases_from_command(comment_body)
        else:
            issue_data = data
            triggered_by = "label"
            phases = None

        # Build feature request from title and description
        title = issue_data.get("title", "")
        description = issue_data.get("description") or ""

        if description:
            feature_request = f"{title}\n\n{description}"
        else:
            feature_request = title

        # Extract metadata
        issue_id = issue_data.get("id", "")
        identifier = issue_data.get("identifier", "")
        issue_url = issue_data.get("url", "")

        return RunParams(
            feature_request=feature_request,
            phases=phases,
            source_info={
                "issue_url": issue_url,
            },
            metadata={
                "linear_issue_id": issue_id,
                "linear_identifier": identifier,
                "triggered_by": triggered_by,
            },
        )

    def _has_auto_label(self, data: dict[str, Any]) -> bool:
        """Check if issue data has the auto-trigger label.

        Args:
            data: The issue data from the webhook payload.

        Returns:
            True if adw:auto label is present.
        """
        labels = data.get("labels", [])
        for label in labels:
            if label.get("name") == self._auto_label:
                return True
        return False

    def _has_adw_command(self, data: dict[str, Any]) -> bool:
        """Check if comment contains @adw run command.

        Args:
            data: The comment data from the webhook payload.

        Returns:
            True if @adw run command is present.
        """
        body = data.get("body", "")
        return ADW_COMMAND_PATTERN.search(body) is not None

    def _parse_phases_from_command(self, text: str) -> list[str] | None:
        """Parse phases from @adw run command.

        Looks for --phase flag in the command text.

        Args:
            text: The comment body text.

        Returns:
            List of phases if --phase flag found, None otherwise.
        """
        match = ADW_COMMAND_PATTERN.search(text)
        if not match:
            return None

        args = match.group(1).strip()

        # Parse --phase flag
        phase_match = re.search(r"--phase\s+(\w+)", args)
        if phase_match:
            return [phase_match.group(1)]

        return None


def _create_linear_provider(config: WebhookConfig) -> LinearProvider:
    """Factory function for creating LinearProvider instances.

    Args:
        config: The webhook configuration.

    Returns:
        Configured LinearProvider instance.
    """
    return LinearProvider(config)


# Register the provider factory on module import
register_provider_factory("linear", _create_linear_provider)
