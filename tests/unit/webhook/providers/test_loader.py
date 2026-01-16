"""Tests for provider loading functionality.

Following ADR-001: Tests focus on business logic and error handling,
not trivial attribute access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi import Request

from adw.models.webhook import ProviderConfig, RunParams, WebhookConfig, WebhookEvent


class MockProvider:
    """Mock provider for testing loader."""

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


class TestLoadProvidersFromConfig:
    """Tests for load_providers_from_config function."""

    def test_load_returns_empty_registry_when_no_providers_enabled(self) -> None:
        """Returns empty registry when no providers are enabled."""
        from adw.webhook.providers.loader import load_providers_from_config
        from adw.webhook.providers.registry import ProviderRegistry

        config = WebhookConfig(providers={})
        registry = load_providers_from_config(config)

        assert isinstance(registry, ProviderRegistry)
        assert registry.list_providers() == []

    def test_load_skips_disabled_providers(self) -> None:
        """Does not register disabled providers."""
        from adw.webhook.providers.loader import load_providers_from_config

        config = WebhookConfig(
            providers={
                "linear": ProviderConfig(enabled=False),
                "github": ProviderConfig(enabled=False),
            }
        )
        registry = load_providers_from_config(config)

        assert registry.list_providers() == []

    def test_load_logs_unavailable_providers(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logs info when enabled provider implementation not available."""
        from adw.webhook.providers.loader import load_providers_from_config

        config = WebhookConfig(
            providers={
                "unknown_provider": ProviderConfig(enabled=True),
            }
        )

        with caplog.at_level("INFO"):
            registry = load_providers_from_config(config)

        # Provider should not be registered (no implementation)
        assert registry.list_providers() == []
        # Should have logged something about unavailable provider
        assert (
            "unknown_provider" in caplog.text or "not available" in caplog.text.lower()
        )

    def test_load_handles_missing_config_gracefully(self) -> None:
        """Returns empty registry when config is None."""
        from adw.webhook.providers.loader import load_providers_from_config

        registry = load_providers_from_config(None)  # type: ignore[arg-type]
        assert registry.list_providers() == []


class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    def test_returns_dict_of_provider_names_to_classes(self) -> None:
        """Returns mapping of provider names to their factory functions."""
        from adw.webhook.providers.loader import get_available_providers

        available = get_available_providers()
        assert isinstance(available, dict)
        # Currently no providers implemented, so empty or minimal
        # Future stories will add Linear, GitHub, etc.
