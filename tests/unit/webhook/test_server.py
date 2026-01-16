# Test Reduction Notes:
# Following ADR-001, these tests focus on:
#   - Endpoint behavior (business logic)
#   - Configuration validation
#   - Error handling paths
# NOT testing:
#   - Default values (Pydantic handles this)
#   - Simple attribute assignment
#   - Import verification

"""Tests for webhook server functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from adw.models.webhook import ProviderConfig, RunParams, WebhookConfig, WebhookEvent
from adw.webhook.server import app, create_app

if TYPE_CHECKING:
    from fastapi import Request


class MockProvider:
    """Mock provider for testing route integration."""

    def __init__(
        self,
        name: str = "mock",
        verify_result: bool = True,
        should_trigger: bool = True,
    ) -> None:
        self._name = name
        self._verify_result = verify_result
        self._should_trigger = should_trigger

    @property
    def name(self) -> str:
        return self._name

    def verify_signature(self, request: Request, body: bytes) -> bool:
        return self._verify_result

    def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
        return WebhookEvent(
            event_type="test",
            provider=self._name,
            payload={"parsed": True},
            headers={},
        )

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        return self._should_trigger

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        return RunParams(feature_request="Test feature")


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200_with_healthy_status(self) -> None:
        """Health endpoint returns 200 with {"status": "healthy"}."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_endpoint_adds_request_id_header(self) -> None:
        """Health endpoint response includes x-request-id header."""
        client = TestClient(app)
        response = client.get("/health")
        assert "x-request-id" in response.headers
        # Verify it looks like a UUID
        request_id = response.headers["x-request-id"]
        assert len(request_id) == 36  # UUID format with dashes


class TestWebhookRoute:
    """Tests for the /webhook/{provider} endpoint."""

    def test_unknown_provider_returns_404(self) -> None:
        """Webhook route returns 404 for unconfigured provider."""
        client = TestClient(app)
        response = client.post("/webhook/unknown", json={})
        assert response.status_code == 404
        assert "unknown" in response.json()["detail"].lower()

    def test_disabled_provider_returns_404(self) -> None:
        """Webhook route returns 404 for disabled provider."""
        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=False)}
        )
        test_app = create_app(config=config)
        client = TestClient(test_app)
        response = client.post("/webhook/linear", json={})
        assert response.status_code == 404
        assert "linear" in response.json()["detail"].lower()

    def test_enabled_provider_returns_202(self) -> None:
        """Webhook route returns 202 for enabled provider."""
        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True)}
        )
        test_app = create_app(config=config)
        client = TestClient(test_app)
        response = client.post("/webhook/linear", json={"test": "data"})
        assert response.status_code == 202
        assert response.json()["status"] == "received"
        assert "request_id" in response.json()

    def test_webhook_response_includes_request_id(self) -> None:
        """Webhook response includes request_id in body and header."""
        config = WebhookConfig(
            providers={"github": ProviderConfig(enabled=True)}
        )
        test_app = create_app(config=config)
        client = TestClient(test_app)
        # Include required GitHub headers for the provider to parse correctly
        response = client.post(
            "/webhook/github",
            json={"action": "opened"},
            headers={
                "x-github-event": "issues",
                "x-github-delivery": "test-delivery-id",
            },
        )
        # Check body
        body_request_id = response.json()["request_id"]
        # Check header
        header_request_id = response.headers["x-request-id"]
        # Both should be valid UUIDs
        assert len(body_request_id) == 36
        assert len(header_request_id) == 36

    def test_unknown_provider_404_lists_available_providers(self) -> None:
        """404 response should list available providers when provider not found."""
        from adw.webhook.providers.registry import ProviderRegistry

        # Create registry with providers
        registry = ProviderRegistry()
        registry.register(MockProvider("linear"))
        registry.register(MockProvider("github"))

        config = WebhookConfig()
        test_app = create_app(config=config, registry=registry)
        client = TestClient(test_app)

        response = client.post("/webhook/unknown", json={})
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "unknown" in detail.lower()
        assert "linear" in detail or "github" in detail

    def test_provider_signature_verification_fails_returns_401(self) -> None:
        """Route returns 401 when provider signature verification fails."""
        from adw.webhook.providers.registry import ProviderRegistry

        # Provider that fails verification
        failing_provider = MockProvider("linear", verify_result=False)

        registry = ProviderRegistry()
        registry.register(failing_provider)

        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True)}
        )
        test_app = create_app(config=config, registry=registry)
        client = TestClient(test_app)

        response = client.post("/webhook/linear", json={"test": "data"})
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    def test_provider_parses_event_successfully(self) -> None:
        """Route uses provider to parse events when registered."""
        from adw.webhook.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        registry.register(MockProvider("linear"))

        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True)}
        )
        test_app = create_app(config=config, registry=registry)
        client = TestClient(test_app)

        response = client.post("/webhook/linear", json={"test": "data"})
        assert response.status_code == 202
        # Event was parsed by provider (we know this passed if 202)

    def test_provider_not_in_registry_uses_fallback(self) -> None:
        """When provider is enabled but not in registry, uses fallback behavior."""
        from adw.webhook.providers.registry import ProviderRegistry

        # Empty registry - no providers registered
        registry = ProviderRegistry()

        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True)}
        )
        test_app = create_app(config=config, registry=registry)
        client = TestClient(test_app)

        # Should still work (fallback to legacy behavior)
        response = client.post("/webhook/linear", json={"test": "data"})
        assert response.status_code == 202


class TestRequestLogging:
    """Tests for request logging middleware."""

    def test_logging_middleware_captures_webhook_metadata(self) -> None:
        """Middleware captures provider, event_type, payload_size."""
        captured_logs: list[dict] = []

        def capture_log(**kwargs: object) -> None:
            captured_logs.append(dict(kwargs))

        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True)}
        )
        test_app = create_app(config=config, log_func=capture_log)
        client = TestClient(test_app)

        # Send a webhook with event header
        response = client.post(
            "/webhook/linear",
            json={"action": "create"},
            headers={"x-linear-event": "Issue"},
        )
        assert response.status_code == 202

        # Verify log captured
        assert len(captured_logs) == 1
        log = captured_logs[0]
        assert log["provider"] == "linear"
        assert log["event_type"] == "Issue"
        assert log["payload_size"] > 0
        assert "request_id" in log
        assert "duration_ms" in log

    def test_logging_middleware_handles_non_webhook_requests(self) -> None:
        """Middleware logs non-webhook requests without webhook fields."""
        captured_logs: list[dict] = []

        def capture_log(**kwargs: object) -> None:
            captured_logs.append(dict(kwargs))

        test_app = create_app(log_func=capture_log)
        client = TestClient(test_app)

        client.get("/health")

        assert len(captured_logs) == 1
        log = captured_logs[0]
        assert log["path"] == "/health"
        assert log["method"] == "GET"
        assert log["status_code"] == 200
        # Webhook-specific fields should not be present
        assert log.get("provider") is None


class TestWebhookConfig:
    """Tests for WebhookConfig behavior."""

    def test_is_provider_enabled_returns_true_for_enabled(self) -> None:
        """is_provider_enabled returns True for enabled provider."""
        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=True)}
        )
        assert config.is_provider_enabled("linear") is True

    def test_is_provider_enabled_returns_false_for_disabled(self) -> None:
        """is_provider_enabled returns False for disabled provider."""
        config = WebhookConfig(
            providers={"linear": ProviderConfig(enabled=False)}
        )
        assert config.is_provider_enabled("linear") is False

    def test_is_provider_enabled_returns_false_for_unknown(self) -> None:
        """is_provider_enabled returns False for unconfigured provider."""
        config = WebhookConfig(providers={})
        assert config.is_provider_enabled("linear") is False

    def test_get_provider_returns_config_for_known_provider(self) -> None:
        """get_provider returns config for configured provider."""
        provider_config = ProviderConfig(enabled=True, secret_env="TEST_SECRET")
        config = WebhookConfig(providers={"linear": provider_config})
        result = config.get_provider("linear")
        assert result is not None
        assert result.enabled is True
        assert result.secret_env == "TEST_SECRET"

    def test_get_provider_returns_none_for_unknown(self) -> None:
        """get_provider returns None for unconfigured provider."""
        config = WebhookConfig(providers={})
        assert config.get_provider("unknown") is None


class TestProviderConfig:
    """Tests for ProviderConfig behavior."""

    def test_get_secret_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_secret returns environment variable value."""
        monkeypatch.setenv("TEST_WEBHOOK_SECRET", "my-secret-value")
        config = ProviderConfig(enabled=True, secret_env="TEST_WEBHOOK_SECRET")
        assert config.get_secret() == "my-secret-value"

    def test_get_secret_returns_none_when_env_not_set(self) -> None:
        """get_secret returns None when env var is not set."""
        config = ProviderConfig(enabled=True, secret_env="NONEXISTENT_VAR_12345")
        assert config.get_secret() is None

    def test_get_secret_returns_none_when_no_secret_env(self) -> None:
        """get_secret returns None when secret_env is not configured."""
        config = ProviderConfig(enabled=True)
        assert config.get_secret() is None


class TestWebhookConfigInYAML:
    """Tests for webhook configuration in project YAML."""

    def test_webhook_config_loads_from_project_yaml(self) -> None:
        """WebhookConfig loads correctly from ProjectConfig YAML."""
        from adw.models.config import ProjectConfig

        yaml_content = """
name: test-project
language: python
webhook:
  port: 9000
  host: "127.0.0.1"
  providers:
    linear:
      enabled: true
      secret_env: LINEAR_WEBHOOK_SECRET
    github:
      enabled: false
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.webhook.port == 9000
        assert config.webhook.host == "127.0.0.1"
        assert config.webhook.is_provider_enabled("linear") is True
        assert config.webhook.is_provider_enabled("github") is False
        assert config.webhook.providers["linear"].secret_env == "LINEAR_WEBHOOK_SECRET"

    def test_webhook_config_uses_defaults_when_not_specified(self) -> None:
        """WebhookConfig uses defaults when not in YAML."""
        from adw.models.config import ProjectConfig

        yaml_content = """
name: test-project
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.webhook.port == 8000
        assert config.webhook.host == "0.0.0.0"
        assert config.webhook.providers == {}
