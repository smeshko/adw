"""Ship phase configuration step for the wizard.

This module handles the ship phase configuration step where users can set up
deployment commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class ShipStepHandler:
    """Handler for the ship phase configuration wizard step.

    This step:
    - Prompts if user wants to configure ship phase settings
    - If yes, collects deployment commands (version_bump, publish)
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the ship phase configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - enabled: Whether ship phase is enabled
            - commands: Dict of deployment commands
        """
        return run_ship_step(state, console)


def run_ship_step(
    state: WizardState,  # noqa: ARG001 - reserved for future use
    console: Console,
) -> dict[str, Any]:
    """Execute the ship phase configuration step.

    This is the main entry point for the ship step, implementing
    the full interactive flow for ship phase configuration.

    Note: This step has been removed from the wizard flow. Ship phase
    configuration is now handled as part of the phases step. This function
    is retained for backwards compatibility and direct usage.

    Args:
        state: Current wizard state (reserved for future use).
        console: Console for output.

    Returns:
        Configuration dict containing ship phase settings.
    """
    # Step 1: Ask if user wants to configure ship phase
    configure = Confirm.ask(
        "Configure ship phase settings?",
        default=False,
        console=console,
    )

    if not configure:
        # Return defaults when user skips configuration
        return {
            "enabled": True,  # Ship phase is enabled by default
            "commands": {},
        }

    # Step 2: Collect deployment commands
    console.print()
    console.print(Rule("[bold cyan]Deployment Commands[/]", style="cyan"))
    commands = _prompt_deployment_commands(console)

    return {
        "enabled": True,
        "commands": commands,
    }


def _prompt_deployment_commands(console: Console) -> dict[str, str]:
    """Prompt for deployment commands.

    Args:
        console: Console for output.

    Returns:
        Dictionary of command name to command string.
        Only includes commands that were provided (non-empty).
    """
    console.print("[dim]Enter commands to run during ship phase (empty to skip):[/]")

    commands: dict[str, str] = {}

    # Version bump command
    version_bump = Prompt.ask(
        "Version bump command",
        default="",
        console=console,
    ).strip()
    if version_bump:
        commands["version_bump"] = version_bump

    # Note: build_command is configured at the project level in project.yaml

    # Publish command
    publish = Prompt.ask(
        "Publish command",
        default="",
        console=console,
    ).strip()
    if publish:
        commands["publish"] = publish

    return commands


