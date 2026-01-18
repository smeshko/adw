# Test Reduction Notes:
# Following ADR-001, these tests focus on:
#   - Event evaluation logic (business rules)
#   - Condition matching (label, mention)
#   - Phases override behavior
#   - Edge cases (unknown providers, missing configs)
# NOT testing:
#   - Model serialization (Pydantic handles this)
#   - Default values (visible in model definition)
#   - Import verification

"""Tests for webhook event-to-workflow mapping (Story 13.4)."""

from __future__ import annotations

import pytest

from adw.models.webhook import (
    EventTriggerConfig,
    MappingEvaluationResult,
    ProviderEventMapping,
    WebhookEvent,
    WebhookMappings,
)
from adw.webhook.mapping import EventMapper


class TestEventTriggerConfigValidation:
    """Tests for EventTriggerConfig validation rules."""

    def test_parse_command_requires_require_mention(self) -> None:
        """parse_command=True without require_mention raises ValueError."""
        with pytest.raises(
            ValueError, match="parse_command=True requires require_mention"
        ):
            EventTriggerConfig(parse_command=True)

    def test_parse_command_with_require_mention_valid(self) -> None:
        """parse_command=True with require_mention is valid."""
        config = EventTriggerConfig(
            parse_command=True,
            require_mention="@adw",
        )
        assert config.parse_command is True
        assert config.require_mention == "@adw"


class TestEventMapperEvaluation:
    """Tests for EventMapper.evaluate() business logic."""

    @pytest.fixture
    def mapper_with_config(self) -> EventMapper:
        """Create mapper with full configuration for testing."""
        mappings = WebhookMappings(
            linear=ProviderEventMapping(
                issue_created=EventTriggerConfig(
                    trigger=True,
                    require_label="adw:auto",
                    phases=["plan", "build"],
                ),
                issue_updated=EventTriggerConfig(trigger=False),
                comment_created=EventTriggerConfig(
                    trigger=True,
                    require_mention="@adw",
                    parse_command=True,
                ),
            ),
            github=ProviderEventMapping(
                issue_created=EventTriggerConfig(
                    trigger=True,
                    require_label="adw",
                ),
            ),
        )
        return EventMapper(mappings)

    @pytest.fixture
    def linear_issue_with_label(self) -> WebhookEvent:
        """Linear issue created event with adw:auto label."""
        return WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-123",
                    "title": "Add dark mode",
                    "description": "Implement dark mode for better UX",
                    "labels": [{"name": "adw:auto"}, {"name": "feature"}],
                },
            },
        )

    @pytest.fixture
    def linear_issue_without_label(self) -> WebhookEvent:
        """Linear issue created event without adw:auto label."""
        return WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-456",
                    "title": "Fix bug",
                    "labels": [{"name": "bug"}],
                },
            },
        )

    @pytest.fixture
    def linear_comment_with_mention(self) -> WebhookEvent:
        """Linear comment event with @adw mention."""
        return WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Comment",
                "data": {
                    "id": "comment-789",
                    "body": "Hey @adw run --phase plan",
                    "issue": {"id": "issue-123", "title": "Test"},
                },
            },
        )

    @pytest.fixture
    def linear_comment_without_mention(self) -> WebhookEvent:
        """Linear comment event without @adw mention."""
        return WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Comment",
                "data": {
                    "id": "comment-101",
                    "body": "Just a regular comment",
                    "issue": {"id": "issue-123", "title": "Test"},
                },
            },
        )

    # === Label Matching Tests ===

    def test_evaluate_triggers_when_label_present(
        self,
        mapper_with_config: EventMapper,
        linear_issue_with_label: WebhookEvent,
    ) -> None:
        """Event with required label triggers run."""
        result = mapper_with_config.evaluate(
            "linear", "Issue.create", linear_issue_with_label
        )
        assert result.should_trigger is True
        assert result.matched_condition == "require_label"
        assert "adw:auto" in result.reason

    def test_evaluate_does_not_trigger_when_label_missing(
        self,
        mapper_with_config: EventMapper,
        linear_issue_without_label: WebhookEvent,
    ) -> None:
        """Event missing required label does not trigger."""
        result = mapper_with_config.evaluate(
            "linear", "Issue.create", linear_issue_without_label
        )
        assert result.should_trigger is False
        assert "Missing required label" in result.reason

    # === Mention Matching Tests ===

    def test_evaluate_triggers_when_mention_present(
        self,
        mapper_with_config: EventMapper,
        linear_comment_with_mention: WebhookEvent,
    ) -> None:
        """Comment with required mention triggers run."""
        result = mapper_with_config.evaluate(
            "linear", "Comment.create", linear_comment_with_mention
        )
        assert result.should_trigger is True
        assert result.matched_condition == "require_mention"
        assert "@adw" in result.reason

    def test_evaluate_does_not_trigger_when_mention_missing(
        self,
        mapper_with_config: EventMapper,
        linear_comment_without_mention: WebhookEvent,
    ) -> None:
        """Comment without required mention does not trigger."""
        result = mapper_with_config.evaluate(
            "linear", "Comment.create", linear_comment_without_mention
        )
        assert result.should_trigger is False
        assert "Missing required mention" in result.reason

    # === Phases Override Tests ===

    def test_evaluate_returns_configured_phases(
        self,
        mapper_with_config: EventMapper,
        linear_issue_with_label: WebhookEvent,
    ) -> None:
        """Evaluation result includes phases from config."""
        result = mapper_with_config.evaluate(
            "linear", "Issue.create", linear_issue_with_label
        )
        assert result.phases == ["plan", "build"]

    def test_evaluate_returns_none_phases_when_not_configured(
        self,
        mapper_with_config: EventMapper,
        linear_comment_with_mention: WebhookEvent,
    ) -> None:
        """Evaluation result has None phases when not configured."""
        result = mapper_with_config.evaluate(
            "linear", "Comment.create", linear_comment_with_mention
        )
        assert result.phases is None

    # === Trigger Disabled Tests ===

    def test_evaluate_does_not_trigger_when_disabled(
        self,
        mapper_with_config: EventMapper,
    ) -> None:
        """Event type with trigger=False does not trigger."""
        event = WebhookEvent(
            event_type="Issue.update",
            provider="linear",
            payload={"action": "update", "type": "Issue", "data": {}},
        )
        result = mapper_with_config.evaluate("linear", "Issue.update", event)
        assert result.should_trigger is False
        assert "Trigger disabled" in result.reason

    # === Unknown Provider/Event Tests ===

    def test_evaluate_unknown_provider_does_not_trigger(
        self,
        mapper_with_config: EventMapper,
        linear_issue_with_label: WebhookEvent,
    ) -> None:
        """Unknown provider does not trigger."""
        result = mapper_with_config.evaluate(
            "unknown", "Issue.create", linear_issue_with_label
        )
        assert result.should_trigger is False
        assert "No mapping configured" in result.reason

    def test_evaluate_unknown_event_type_does_not_trigger(
        self,
        mapper_with_config: EventMapper,
    ) -> None:
        """Unknown event type does not trigger."""
        event = WebhookEvent(
            event_type="Unknown.event",
            provider="linear",
            payload={},
        )
        result = mapper_with_config.evaluate("linear", "Unknown.event", event)
        assert result.should_trigger is False
        assert "No mapping configured" in result.reason


class TestEventMapperEmpty:
    """Tests for EventMapper with no configuration."""

    def test_evaluate_with_no_mappings_does_not_trigger(self) -> None:
        """Mapper with no mappings does not trigger any events."""
        mapper = EventMapper(None)
        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={"data": {"labels": [{"name": "adw:auto"}]}},
        )
        result = mapper.evaluate("linear", "Issue.create", event)
        assert result.should_trigger is False


class TestEventTypeNormalization:
    """Tests for event type normalization mapping."""

    @pytest.mark.parametrize(
        "provider,raw_type,expected",
        [
            ("linear", "Issue.create", "issue_created"),
            ("linear", "Issue.update", "issue_updated"),
            ("linear", "Comment.create", "comment_created"),
            # GitHub events use underscore format: {event}_{action}
            ("github", "issues_opened", "issue_created"),
            ("github", "issues_edited", "issue_updated"),
            ("github", "issue_comment_created", "comment_created"),
        ],
    )
    def test_normalization_mapping_exists(
        self,
        provider: str,
        raw_type: str,
        expected: str,
    ) -> None:
        """Event type normalization maps provider-specific types correctly."""
        mapper = EventMapper()
        normalized = mapper._normalize_event_type(provider, raw_type)
        assert normalized == expected

    def test_unknown_type_returns_unchanged(self) -> None:
        """Unknown event type returns unchanged."""
        mapper = EventMapper()
        normalized = mapper._normalize_event_type("linear", "Unknown.custom")
        assert normalized == "Unknown.custom"


class TestConditionMatching:
    """Tests for label and mention matching edge cases."""

    @pytest.fixture
    def mapper_no_conditions(self) -> EventMapper:
        """Mapper with trigger enabled but no conditions."""
        mappings = WebhookMappings(
            linear=ProviderEventMapping(
                issue_created=EventTriggerConfig(trigger=True),
            ),
        )
        return EventMapper(mappings)

    def test_triggers_with_no_conditions(
        self,
        mapper_no_conditions: EventMapper,
    ) -> None:
        """Event triggers when no conditions required."""
        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={"data": {}},
        )
        result = mapper_no_conditions.evaluate("linear", "Issue.create", event)
        assert result.should_trigger is True
        assert result.matched_condition == "default"
        assert "No conditions required" in result.reason

    def test_label_match_case_sensitive(self) -> None:
        """Label matching is case-sensitive."""
        mappings = WebhookMappings(
            linear=ProviderEventMapping(
                issue_created=EventTriggerConfig(
                    trigger=True,
                    require_label="ADW:AUTO",
                ),
            ),
        )
        mapper = EventMapper(mappings)
        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={"data": {"labels": [{"name": "adw:auto"}]}},
        )
        result = mapper.evaluate("linear", "Issue.create", event)
        # Should NOT trigger because labels are case-sensitive
        assert result.should_trigger is False

    def test_mention_match_case_insensitive(self) -> None:
        """Mention matching is case-insensitive."""
        mappings = WebhookMappings(
            linear=ProviderEventMapping(
                comment_created=EventTriggerConfig(
                    trigger=True,
                    require_mention="@ADW",
                ),
            ),
        )
        mapper = EventMapper(mappings)
        event = WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={"data": {"body": "Hey @adw run this"}},
        )
        result = mapper.evaluate("linear", "Comment.create", event)
        # Should trigger because mention matching is case-insensitive
        assert result.should_trigger is True

    def test_label_from_comment_issue(self) -> None:
        """Labels are checked from issue within comment event."""
        mappings = WebhookMappings(
            linear=ProviderEventMapping(
                comment_created=EventTriggerConfig(
                    trigger=True,
                    require_label="priority",
                ),
            ),
        )
        mapper = EventMapper(mappings)
        event = WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "data": {
                    "body": "A comment",
                    "issue": {"labels": [{"name": "priority"}]},
                },
            },
        )
        result = mapper.evaluate("linear", "Comment.create", event)
        assert result.should_trigger is True


class TestMappingEvaluationResultModel:
    """Tests for MappingEvaluationResult model."""

    def test_evaluation_result_fields_populated(self) -> None:
        """MappingEvaluationResult captures all evaluation details."""
        result = MappingEvaluationResult(
            should_trigger=True,
            phases=["plan"],
            reason="Has label",
            matched_condition="require_label",
        )
        assert result.should_trigger is True
        assert result.phases == ["plan"]
        assert result.reason == "Has label"
        assert result.matched_condition == "require_label"
