"""Ship phase configuration step for the wizard.

This module handles the ship phase configuration step where users can set up
deployment commands, post-publish hooks, and PR merge settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


# Merge strategy options
MERGE_STRATEGIES: list[str] = ["squash", "merge", "rebase"]


class ShipStepHandler:
    """Handler for the ship phase configuration wizard step.

    This step:
    - Prompts if user wants to configure ship phase settings
    - If yes, collects deployment commands (version_bump, publish)
    - Collects post-publish hooks
    - Configures PR merge settings (auto-merge, strategy, delete branch)
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
            - post_publish: List of post-publish hooks
            - pr: Dict of PR merge settings
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

    # Default PR settings (used both when skipping and as base for config)
    default_pr: dict[str, Any] = {
        "merge_on_success": False,
        "delete_branch_on_merge": True,
        "merge_method": "squash",
    }

    if not configure:
        # Return defaults when user skips configuration
        return {
            "enabled": True,  # Ship phase is enabled by default
            "commands": {},
            "post_publish": [],
            "pr": default_pr,
        }

    # Step 2: Collect deployment commands
    console.print()
    console.print(Rule("[bold cyan]Deployment Commands[/]", style="cyan"))
    commands = _prompt_deployment_commands(console)

    # Step 3: Collect post-publish hooks
    console.print()
    console.print(Rule("[bold cyan]Post-Publish Hooks[/]", style="cyan"))
    post_publish = _prompt_post_publish_hooks(console)

    # Step 4: Configure PR merge settings
    console.print()
    console.print(Rule("[bold cyan]PR Merge Settings[/]", style="cyan"))
    pr_config = _prompt_pr_settings(console)

    return {
        "enabled": True,
        "commands": commands,
        "post_publish": post_publish,
        "pr": pr_config,
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


def _prompt_post_publish_hooks(console: Console) -> list[str]:
    """Prompt for post-publish hooks.

    Allows user to add multiple hooks in a loop until they enter an empty line.

    Args:
        console: Console for output.

    Returns:
        List of hook commands.
    """
    add_hooks = Confirm.ask(
        "Add post-publish hooks?",
        default=False,
        console=console,
    )

    if not add_hooks:
        return []

    hooks: list[str] = []
    console.print("[dim]Enter hook commands (empty to finish):[/]")

    while True:
        hook = Prompt.ask(
            "Hook command",
            default="",
            console=console,
        ).strip()

        if not hook:
            break

        hooks.append(hook)

    return hooks


def _prompt_pr_settings(console: Console) -> dict[str, Any]:
    """Prompt for PR merge settings.

    Only prompts for merge strategy and delete branch if auto-merge is enabled.
    This prevents asking redundant questions when auto-merge is disabled.

    Args:
        console: Console for output.

    Returns:
        Dictionary of PR settings.
    """
    merge_on_success = Confirm.ask(
        "Auto-merge after successful ship?",
        default=False,
        console=console,
    )

    # Defaults
    merge_method = "squash"
    delete_branch = True

    # Only ask follow-up questions if auto-merge is enabled
    if merge_on_success:
        merge_method = Prompt.ask(
            "Merge strategy",
            choices=MERGE_STRATEGIES,
            default="squash",
            console=console,
        )

        delete_branch = Confirm.ask(
            "Delete branch after merge?",
            default=True,
            console=console,
        )

    return {
        "merge_on_success": merge_on_success,
        "delete_branch_on_merge": delete_branch,
        "merge_method": merge_method,
    }
