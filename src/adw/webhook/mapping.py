"""Event-to-workflow mapping evaluation.

This module provides the EventMapper class that evaluates webhook events
against configured mapping rules to determine whether to trigger ADW runs.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from adw.models.webhook import (
    EventTriggerConfig,
    MappingEvaluationResult,
    ProviderEventMapping,
    WebhookMappings,
)

if TYPE_CHECKING:
    from adw.models.webhook import WebhookEvent

logger = logging.getLogger(__name__)


# Event type normalization mapping
# Maps provider-specific event types to normalized names
EVENT_TYPE_NORMALIZATION: dict[str, dict[str, str]] = {
    "linear": {
        "Issue.create": "issue_created",
        "Issue.update": "issue_updated",
        "Comment.create": "comment_created",
    },
    "github": {
        # GitHub events use underscore format: {event}_{action}
        # e.g., "issues" event with "opened" action becomes "issues_opened"
        "issues_opened": "issue_created",
        "issues_edited": "issue_updated",
        "issues_labeled": "issue_updated",
        "issue_comment_created": "comment_created",
    },
}


class EventMapper:
    """Evaluates webhook events against configured mappings.

    Determines whether an event should trigger an ADW workflow run
    based on the mapping configuration. Supports conditions like
    required labels, required mentions, and phase restrictions.

    Attributes:
        _mappings: The webhook mappings configuration.

    Example:
        >>> mappings = WebhookMappings(
        ...     linear=ProviderEventMapping(
        ...         issue_created=EventTriggerConfig(
        ...             trigger=True,
        ...             require_label="adw:auto",
        ...         ),
        ...     ),
        ... )
        >>> mapper = EventMapper(mappings)
        >>> result = mapper.evaluate("linear", "Issue.create", event)
        >>> if result.should_trigger:
        ...     print(f"Triggering with phases: {result.phases}")
    """

    def __init__(self, mappings: WebhookMappings | None = None) -> None:
        """Initialize the EventMapper.

        Args:
            mappings: The webhook mappings configuration.
                     If None, no events will trigger runs.
        """
        self._mappings = mappings or WebhookMappings()

    def evaluate(
        self,
        provider: str,
        event_type: str,
        event: WebhookEvent,
    ) -> MappingEvaluationResult:
        """Evaluate if an event should trigger a run.

        Checks the event against configured mapping rules for the
        provider and event type. Evaluates all conditions (label,
        mention) and returns a decision with reasoning.

        Args:
            provider: Provider name (e.g., "linear", "github").
            event_type: The provider-specific event type.
            event: The parsed webhook event.

        Returns:
            MappingEvaluationResult with trigger decision and details.

        Example:
            >>> result = mapper.evaluate("linear", "Issue.create", event)
            >>> result.should_trigger
            True
            >>> result.reason
            "Issue has required label 'adw:auto'"
        """
        # Normalize the event type
        normalized_type = self._normalize_event_type(provider, event_type)

        logger.debug(
            "Evaluating event",
            extra={
                "provider": provider,
                "event_type": event_type,
                "normalized_type": normalized_type,
            },
        )

        # Get mapping configuration for this provider and event type
        config = self._get_event_config(provider, normalized_type)

        if config is None:
            logger.debug(
                "No mapping configured for event type",
                extra={
                    "provider": provider,
                    "normalized_type": normalized_type,
                },
            )
            return MappingEvaluationResult(
                should_trigger=False,
                reason=f"No mapping configured for {provider}/{normalized_type}",
            )

        # Check if triggering is disabled
        if not config.trigger:
            logger.debug(
                "Trigger disabled for event type",
                extra={
                    "provider": provider,
                    "normalized_type": normalized_type,
                },
            )
            return MappingEvaluationResult(
                should_trigger=False,
                reason=f"Trigger disabled for {provider}/{normalized_type}",
            )

        # Check conditions
        return self._check_conditions(config, event)

    def _normalize_event_type(self, provider: str, event_type: str) -> str:
        """Normalize provider-specific event type to common name.

        Args:
            provider: The provider name.
            event_type: The provider-specific event type.

        Returns:
            Normalized event type (e.g., "issue_created").
        """
        provider_map = EVENT_TYPE_NORMALIZATION.get(provider, {})
        return provider_map.get(event_type, event_type)

    def _get_event_config(
        self,
        provider: str,
        normalized_type: str,
    ) -> EventTriggerConfig | None:
        """Get the trigger configuration for a provider/event type.

        Args:
            provider: The provider name.
            normalized_type: The normalized event type.

        Returns:
            EventTriggerConfig if found, None otherwise.
        """
        provider_mapping: ProviderEventMapping | None = (
            self._mappings.get_provider_mapping(provider)
        )
        if provider_mapping is None:
            return None
        return provider_mapping.get_event_config(normalized_type)

    def _check_conditions(
        self,
        config: EventTriggerConfig,
        event: WebhookEvent,
    ) -> MappingEvaluationResult:
        """Check if event meets all required conditions.

        Conditions are evaluated in order:
        1. require_label - event must have specified label
        2. require_mention - event must contain mention string

        All conditions must pass for trigger to activate.

        Args:
            config: The trigger configuration.
            event: The webhook event.

        Returns:
            MappingEvaluationResult with decision and reasoning.
        """
        # Check require_label condition
        if (
            config.require_label is not None
            and not self._has_label(event, config.require_label)
        ):
            logger.debug(
                "Label requirement not met",
                extra={
                    "required_label": config.require_label,
                },
            )
            return MappingEvaluationResult(
                should_trigger=False,
                reason=f"Missing required label '{config.require_label}'",
            )

        # Check require_mention condition
        if (
            config.require_mention is not None
            and not self._has_mention(event, config.require_mention)
        ):
            logger.debug(
                "Mention requirement not met",
                extra={
                    "required_mention": config.require_mention,
                },
            )
            return MappingEvaluationResult(
                should_trigger=False,
                reason=f"Missing required mention '{config.require_mention}'",
            )

        # All conditions passed - determine reason based on what matched
        matched_condition: str | None = None
        reason: str

        if config.require_label:
            matched_condition = "require_label"
            reason = f"Issue has required label '{config.require_label}'"
        elif config.require_mention:
            matched_condition = "require_mention"
            reason = f"Content has required mention '{config.require_mention}'"
        else:
            matched_condition = "default"
            reason = "No conditions required, trigger enabled"

        logger.info(
            "Event evaluation result: trigger",
            extra={
                "reason": reason,
                "matched_condition": matched_condition,
                "phases": config.phases,
            },
        )

        return MappingEvaluationResult(
            should_trigger=True,
            phases=config.phases,
            reason=reason,
            matched_condition=matched_condition,
        )

    def _has_label(self, event: WebhookEvent, label: str) -> bool:
        """Check if event has the specified label.

        Looks for labels in the event payload data. Supports both
        Linear and GitHub label structures.

        Args:
            event: The webhook event.
            label: The label name to find.

        Returns:
            True if label is present, False otherwise.
        """
        data = event.payload.get("data", {})

        # For comment events, labels are on the issue
        if "issue" in data:
            data = data["issue"]

        labels = data.get("labels", [])
        return any(self._label_matches(lbl, label) for lbl in labels)

    def _label_matches(self, label_data: Any, target: str) -> bool:
        """Check if a label entry matches the target label.

        Supports both dict format ({"name": "label"}) and string format.

        Args:
            label_data: The label data from payload.
            target: The target label name.

        Returns:
            True if label matches, False otherwise.
        """
        if isinstance(label_data, dict):
            return label_data.get("name") == target
        if isinstance(label_data, str):
            return label_data == target
        return False

    def _has_mention(self, event: WebhookEvent, mention: str) -> bool:
        """Check if event content contains the specified mention.

        Looks for mention in issue/comment body. Uses case-insensitive
        matching with word boundaries.

        Args:
            event: The webhook event.
            mention: The mention string to find (e.g., "@adw").

        Returns:
            True if mention is found, False otherwise.
        """
        data = event.payload.get("data", {})

        # Check comment body
        body = data.get("body", "")

        # Also check issue description if no comment body
        if not body and "description" in data:
            body = data.get("description", "") or ""

        # Check issue body in issue field (for comment events)
        if not body and "issue" in data:
            issue_data = data["issue"]
            body = issue_data.get("description", "") or ""

        if not body:
            return False

        # Use regex for case-insensitive matching with word boundaries
        # Escape mention to handle @ symbol
        pattern = re.escape(mention)
        return re.search(pattern, body, re.IGNORECASE) is not None
