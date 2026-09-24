"""Global registry step for the wizard.

This module handles the global registry step of the wizard where users
can choose to register their project in the ADW web dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt


def run_global_registry_step(console: Console) -> dict[str, Any]:
    """Execute the global registry step.

    This is the main entry point for the global registry step, implementing
    the full interactive flow for dashboard registration.

    Args:
        console: Console for output.

    Returns:
        Configuration dict containing global_registry_enabled and
        global_registry_name values.
    """
    console.print()
    console.print("[dim]The ADW web dashboard tracks runs across all your projects.[/]")
    console.print(
        "[dim]Registering allows this project to appear in cross-project views.[/]"
    )
    console.print()

    # Step 1: Ask if user wants to register
    register = Confirm.ask(
        "Register this project in the ADW web dashboard?",
        default=True,
        console=console,
    )

    if not register:
        return {
            "global_registry_enabled": False,
            "global_registry_name": None,
        }

    # Step 2: Get display name (default to directory name)
    default_name = Path.cwd().name

    console.print()
    custom_name = Prompt.ask(
        "Custom display name",
        default=default_name,
        console=console,
    )

    # Use stripped name, fallback to default if empty
    final_name = custom_name.strip() or default_name

    console.print()
    console.print(f"[dim]Project will be registered as '{final_name}'[/]")

    return {
        "global_registry_enabled": True,
        "global_registry_name": final_name,
    }
