"""Tests for Linear webhook provider.

Following ADR-001: Tests focus on business logic, validation, and error paths.
Avoid trivial attribute tests and Pydantic serialization smoke tests.
"""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import MagicMock

import pytest

from adw.models.webhook import ProviderConfig, WebhookConfig


class TestLinearProviderProtocol:
    """Tests that LinearProvider satisfies the WebhookProvider Protocol."""

    def test_linear_provider_implements_protocol(self) -> None:
        """LinearProvider should implement the WebhookProvider protocol."""
        from adw.webhook.providers.base import WebhookProvider
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True, secret_env="TEST_SECRET")}
        )
        provider = LinearProvider(config)
        assert isinstance(provider, WebhookProvider)

    def test_linear_provider_name_is_linear(self) -> None:
        """LinearProvider.name should be 'linear'."""
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)
        assert provider.name == "linear"


class TestLinearProviderSignatureVerification:
    """Tests for Linear HMAC-SHA256 signature verification."""

    def test_verify_signature_valid(self) -> None:
        """Should return True for valid HMAC-SHA256 signature."""
        from adw.webhook.providers.linear import LinearProvider

        secret = "test_webhook_secret"
        config = WebhookConfig(
            providers={
                "linear": ProviderConfig(enabled=True, secret_env="LINEAR_SECRET")
            }
        )
        provider = LinearProvider(config, secret=secret)

        body = b'{"action":"create","type":"Issue"}'
        expected_signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        request = MagicMock()
        request.headers = {"x-linear-signature": expected_signature}

        assert provider.verify_signature(request, body) is True

    def test_verify_signature_invalid(self) -> None:
        """Should return False for invalid signature."""
        from adw.webhook.providers.linear import LinearProvider

        secret = "test_webhook_secret"
        config = WebhookConfig(
            providers={
                "linear": ProviderConfig(enabled=True, secret_env="LINEAR_SECRET")
            }
        )
        provider = LinearProvider(config, secret=secret)

        body = b'{"action":"create","type":"Issue"}'
        request = MagicMock()
        request.headers = {"x-linear-signature": "invalid_signature"}

        assert provider.verify_signature(request, body) is False

    def test_verify_signature_missing_header(self) -> None:
        """Should return False when signature header is missing."""
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config, secret="test_secret")

        body = b'{"action":"create"}'
        request = MagicMock()
        request.headers = {}

        assert provider.verify_signature(request, body) is False

    def test_verify_signature_no_secret_configured(self) -> None:
        """Should return True (skip verification) when no secret configured."""
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)  # No secret

        body = b'{"action":"create"}'
        request = MagicMock()
        request.headers = {}

        # When no secret, verification is skipped (returns True)
        assert provider.verify_signature(request, body) is True


class TestLinearProviderEventParsing:
    """Tests for parsing Linear webhook events."""

    def test_parse_event_issue_created(self) -> None:
        """Should parse issue created event correctly."""
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        payload = {
            "action": "create",
            "type": "Issue",
            "data": {
                "id": "issue-123",
                "identifier": "ENG-42",
                "title": "Add dark mode",
                "description": "Implement dark mode toggle",
                "state": {"id": "state-1", "name": "Todo"},
                "labels": [{"id": "label-1", "name": "adw:auto"}],
            },
            "createdAt": "2024-01-15T10:00:00.000Z",
        }
        body = bytes(__import__("json").dumps(payload), "utf-8")

        request = MagicMock()
        request.headers = {"x-linear-event": "Issue"}

        event = provider.parse_event(request, body)

        assert event.provider == "linear"
        assert event.event_type == "Issue.create"
        assert event.payload["data"]["identifier"] == "ENG-42"

    def test_parse_event_comment_created(self) -> None:
        """Should parse comment created event correctly."""
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        payload = {
            "action": "create",
            "type": "Comment",
            "data": {
                "id": "comment-123",
                "body": "Let's implement this. @adw run --phase build",
                "issue": {
                    "id": "issue-123",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                },
            },
            "createdAt": "2024-01-15T11:00:00.000Z",
        }
        body = bytes(__import__("json").dumps(payload), "utf-8")

        request = MagicMock()
        request.headers = {"x-linear-event": "Comment"}

        event = provider.parse_event(request, body)

        assert event.provider == "linear"
        assert event.event_type == "Comment.create"
        assert "@adw run" in event.payload["data"]["body"]

    def test_parse_event_invalid_json(self) -> None:
        """Should raise ValueError for invalid JSON."""
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        body = b"not valid json"
        request = MagicMock()
        request.headers = {}

        with pytest.raises(ValueError, match="Invalid JSON"):
            provider.parse_event(request, body)


class TestLinearProviderTriggerLogic:
    """Tests for run trigger logic."""

    def test_should_trigger_on_adw_auto_label(self) -> None:
        """Should trigger run when issue has adw:auto label."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-123",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                    "labels": [{"id": "label-1", "name": "adw:auto"}],
                },
            },
        )

        assert provider.should_trigger_run(event) is True

    def test_should_not_trigger_without_label(self) -> None:
        """Should not trigger run when issue lacks adw:auto label."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-123",
                    "labels": [{"id": "label-1", "name": "feature"}],
                },
            },
        )

        assert provider.should_trigger_run(event) is False

    def test_should_trigger_on_adw_command_in_comment(self) -> None:
        """Should trigger run when comment contains @adw run."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Comment",
                "data": {
                    "id": "comment-123",
                    "body": "Let's implement this. @adw run --phase build",
                    "issue": {
                        "id": "issue-123",
                        "identifier": "ENG-42",
                        "title": "Add dark mode",
                    },
                },
            },
        )

        assert provider.should_trigger_run(event) is True

    def test_should_not_trigger_on_comment_without_command(self) -> None:
        """Should not trigger run for comments without @adw run."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Comment",
                "data": {
                    "id": "comment-123",
                    "body": "This looks good!",
                    "issue": {"id": "issue-123"},
                },
            },
        )

        assert provider.should_trigger_run(event) is False


class TestLinearProviderRunParams:
    """Tests for run parameter extraction."""

    def test_extract_run_params_from_issue(self) -> None:
        """Should extract feature_request from issue title and description."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-uuid",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                    "description": "Implement dark mode toggle in settings",
                    "url": "https://linear.app/team/issue/ENG-42",
                    "labels": [{"name": "adw:auto"}],
                },
            },
        )

        params = provider.extract_run_params(event)

        assert "Add dark mode" in params.feature_request
        assert "dark mode toggle" in params.feature_request
        assert params.source_info["issue_url"] == "https://linear.app/team/issue/ENG-42"
        assert params.metadata["linear_issue_id"] == "issue-uuid"
        assert params.metadata["linear_identifier"] == "ENG-42"

    def test_extract_run_params_from_comment_with_phase(self) -> None:
        """Should parse phase from @adw run --phase flag."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Comment",
                "data": {
                    "id": "comment-123",
                    "body": "@adw run --phase build",
                    "issue": {
                        "id": "issue-uuid",
                        "identifier": "ENG-42",
                        "title": "Add dark mode",
                        "description": "Implement dark mode toggle",
                        "url": "https://linear.app/team/issue/ENG-42",
                    },
                },
            },
        )

        params = provider.extract_run_params(event)

        assert "Add dark mode" in params.feature_request
        assert params.phases == ["build"]
        assert params.metadata["triggered_by"] == "comment"

    def test_extract_run_params_handles_missing_description(self) -> None:
        """Should handle issues with null/missing description."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-uuid",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                    "description": None,
                    "labels": [{"name": "adw:auto"}],
                },
            },
        )

        params = provider.extract_run_params(event)

        assert params.feature_request == "Add dark mode"

    def test_extract_run_params_includes_labels_and_assignee(self) -> None:
        """Should include labels and assignee in metadata per acceptance criteria."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-uuid",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                    "labels": [
                        {"id": "l1", "name": "adw:auto"},
                        {"id": "l2", "name": "feature"},
                    ],
                    "assignee": {
                        "id": "user-123",
                        "name": "John Doe",
                        "email": "john@example.com",
                    },
                },
            },
        )

        params = provider.extract_run_params(event)

        # Verify labels are extracted
        assert params.metadata["labels"] == ["adw:auto", "feature"]

        # Verify assignee is extracted
        assert params.metadata["assignee"]["id"] == "user-123"
        assert params.metadata["assignee"]["name"] == "John Doe"
        assert params.metadata["assignee"]["email"] == "john@example.com"

    def test_extract_run_params_handles_missing_assignee(self) -> None:
        """Should handle issues without assignee."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Issue.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Issue",
                "data": {
                    "id": "issue-uuid",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                    "labels": [],
                },
            },
        )

        params = provider.extract_run_params(event)

        assert params.metadata["labels"] == []
        assert params.metadata["assignee"] is None

    def test_extract_run_params_with_multiple_phases(self) -> None:
        """Should parse multiple --phase flags from command."""
        from adw.models.webhook import WebhookEvent
        from adw.webhook.providers.linear import LinearProvider

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})
        provider = LinearProvider(config)

        event = WebhookEvent(
            event_type="Comment.create",
            provider="linear",
            payload={
                "action": "create",
                "type": "Comment",
                "data": {
                    "id": "comment-123",
                    "body": "@adw run --phase plan --phase build --phase test",
                    "issue": {
                        "id": "issue-uuid",
                        "identifier": "ENG-42",
                        "title": "Add dark mode",
                    },
                },
            },
        )

        params = provider.extract_run_params(event)

        assert params.phases == ["plan", "build", "test"]


class TestLinearProviderRegistration:
    """Tests for provider registration."""

    def test_linear_provider_registered_in_factories(self) -> None:
        """LinearProvider should be registered in provider factories."""
        # Import linear module to trigger registration
        import adw.webhook.providers.linear  # noqa: F401
        from adw.webhook.providers.loader import get_available_providers

        factories = get_available_providers()
        assert "linear" in factories

    def test_linear_provider_can_be_loaded_from_config(self) -> None:
        """Should be able to load LinearProvider via load_providers_from_config."""
        # Import linear module to trigger registration
        import adw.webhook.providers.linear  # noqa: F401
        from adw.webhook.providers.loader import load_providers_from_config

        config = WebhookConfig(providers={"linear": ProviderConfig(enabled=True)})

        registry = load_providers_from_config(config)

        assert "linear" in registry.list_providers()
        provider = registry.get("linear")
        assert provider is not None
        assert provider.name == "linear"
