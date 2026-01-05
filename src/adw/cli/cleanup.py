"""Cleanup command for removing worktrees and branches.

This module provides the cleanup command that allows users to remove
worktrees and optionally delete their associated branches.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from adw.cli.bootstrap import get_runs_dir
from adw.core import ContextManager
from adw.exceptions import ConfigError, StateError, WorktreeError
from adw.worktree import ConcurrentRunManager, WorktreeManager

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
                    "(has PR, gh CLI unavailable, or deletion failed)"
                )
        else:
            console.print(f"[dim]Branch preserved: adw/{run_id}[/]")

    except WorktreeError as e:
        if e.code == "WORKTREE_NOT_FOUND":
            console.print("[yellow]![/] Worktree already removed or doesn't exist")
            # Still try to delete branch if requested
            if delete_branch:
                branch_manager = worktree_manager.branch_manager
                # When worktree doesn't exist, user explicitly wants deletion
                # Use force=True since there's no worktree to protect
                deleted = branch_manager.delete_branch(run_id, force=True)
                if deleted:
                    console.print(f"[green]✓[/] Branch deleted: adw/{run_id}")
                else:
                    console.print(
                        f"[yellow]![/] Branch preserved: adw/{run_id} "
                        "(branch not found or deletion failed)"
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


def cleanup_orphans_command(
    delete_branch: bool = typer.Option(
        False,
        "--delete-branch",
        "-b",
        help="Also delete the adw/<run_id> branch for each orphaned worktree",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt and force remove even with uncommitted changes",
    ),
) -> None:
    """Find and remove orphaned worktrees.

    Scans for worktrees that don't have corresponding active lock files
    (from crashed or killed runs) and removes them after confirmation.

    Examples:
        # Find and list orphaned worktrees
        adw cleanup-orphans

        # Remove orphaned worktrees and their branches
        adw cleanup-orphans --delete-branch

        # Skip confirmation
        adw cleanup-orphans --force
    """
    project_root = Path.cwd()
    manager = ConcurrentRunManager(project_root)

    orphaned = manager.get_orphaned_worktrees()

    if not orphaned:
        console.print("[green]No orphaned worktrees found[/]")
        return

    # Display orphaned worktrees
    table = Table(title=f"Orphaned Worktrees ({len(orphaned)})")
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Path", style="dim", max_width=50)

    for worktree_path in orphaned:
        run_id = worktree_path.name
        path_str = str(worktree_path)
        if len(path_str) > 50:
            path_str = "..." + path_str[-47:]
        table.add_row(run_id, path_str)

    console.print(table)

    # Confirm cleanup
    if not force:
        msg = "Remove these orphaned worktrees?"
        if delete_branch:
            msg = "Remove these orphaned worktrees and their branches?"
        if not Confirm.ask(msg, default=False):
            console.print("[green]Cleanup cancelled[/]")
            return

    # Remove each orphaned worktree
    worktree_manager = WorktreeManager(
        project_root=project_root,
        base_dir=manager._base_dir,
    )

    removed_count = 0
    branch_deleted_count = 0

    for worktree_path in orphaned:
        run_id = worktree_path.name

        try:
            worktree_removed, branch_deleted = worktree_manager.remove_worktree(
                run_id,
                force=force,
                delete_branch=delete_branch,
            )

            if worktree_removed:
                removed_count += 1
                console.print(f"[green]✓[/] Removed: {run_id}")

            if branch_deleted:
                branch_deleted_count += 1

        except WorktreeError as e:
            if e.code == "WORKTREE_NOT_FOUND":
                console.print(f"[yellow]![/] Already removed: {run_id}")
            elif e.code == "WORKTREE_HAS_CHANGES":
                console.print(
                    f"[yellow]![/] Has uncommitted changes (use --force): {run_id}"
                )
            else:
                console.print(f"[red]✗[/] Error removing {run_id}: {e.message}")

    # Summary
    console.print()
    console.print(f"[bold]Summary:[/] Removed {removed_count} orphaned worktrees")
    if delete_branch:
        console.print(f"[bold]Branches deleted:[/] {branch_deleted_count}")
