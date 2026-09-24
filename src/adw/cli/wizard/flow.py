"""The init wizard's step sequence.

run_wizard asks each step's questions in order, collects their answers in one
dict keyed by section, and hands it to the summary step, which writes the files.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from adw.cli.wizard.basics import run_basics_step
from adw.cli.wizard.git import run_git_step
from adw.cli.wizard.global_registry import run_global_registry_step
from adw.cli.wizard.phases import run_phases_step
from adw.cli.wizard.summary import run_summary_step
from adw.cli.wizard.task_manager import run_task_manager_step
from adw.cli.wizard.webhooks import run_webhooks_step

Step = Callable[[Console], dict[str, Any]]


def run_wizard(root: Path) -> bool:
    """Run the init wizard in root.

    Args:
        root: Project root; the configuration is written to root/.adw.

    Returns:
        True if the configuration files were written. False if the user
        declined at the summary, the write failed, or stdin ran out; nothing
        was written then.
    """
    console = Console()
    steps: list[tuple[str, str, Step]] = [
        ("basics", "Project Basics", lambda c: run_basics_step(c, root)),
        ("global_registry", "Web Dashboard Registration", run_global_registry_step),
        ("git", "Git Configuration", run_git_step),
        ("task_manager", "Task Manager Integration", run_task_manager_step),
        ("phases", "Phase Configuration", run_phases_step),
        ("webhooks", "Webhook Configuration", run_webhooks_step),
    ]
    total = len(steps) + 1  # the summary is the last step

    _show_welcome(console)
    cfg: dict[str, dict[str, Any]] = {}
    try:
        for number, (section, title, step) in enumerate(steps, start=1):
            _show_step_header(console, number, total, title)
            cfg[section] = step(console)

        _show_step_header(console, total, total, "Configuration Summary")
        return run_summary_step(cfg, console, root)
    except EOFError:
        # Rich's prompts raise this when stdin ends (Ctrl+D, or piped input)
        console.print(
            "\n[yellow]Setup cancelled (no more input). Nothing was written.[/]"
        )
        return False


def _show_welcome(console: Console) -> None:
    """Display wizard welcome message."""
    console.print()
    console.print(
        Panel(
            "[bold]Welcome to the ADW Configuration Wizard![/]\n\n"
            "The wizard asks a few questions, shows a summary, and writes\n"
            "nothing to .adw/ until you confirm it.\n"
            "Press [bold]Enter[/] to accept a default, [bold]Ctrl+C[/] to cancel.",
            title="[blue]ADW Setup Wizard[/]",
            border_style="blue",
        )
    )


def _show_step_header(console: Console, number: int, total: int, title: str) -> None:
    """Display the "Step N/M: title" header for a step."""
    console.print()
    console.print(f"[bold blue]Step {number}/{total}:[/] [bold]{title}[/]")
    console.print("[dim]" + "─" * 50 + "[/]")
