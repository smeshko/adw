"""Cleanup command for removing worktrees and branches.

This module provides the cleanup command that allows users to remove
worktrees and optionally delete their associated branches.
"""

import typer
from rich.console import Console
from rich.prompt import Confirm

from adw.cli.bootstrap import get_runs_dir
from adw.core import ContextManager
from adw.exceptions import ConfigError, StateError, WorktreeError
from adw.worktree import WorktreeManager

console = Console()


def cleanup_command(
    run_id: str = typer.Argument(
        ...,
        help="Run ID to clean up",
    ),
    delete_branch: bool = typer.Option(
        False,
        "--delete-branch",
        "-b",
        help="Also delete the adw/<run_id> branch after removing worktree",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force cleanup without confirmation (required if worktree has changes)",
    ),
) -> None:
    """Clean up worktree and optionally branch for a run.

    Removes the worktree directory created for a run. By default, preserves
    the branch for debugging or later PR creation.

    Use --delete-branch to also remove the branch. Note: branches with
    existing PRs or unpushed commits will be preserved unless --force is used.

    Examples:
        # Remove worktree only (preserve branch)
        adw cleanup 01HQXK5P3Z7V8R2M4N6T9W1Y3C

        # Remove worktree and branch
        adw cleanup 01HQXK5P3Z7V8R2M4N6T9W1Y3C --delete-branch

        # Force cleanup (skip confirmations, delete even with uncommitted changes)
        adw cleanup 01HQXK5P3Z7V8R2M4N6T9W1Y3C --force --delete-branch
    """
    runs_dir = get_runs_dir()
    context_manager = ContextManager(runs_dir)

    # Try to load context to get worktree info
    try:
        context = context_manager.load(run_id)
    except StateError as e:
        if e.code == "CONTEXT_NOT_FOUND":
            raise ConfigError(
                code="RUN_NOT_FOUND",
                message=f"Run {run_id} not found",
                suggestion="Use 'adw list' to see available runs",
                recoverable=False,
            ) from e
        raise

    # Check if run used worktree
    if not context.use_worktree or context.worktree_path is None:
        raise ConfigError(
            code="NO_WORKTREE",
            message=f"Run {run_id} did not use worktree isolation",
            suggestion="Nothing to clean up for runs without worktrees",
            recoverable=False,
        )

    # Warn about branch deletion
    if delete_branch and not force:
        console.print(
            "[yellow]⚠ Warning:[/] --delete-branch will permanently remove "
            f"the branch 'adw/{run_id}'"
        )
        console.print(
            "[dim]Branches with existing PRs or unpushed commits "
            "will be preserved unless --force is used[/]"
        )
        if not Confirm.ask("Continue with cleanup?", default=False):
            console.print("[green]Cleanup cancelled[/]")
            return

    # Get project root from worktree path
    # Worktree path is like /project/trees/<run_id>, so project root is parent's parent
    project_root = context.worktree_path.parent.parent
    worktree_manager = WorktreeManager(
        project_root=project_root,
        base_dir=context.worktree_path.parent.name,
    )

    try:
        worktree_removed, branch_deleted = worktree_manager.remove_worktree(
            run_id,
            force=force,
            delete_branch=delete_branch,
        )

        if worktree_removed:
            console.print(f"[green]✓[/] Worktree removed: {context.worktree_path}")

        if delete_branch:
            if branch_deleted:
                console.print(f"[green]✓[/] Branch deleted: adw/{run_id}")
            else:
                console.print(
                    f"[yellow]![/] Branch preserved: adw/{run_id} "
                    "(has PR or unpushed commits)"
                )
        else:
            console.print(f"[dim]Branch preserved: adw/{run_id}[/]")

    except WorktreeError as e:
        if e.code == "WORKTREE_NOT_FOUND":
            console.print("[yellow]![/] Worktree already removed or doesn't exist")
            # Still try to delete branch if requested
            if delete_branch:
                branch_manager = worktree_manager.branch_manager
                deleted = branch_manager.delete_branch(run_id, force=force)
                if deleted:
                    console.print(f"[green]✓[/] Branch deleted: adw/{run_id}")
                else:
                    console.print(
                        f"[yellow]![/] Branch preserved: adw/{run_id} "
                        "(has PR or unpushed commits)"
                    )
        elif e.code == "WORKTREE_HAS_CHANGES":
            worktree_path = context.worktree_path
            console.print(
                f"[red]Error:[/] Worktree has uncommitted changes: {worktree_path}"
            )
            console.print("[dim]Suggestion:[/] Use --force to discard changes")
            raise typer.Exit(1) from None
        else:
            raise
