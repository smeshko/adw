"""Tests for ProviderRegistry.

Following ADR-001: Tests focus on business logic and validation,
not trivial attribute access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request

from adw.models.webhook import RunParams, WebhookEvent
from adw.webhook.providers.base import WebhookProvider


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, name: str = "mock") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def verify_signature(self, request: Request, body: bytes) -> bool:
        return True

    def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
        return WebhookEvent(
            event_type="test", provider=self._name, payload={}, headers={}
        )

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        return True

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        return RunParams(feature_request="test")


class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    def test_register_and_get_provider(self) -> None:
        """Registered provider should be retrievable by name."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        provider = MockProvider("linear")
        registry.register(provider)

        result = registry.get("linear")
        assert result is provider

    def test_get_returns_none_for_unknown_provider(self) -> None:
        """Unknown provider should return None, not raise."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        result = registry.get("unknown")
        assert result is None

    def test_list_providers_returns_registered_names(self) -> None:
        """list_providers should return all registered provider names."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        registry.register(MockProvider("linear"))
        registry.register(MockProvider("github"))

        providers = registry.list_providers()
        assert set(providers) == {"linear", "github"}

    def test_list_providers_empty_when_no_registrations(self) -> None:
        """list_providers should return empty list when nothing registered."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        assert registry.list_providers() == []

    def test_register_overwrites_existing_provider(self) -> None:
        """Registering with same name should overwrite previous provider."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        provider1 = MockProvider("linear")
        provider2 = MockProvider("linear")

        registry.register(provider1)
        registry.register(provider2)

        result = registry.get("linear")
        assert result is provider2

    def test_registered_provider_satisfies_protocol(self) -> None:
        """Registered provider should satisfy WebhookProvider protocol."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        provider = MockProvider("test")
        registry.register(provider)

        result = registry.get("test")
        assert isinstance(result, WebhookProvider)
