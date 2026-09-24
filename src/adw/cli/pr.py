"""PR creation command for ADW CLI.

This module provides the pr command that opens a GitHub PR for a
completed run through core.pr.create_pr and saves its URL on the run
context. The document step opens PRs through the same function.

Base branch is configurable via git.base_branch in project.yaml.
Defaults to 'main' if not configured.

Examples:
    adw pr 01HQXK5P3Z...              # Create PR from run
    adw pr 01HQXK5P3Z... --draft      # Create as draft PR
"""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax

from adw.cli.bootstrap import require_runs_dir
from adw.core.context_manager import ContextManager
from adw.core.pr import create_pr, generate_pr_title, load_pr_description
from adw.core.run_lookup import RunLookup
from adw.exceptions import ADWError
from adw.models.context import RunStatus

logger = logging.getLogger(__name__)

console = Console()


def display_manual_instructions(
    description: str,
    title: str,
    base: str,
) -> None:
    """Display instructions for manual PR creation.

    Shows the PR description and GitHub URL pattern for users
    who don't have gh CLI installed.

    Args:
        description: Markdown PR description.
        title: Suggested PR title.
        base: Suggested base branch.

    Example:
        >>> display_manual_instructions("## Summary\\n...", "Add login", "main")
    """
    console.print()
    console.print(
        Panel(
            "[yellow]GitHub CLI (gh) not found[/]\n\n"
            "To create a PR automatically, install gh:\n"
            "  • macOS: [cyan]brew install gh[/]\n"
            "  • Linux: [cyan]sudo apt install gh[/] or [cyan]sudo dnf install gh[/]\n"
            "  • Windows: [cyan]winget install GitHub.cli[/]\n\n"
            "After installing, run [cyan]gh auth login[/] to authenticate.",
            title="Manual PR Creation Required",
            border_style="yellow",
        )
    )

    console.print()
    console.print("[bold]Suggested PR Title:[/]")
    console.print(f"  {title}")

    console.print()
    console.print("[bold]Base Branch:[/]")
    console.print(f"  {base}")

    console.print()
    console.print("[bold]PR Description (copy this):[/]")
    console.print()

    # Show description with syntax highlighting
    syntax = Syntax(description, "markdown", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, border_style="dim"))

    console.print()
    console.print("[dim]To create the PR manually:[/]")
    console.print("  1. Push your branch to GitHub")
    console.print("  2. Go to your repository on GitHub")
    console.print("  3. Click 'Compare & pull request'")
    console.print("  4. Paste the description above")
    console.print()


def _get_base_branch(run_dir: Path) -> str:
    """Get the base branch for PR creation.

    Reads git.base_branch from project.yaml config.
    Falls back to the GitConfig default if the config can't be loaded.

    Args:
        run_dir: Path to the run directory (.adw/runs/<run_id>).

    Returns:
        Base branch name from config, or the GitConfig default.
    """
    from adw.config.loader import ConfigLoader
    from adw.models import GitConfig

    # .adw/runs/<id> -> project root
    project_root = run_dir.parent.parent.parent

    try:
        loader = ConfigLoader(project_root)
        if loader.has_project_config:
            return loader.load().git.base_branch
    except Exception:
        # Config loading failed - use default
        pass

    return GitConfig().base_branch


def pr(
    run_id: str | None = typer.Argument(
        None,
        help="Run ID to create PR from (defaults to most recent completed)",
    ),
    draft: bool = typer.Option(
        False,
        "--draft",
        "-d",
        help="Create as draft PR",
    ),
) -> None:
    """Create a GitHub PR from a completed run.

    Uses the PR description generated during the document phase to open
    a pull request via the gh CLI, and saves the PR URL on the run.
    A run that already has a PR prints its URL and exits.

    If PR creation fails, shows the error and the PR description for
    manual copy-paste, and exits 1.

    Base branch is read from git.base_branch in project.yaml config.
    Defaults to 'main' if not configured.

    Examples:
        adw pr                         # Most recent completed run
        adw pr 01HQXK5P3Z...           # Specific run
        adw pr --draft                 # Create as draft PR
    """
    runs_dir = require_runs_dir()
    lookup = RunLookup(runs_dir)

    # Find the run
    if run_id:
        context = lookup.find_by_id(run_id)
        if not context:
            console.print(
                Panel(
                    f"[red]Run not found:[/] {run_id}\n\n"
                    "[dim]Use 'adw list' to see available runs[/]",
                    title="[red]RUN_NOT_FOUND[/]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)
    else:
        # Find most recent completed run
        context = lookup.find_most_recent()
        if not context:
            console.print("[yellow]No runs found[/]")
            console.print("Use 'adw run \"feature\"' to start a new run")
            raise typer.Exit(1)

    # Check run is complete
    if context.status != RunStatus.COMPLETED:
        console.print(
            Panel(
                f"[red]Run is not complete[/]\n\n"
                f"Run ID: {context.run_id}\n"
                f"Status: [yellow]{context.status}[/]\n\n"
                "PR creation requires a completed run with all phases finished.",
                title="[red]RUN_NOT_COMPLETE[/]",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # A run keeps one PR: re-running adw pr reports it
    if context.pr_url:
        console.print(f"[green]✓[/] Run already has a PR: {context.pr_url}")
        return

    run_dir = runs_dir / context.run_id
    try:
        pr_body = load_pr_description(run_dir)
    except ADWError as e:
        _print_error(e)
        raise typer.Exit(1) from None

    # Base branch from config (defaults to main)
    base_branch = _get_base_branch(run_dir)

    console.print(f"[bold]Creating PR from run:[/] {context.run_id}")
    console.print(f"[dim]Base branch:[/] {base_branch}")
    if draft:
        console.print("[dim]Mode:[/] Draft PR")
    console.print()

    try:
        pr_url = create_pr(context, pr_body, base=base_branch, draft=draft)
    except ADWError as e:
        _print_error(e)
        console.print()
        console.print("[yellow]Falling back to manual instructions:[/]")
        display_manual_instructions(pr_body, generate_pr_title(context), base_branch)
        raise typer.Exit(1) from None

    ContextManager(runs_dir).save(context.model_copy(update={"pr_url": pr_url}))

    console.print(
        Panel(
            f"[green]PR created successfully![/]\n\n{pr_url}",
            title="[green]✓ Pull Request Created[/]",
            border_style="green",
        )
    )


def _print_error(error: ADWError) -> None:
    """Print an ADWError as a red panel titled with its code."""
    console.print(
        Panel(
            f"[red]{escape(error.message)}[/]\n\n"
            f"[dim]Suggestion:[/] {escape(error.suggestion or '')}",
            title=f"[red]{error.code}[/]",
            border_style="red",
        )
    )
