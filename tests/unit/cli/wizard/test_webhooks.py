"""Tests for wizard webhook configuration step.

Tests the webhook server configuration, provider selection, provider configuration,
and event mapping configuration for the webhook setup wizard step.
"""

from __future__ import annotations

from unittest.mock import patch

from rich.console import Console

from adw.cli.wizard.webhooks import (
    AVAILABLE_PROVIDERS,
    DEFAULT_COMMAND_PREFIX,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SECRET_ENVS,
    DEFAULT_TRIGGER_LABEL,
    EVENT_TYPES,
    WebhooksStepHandler,
    _configure_event,
    _configure_event_mappings,
    _configure_provider,
    _prompt_provider_selection,
    _prompt_server_config,
    run_webhooks_step,
)
from adw.models.wizard import WizardState


class TestConstants:
    """Tests for module constants."""

    def test_available_providers(self) -> None:
        """Test available providers list."""
        assert AVAILABLE_PROVIDERS == ["linear", "github"]

    def test_default_port(self) -> None:
        """Test default port value."""
        assert DEFAULT_PORT == 8000

    def test_default_host(self) -> None:
        """Test default host value."""
        assert DEFAULT_HOST == "0.0.0.0"

    def test_default_secret_envs(self) -> None:
        """Test default secret environment variable names."""
        assert DEFAULT_SECRET_ENVS["linear"] == "LINEAR_WEBHOOK_SECRET"
        assert DEFAULT_SECRET_ENVS["github"] == "GITHUB_WEBHOOK_SECRET"

    def test_default_command_prefix(self) -> None:
        """Test default command prefix."""
        assert DEFAULT_COMMAND_PREFIX == "/adw"

    def test_default_trigger_label(self) -> None:
        """Test default trigger label."""
        assert DEFAULT_TRIGGER_LABEL == "adw"

    def test_event_types(self) -> None:
        """Test event types list."""
        assert EVENT_TYPES == ["issue_created", "issue_updated", "comment_created"]


class TestWebhooksDisabled:
    """Tests for when user declines webhook setup."""

    def test_webhook_disabled_returns_default_config(self) -> None:
        """Test that declining webhooks returns disabled config with defaults."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=False):
            result = run_webhooks_step(state, console)

        assert result["enabled"] is False
        assert result["port"] == DEFAULT_PORT
        assert result["host"] == DEFAULT_HOST
        assert result["providers"] == {}
        assert result["mappings"] == {}


class TestServerConfiguration:
    """Tests for server configuration prompts."""

    def test_server_config_with_defaults(self) -> None:
        """Test server config using defaults."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=8000),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="0.0.0.0"),
        ):
            port, host = _prompt_server_config(console)

        assert port == 8000
        assert host == "0.0.0.0"

    def test_server_config_custom_values(self) -> None:
        """Test server config with custom values."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=9000),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="127.0.0.1"),
        ):
            port, host = _prompt_server_config(console)

        assert port == 9000
        assert host == "127.0.0.1"

    def test_server_config_invalid_port_uses_default(self) -> None:
        """Test that invalid port falls back to default."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=99999),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="0.0.0.0"),
        ):
            port, host = _prompt_server_config(console)

        assert port == 8000  # Falls back to default

    def test_server_config_zero_port_uses_default(self) -> None:
        """Test that zero port falls back to default."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=0),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="0.0.0.0"),
        ):
            port, host = _prompt_server_config(console)

        assert port == 8000  # Falls back to default


class TestProviderSelection:
    """Tests for provider selection flow."""

    def test_select_no_providers(self) -> None:
        """Test selecting no providers returns empty list."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [False, False]
            selected = _prompt_provider_selection(console)

        assert selected == []

    def test_select_all_providers(self) -> None:
        """Test selecting all providers."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [True, True]
            selected = _prompt_provider_selection(console)

        assert selected == AVAILABLE_PROVIDERS

    def test_select_linear_only(self) -> None:
        """Test selecting only Linear provider."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [True, False]
            selected = _prompt_provider_selection(console)

        assert selected == ["linear"]

    def test_select_github_only(self) -> None:
        """Test selecting only GitHub provider."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [False, True]
            selected = _prompt_provider_selection(console)

        assert selected == ["github"]

    def test_no_providers_selected_disables_webhooks(self) -> None:
        """Test that selecting no providers after enabling returns disabled config."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=8000),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="0.0.0.0"),
        ):
            # Enable webhooks, configure server, then no providers
            mock_confirm.side_effect = [True, False, False]
            result = run_webhooks_step(state, console)

        assert result["enabled"] is False
        assert result["providers"] == {}
        assert result["mappings"] == {}


class TestProviderConfiguration:
    """Tests for individual provider configuration."""

    def test_configure_provider_disabled(self) -> None:
        """Test provider configuration when disabled."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=False):
            config, mappings = _configure_provider("linear", console)

        assert config == {"enabled": False}
        assert mappings == {}

    def test_configure_provider_defaults(self) -> None:
        """Test provider configuration with defaults (no event mappings)."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            # enabled=True, configure events=False
            mock_confirm.side_effect = [True, False]
            mock_prompt.side_effect = [
                "LINEAR_WEBHOOK_SECRET",
                "/adw",
                "adw",
            ]

            config, mappings = _configure_provider("linear", console)

        # Provider config matches ProviderConfig model (no event_mappings field)
        assert config["enabled"] is True
        assert config["secret_env"] == "LINEAR_WEBHOOK_SECRET"
        assert config["command_prefix"] == "/adw"
        assert config["trigger_label"] == "adw"
        assert "event_mappings" not in config  # Mappings returned separately
        assert mappings == {}

    def test_configure_provider_custom_values(self) -> None:
        """Test provider configuration with custom values."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False]
            mock_prompt.side_effect = [
                "MY_CUSTOM_SECRET",
                "!adw",
                "custom-label",
            ]

            config, mappings = _configure_provider("linear", console)

        assert config["secret_env"] == "MY_CUSTOM_SECRET"
        assert config["command_prefix"] == "!adw"
        assert config["trigger_label"] == "custom-label"
        assert mappings == {}

    def test_configure_github_uses_correct_default_secret(self) -> None:
        """Test that GitHub provider uses correct default secret env."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False]
            mock_prompt.side_effect = [
                "GITHUB_WEBHOOK_SECRET",  # This is the default for GitHub
                "/adw",
                "adw",
            ]

            config, mappings = _configure_provider("github", console)

        assert config["secret_env"] == "GITHUB_WEBHOOK_SECRET"
        assert mappings == {}


class TestEventMappingConfiguration:
    """Tests for event mapping configuration."""

    def test_configure_event_mappings_all_defaults(self) -> None:
        """Test event mappings with default enables/disables."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            # issue_created: enabled, issue_updated: disabled, comment_created: enabled
            mock_confirm.side_effect = [
                True,  # issue_created trigger
                True,  # issue_updated trigger (overriding default False)
                True,  # comment_created trigger
                True,  # parse_command
            ]
            mock_prompt.side_effect = [
                "",  # issue_created label
                "",  # issue_updated label
                "",  # comment_created label
                "@adw",  # require_mention
            ]

            mappings = _configure_event_mappings(console)

        assert "issue_created" in mappings
        assert "issue_updated" in mappings
        assert "comment_created" in mappings

    def test_configure_event_disabled(self) -> None:
        """Test event configuration when disabled."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=False):
            config = _configure_event("issue_updated", "Issue Updated", console)

        assert config == {"enabled": False}

    def test_configure_event_with_label(self) -> None:
        """Test event configuration with required label."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="adw:auto"),
        ):
            config = _configure_event("issue_created", "Issue Created", console)

        assert config["enabled"] is True
        assert config["require_label"] == "adw:auto"

    def test_configure_event_no_label(self) -> None:
        """Test event configuration without required label."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value=""),
        ):
            config = _configure_event("issue_created", "Issue Created", console)

        assert config["enabled"] is True
        assert "require_label" not in config

    def test_configure_comment_event_with_mention(self) -> None:
        """Test comment event configuration with mention and parse command."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, True]  # trigger, parse_command
            mock_prompt.side_effect = ["", "@bot"]  # label, mention

            config = _configure_event("comment_created", "Comment Created", console)

        assert config["enabled"] is True
        assert config["require_mention"] == "@bot"
        assert config["parse_command"] is True

    def test_configure_comment_event_no_parse_command(self) -> None:
        """Test comment event configuration without parse command."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False]  # trigger, parse_command=False
            mock_prompt.side_effect = ["", "@adw"]  # label, mention

            config = _configure_event("comment_created", "Comment Created", console)

        assert config["enabled"] is True
        assert config["parse_command"] is False


class TestWebhooksStepHandler:
    """Tests for WebhooksStepHandler class."""

    def test_handler_delegates_to_run_webhooks_step(self) -> None:
        """Test that handler properly delegates to run_webhooks_step."""
        handler = WebhooksStepHandler()
        state = WizardState()
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=False):
            result = handler.execute(state, console)

        assert result["enabled"] is False
        assert result["providers"] == {}
        assert result["mappings"] == {}


class TestFullFlow:
    """Tests for full webhook configuration flow."""

    def test_full_flow_with_linear_provider(self) -> None:
        """Test full flow configuring Linear provider with events."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=8080),
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # enable webhooks
                True,  # configure linear
                False,  # skip github
                True,  # enable linear
                True,  # configure events
                True,  # issue_created trigger
                False,  # issue_updated trigger
                True,  # comment_created trigger
                True,  # parse_command
            ]
            mock_prompt.side_effect = [
                "localhost",  # host
                "LINEAR_WEBHOOK_SECRET",  # secret
                "/adw",  # command prefix
                "adw",  # trigger label
                "",  # issue_created label
                "",  # comment_created label
                "@adw",  # comment mention
            ]

            result = run_webhooks_step(state, console)

        assert result["enabled"] is True
        assert result["port"] == 8080
        assert result["host"] == "localhost"
        # Provider config matches ProviderConfig model
        assert "linear" in result["providers"]
        linear_config = result["providers"]["linear"]
        assert linear_config["enabled"] is True
        assert linear_config["secret_env"] == "LINEAR_WEBHOOK_SECRET"
        assert "event_mappings" not in linear_config  # Mappings at top level
        # Mappings stored at top level, matching WebhookMappings structure
        assert "linear" in result["mappings"]
        assert "issue_created" in result["mappings"]["linear"]
        assert "comment_created" in result["mappings"]["linear"]

    def test_full_flow_with_both_providers(self) -> None:
        """Test full flow configuring both Linear and GitHub providers."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=8000),
            patch("adw.cli.wizard.webhooks.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # enable webhooks
                True,  # configure linear
                True,  # configure github
                True,  # enable linear
                False,  # skip linear events config
                True,  # enable github
                False,  # skip github events config
            ]
            mock_prompt.side_effect = [
                "0.0.0.0",  # host
                "LINEAR_WEBHOOK_SECRET",  # linear secret
                "/adw",  # linear command prefix
                "adw",  # linear trigger label
                "GITHUB_WEBHOOK_SECRET",  # github secret
                "/adw",  # github command prefix
                "adw",  # github trigger label
            ]

            result = run_webhooks_step(state, console)

        assert result["enabled"] is True
        assert "linear" in result["providers"]
        assert "github" in result["providers"]
        assert result["providers"]["linear"]["enabled"] is True
        assert result["providers"]["github"]["enabled"] is True
        # Mappings at top level (empty because events config skipped)
        assert result["mappings"] == {}

    def test_all_providers_disabled_returns_disabled_config(self) -> None:
        """Test that disabling all providers results in enabled=False."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.webhooks.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.webhooks.IntPrompt.ask", return_value=8000),
            patch("adw.cli.wizard.webhooks.Prompt.ask", return_value="0.0.0.0"),
        ):
            mock_confirm.side_effect = [
                True,  # enable webhooks
                True,  # configure linear
                False,  # skip github
                False,  # disable linear (!)
            ]

            result = run_webhooks_step(state, console)

        # Global enabled should be False when all providers are disabled
        assert result["enabled"] is False
        assert result["providers"] == {}
        assert result["mappings"] == {}


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_config_can_be_stored_in_state(self) -> None:
        """Test that webhook config can be stored via flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.webhooks.Confirm.ask", return_value=False):
            config = run_webhooks_step(state, console)

        # Simulate what flow controller does
        state.update_config("webhooks", config)
        state.mark_completed("webhooks")

        # Verify storage
        stored = state.get_step_config("webhooks")
        assert stored["enabled"] is False
        assert "webhooks" in state.completed_steps


class TestPackageExports:
    """Tests for package exports."""

    def test_webhooks_step_handler_exported(self) -> None:
        """Test that WebhooksStepHandler is exported from package."""
        from adw.cli.wizard import WebhooksStepHandler

        assert WebhooksStepHandler is not None

    def test_run_webhooks_step_exported(self) -> None:
        """Test that run_webhooks_step is exported from package."""
        from adw.cli.wizard import run_webhooks_step

        assert run_webhooks_step is not None
