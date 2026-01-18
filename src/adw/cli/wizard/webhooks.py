"""Webhook configuration step for the wizard.

This module handles the webhook configuration step where users can set up
webhook integrations for triggering ADW runs from external events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


# Available webhook providers
AVAILABLE_PROVIDERS: list[str] = ["linear", "github"]

# Default webhook configuration values
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_SECRET_ENVS: dict[str, str] = {
    "linear": "LINEAR_WEBHOOK_SECRET",
    "github": "GITHUB_WEBHOOK_SECRET",
}
DEFAULT_COMMAND_PREFIX = "/adw"
DEFAULT_TRIGGER_LABEL = "adw"

# Event types for configuration
EVENT_TYPES: list[str] = ["issue_created", "issue_updated", "comment_created"]


class WebhooksStepHandler:
    """Handler for the webhook configuration wizard step.

    This step:
    - Prompts if user wants to set up webhook server
    - If yes, configures server port and host
    - Allows multi-select of providers to configure (Linear, GitHub)
    - For each selected provider, configures:
      - Secret environment variable name
      - Command prefix
      - Trigger label
      - Event mappings (optional)
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the webhook configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - enabled: Whether webhooks are enabled
            - port: Server port
            - host: Server host
            - providers: Dict of provider configurations
        """
        return run_webhooks_step(state, console)


def run_webhooks_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the webhook configuration step.

    This is the main entry point for the webhooks step, implementing
    the full interactive flow for webhook configuration.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing webhook settings.
    """
    # Step 1: Ask if user wants to set up webhooks
    enable_webhooks = Confirm.ask(
        "Set up webhook server?",
        default=False,
        console=console,
    )

    if not enable_webhooks:
        return {
            "enabled": False,
            "port": DEFAULT_PORT,
            "host": DEFAULT_HOST,
            "providers": {},
            "mappings": {},
        }

    # Step 2: Configure server settings
    port, host = _prompt_server_config(console)

    # Step 3: Select providers to configure
    selected_providers = _prompt_provider_selection(console)

    if not selected_providers:
        # No providers selected, effectively disabled
        return {
            "enabled": False,
            "port": port,
            "host": host,
            "providers": {},
            "mappings": {},
        }

    # Step 4: Configure each selected provider
    provider_configs: dict[str, dict[str, Any]] = {}
    mappings: dict[str, dict[str, Any]] = {}

    for provider in selected_providers:
        config, provider_mappings = _configure_provider(provider, console)
        provider_configs[provider] = config
        if provider_mappings:
            mappings[provider] = provider_mappings

    # Derive global enabled from whether any provider is actually enabled
    any_provider_enabled = any(
        cfg.get("enabled", False) for cfg in provider_configs.values()
    )

    if not any_provider_enabled:
        # All providers were disabled during configuration
        return {
            "enabled": False,
            "port": port,
            "host": host,
            "providers": {},
            "mappings": {},
        }

    return {
        "enabled": True,
        "port": port,
        "host": host,
        "providers": provider_configs,
        "mappings": mappings,
    }


def _prompt_server_config(console: Console) -> tuple[int, str]:
    """Prompt for webhook server configuration.

    Args:
        console: Console for output.

    Returns:
        Tuple of (port, host).
    """
    console.print()
    console.print("[dim]Server configuration:[/]")

    port = IntPrompt.ask(
        "Webhook server port",
        default=DEFAULT_PORT,
        console=console,
    )

    # Validate port range
    if port < 1 or port > 65535:
        console.print("[yellow]Invalid port. Using default 8000.[/]")
        port = DEFAULT_PORT

    host = Prompt.ask(
        "Webhook server host",
        default=DEFAULT_HOST,
        console=console,
    )

    return port, host


def _prompt_provider_selection(console: Console) -> list[str]:
    """Prompt user to select which providers to configure.

    Args:
        console: Console for output.

    Returns:
        List of selected provider names.
    """
    console.print()
    console.print("[dim]Select webhook providers to configure:[/]")

    selected: list[str] = []

    for provider in AVAILABLE_PROVIDERS:
        display_name = provider.title()
        if Confirm.ask(
            f"Configure [cyan]{display_name}[/] webhooks?",
            default=False,
            console=console,
        ):
            selected.append(provider)

    return selected


def _configure_provider(
    provider: str, console: Console
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Configure a single webhook provider.

    Args:
        provider: The provider name to configure.
        console: Console for output.

    Returns:
        Tuple of (provider_config, event_mappings) where:
        - provider_config matches ProviderConfig model fields
        - event_mappings matches ProviderEventMapping structure (or empty)
    """
    display_name = provider.title()
    console.print()
    console.print(Rule(f"[bold blue]{display_name}[/] Provider", style="blue"))

    # Basic configuration
    enabled = Confirm.ask(
        f"Enable {display_name} webhooks?",
        default=True,
        console=console,
    )

    if not enabled:
        return {"enabled": False}, {}

    default_secret_env = DEFAULT_SECRET_ENVS.get(
        provider, f"{provider.upper()}_WEBHOOK_SECRET"
    )
    secret_env = Prompt.ask(
        "Secret env variable",
        default=default_secret_env,
        console=console,
    )

    command_prefix = Prompt.ask(
        "Command prefix",
        default=DEFAULT_COMMAND_PREFIX,
        console=console,
    )

    trigger_label = Prompt.ask(
        "Trigger label",
        default=DEFAULT_TRIGGER_LABEL,
        console=console,
    )

    # Event mappings configuration (stored separately per WebhookMappings model)
    configure_events = Confirm.ask(
        "Configure event mappings?",
        default=True,
        console=console,
    )

    event_mappings: dict[str, dict[str, Any]] = {}
    if configure_events:
        event_mappings = _configure_event_mappings(console)

    # Return provider config (matching ProviderConfig model) and mappings separately
    provider_config = {
        "enabled": enabled,
        "secret_env": secret_env,
        "command_prefix": command_prefix,
        "trigger_label": trigger_label,
    }

    return provider_config, event_mappings


def _configure_event_mappings(console: Console) -> dict[str, dict[str, Any]]:
    """Configure event mappings for a provider.

    Args:
        console: Console for output.

    Returns:
        Dictionary of event type to event configuration.
    """
    console.print()
    console.print("[dim]Event mapping configuration:[/]")

    mappings: dict[str, dict[str, Any]] = {}

    for event_type in EVENT_TYPES:
        event_display = event_type.replace("_", " ").title()
        config = _configure_event(event_type, event_display, console)
        mappings[event_type] = config

    return mappings


def _configure_event(
    event_type: str,
    event_display: str,
    console: Console,
) -> dict[str, Any]:
    """Configure a single event type.

    Args:
        event_type: The event type identifier.
        event_display: Display name for the event.
        console: Console for output.

    Returns:
        Event configuration dict.
    """
    # Defaults: issue_created and comment_created enabled by default
    default_enabled = event_type in ("issue_created", "comment_created")

    trigger = Confirm.ask(
        f"On {event_display.lower()} - trigger run?",
        default=default_enabled,
        console=console,
    )

    if not trigger:
        return {"trigger": False}

    config: dict[str, Any] = {"trigger": True}

    # Require label option
    require_label = Prompt.ask(
        "  Require label? (empty for none)",
        default="",
        console=console,
    ).strip()

    if require_label:
        config["require_label"] = require_label

    # Comment-specific options
    if event_type == "comment_created":
        require_mention = Prompt.ask(
            "  Require mention",
            default="@adw",
            console=console,
        )
        config["require_mention"] = require_mention

        parse_command = Confirm.ask(
            "  Parse command from comment?",
            default=True,
            console=console,
        )
        config["parse_command"] = parse_command

    return config
