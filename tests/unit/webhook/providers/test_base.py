"""Tests for WebhookProvider Protocol.

Following ADR-001: Tests focus on protocol compliance and validation,
not trivial attribute access or import smoke tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi import Request


class TestWebhookProviderProtocol:
    """Tests for WebhookProvider protocol compliance."""

    def test_mock_provider_implements_protocol(self) -> None:
        """A class with correct methods should satisfy the protocol."""
        from adw.webhook.providers.base import WebhookProvider
        from adw.models.webhook import RunParams, WebhookEvent

        class MockProvider:
            """Mock provider implementing the protocol."""

            @property
            def name(self) -> str:
                return "mock"

            def verify_signature(self, request: Request) -> bool:
                return True

            def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
                return WebhookEvent(
                    event_type="test",
                    provider="mock",
                    payload={},
                    headers={},
                )

            def should_trigger_run(self, event: WebhookEvent) -> bool:
                return True

            def extract_run_params(self, event: WebhookEvent) -> RunParams:
                return RunParams(feature_request="test")

        provider = MockProvider()
        # runtime_checkable allows isinstance checks
        assert isinstance(provider, WebhookProvider)

    def test_incomplete_provider_fails_protocol_check(self) -> None:
        """A class missing required methods should NOT satisfy the protocol."""
        from adw.webhook.providers.base import WebhookProvider

        class IncompleteProvider:
            """Provider missing required methods."""

            @property
            def name(self) -> str:
                return "incomplete"

            # Missing: verify_signature, parse_event, should_trigger_run, extract_run_params

        provider = IncompleteProvider()
        # Should NOT be an instance due to missing methods
        assert not isinstance(provider, WebhookProvider)

    def test_protocol_is_runtime_checkable(self) -> None:
        """WebhookProvider should be decorated with @runtime_checkable."""
        from adw.webhook.providers.base import WebhookProvider

        # This will raise TypeError if not runtime_checkable
        # when used with isinstance()
        class TestClass:
            pass

        # Should not raise TypeError - protocol is runtime_checkable
        result = isinstance(TestClass(), WebhookProvider)
        assert result is False  # Not a provider, but check should work
