"""Tests for WebhookProvider Protocol and BaseWebhookProvider.

Following ADR-001: Tests focus on protocol compliance and validation,
not trivial attribute access or import smoke tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from fastapi import Request


class TestWebhookProviderProtocol:
    """Tests for WebhookProvider protocol compliance."""

    def test_mock_provider_implements_protocol(self) -> None:
        """A class with correct methods should satisfy the protocol."""
        from adw.models.webhook import RunParams, WebhookEvent
        from adw.webhook.providers.base import WebhookProvider

        class MockProvider:
            """Mock provider implementing the protocol."""

            @property
            def name(self) -> str:
                return "mock"

            def verify_signature(self, request: Request, body: bytes) -> bool:
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


class TestBaseWebhookProvider:
    """Tests for BaseWebhookProvider helper class."""

    def test_get_header_returns_value(self) -> None:
        """get_header should return header value when found."""
        from adw.webhook.providers.base import BaseWebhookProvider

        request = MagicMock()
        # Simulate FastAPI Headers behavior with dict
        request.headers = {"x-custom-header": "test-value"}

        result = BaseWebhookProvider.get_header(request, "x-custom-header")
        assert result == "test-value"

    def test_get_header_returns_default_when_missing(self) -> None:
        """get_header should return default when header not found."""
        from adw.webhook.providers.base import BaseWebhookProvider

        request = MagicMock()
        request.headers = {}

        result = BaseWebhookProvider.get_header(request, "missing", default="fallback")
        assert result == "fallback"

    def test_parse_json_body_returns_dict(self) -> None:
        """parse_json_body should parse JSON bytes to dict."""
        from adw.webhook.providers.base import BaseWebhookProvider

        body = b'{"key": "value", "number": 42}'
        result = BaseWebhookProvider.parse_json_body(body)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_body_raises_on_invalid_json(self) -> None:
        """parse_json_body should raise ValueError on invalid JSON."""
        from adw.webhook.providers.base import BaseWebhookProvider

        body = b"not valid json"
        with pytest.raises(ValueError, match="Invalid JSON"):
            BaseWebhookProvider.parse_json_body(body)

    def test_parse_json_body_raises_on_non_object(self) -> None:
        """parse_json_body should raise ValueError for arrays or primitives."""
        from adw.webhook.providers.base import BaseWebhookProvider

        # JSON array should be rejected
        body = b"[1, 2, 3]"
        with pytest.raises(ValueError, match="must be an object"):
            BaseWebhookProvider.parse_json_body(body)
