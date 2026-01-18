"""Git integration step for the wizard.

This module handles the git integration step of the wizard where users
configure git branch management. Git is mandatory for ADW - the wizard
will exit if not in a git repository.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class GitStepHandler:
    """Handler for the git integration wizard step.

    This step:
    - Requires a git repository (exits wizard if not)
    - Prompts for branch prefix configuration
    - Prompts for auto-PR creation setting
    - Git is always enabled (not optional)
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the git integration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - git_enabled: Always True (git is mandatory)
            - git_branch_prefix: The configured branch prefix
            - git_auto_create_pr: Whether to auto-create PRs

        Raises:
            SystemExit: If not in a git repository.
        """
        return run_git_step(state, console)


def run_git_step(
    state: WizardState,  # noqa: ARG001 - state reserved for future use
    console: Console,
) -> dict[str, Any]:
    """Execute the git integration step.

    This is the main entry point for the git step, implementing
    the full interactive flow for git configuration.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing git_enabled, git_branch_prefix,
        and git_auto_create_pr values.

    Raises:
        SystemExit: If not in a git repository.
    """
    # Step 1: Require git repository (exits if not)
    require_git_repo(console)

    # Step 2: Configure branch prefix
    branch_prefix = prompt_branch_prefix(console)

    # Step 3: Configure auto-PR creation
    auto_create_pr = prompt_auto_create_pr(console)

    return {
        "git_enabled": True,  # Always enabled - git is mandatory
        "git_branch_prefix": branch_prefix,
        "git_auto_create_pr": auto_create_pr,
    }


def require_git_repo(console: Console) -> bool:
    """Require current directory to be inside a git repository.

    Checks if the current directory is inside a git repository using
    `git rev-parse --is-inside-work-tree`. If not, displays an error
    message with guidance and exits the wizard.

    Args:
        console: Console for output.

    Returns:
        True if valid git repo.

    Raises:
        SystemExit: If not in a git repository.
    """
    if is_git_repo():
        return True

    # Not a git repo - show error and exit
    console.print()
    console.print(
        Panel(
            "[red bold]Git repository required[/]\n\n"
            "ADW needs git for branch management and worktree isolation.\n\n"
            "[dim]To fix:[/]\n"
            "  1. Run [cyan]git init[/] to initialize a repository\n"
            "  2. Re-run [cyan]adw init[/]",
            title="Error",
            border_style="red",
        )
    )
    raise SystemExit(1)


def is_git_repo() -> bool:
    """Check if current directory is inside a git repository.

    Uses `git rev-parse --is-inside-work-tree` to detect if we're
    inside a git working tree.

    Returns:
        True if inside a git repository, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def validate_branch_prefix(prefix: str) -> tuple[bool, str]:
    """Validate branch prefix format.

    Validates that the branch prefix follows git naming conventions:
    - No spaces allowed
    - Must end with '/' (auto-appended if missing)
    - Valid git branch characters only (alphanumeric, -, _, /)
    - Cannot start with '-'

    Args:
        prefix: The branch prefix to validate.

    Returns:
        Tuple of (is_valid, result_or_error).
        If valid, result_or_error is the normalized prefix (with trailing /).
        If invalid, result_or_error is the error message.
    """
    # Placeholder - will be implemented in Task 3
    if not prefix:
        return False, "Branch prefix cannot be empty"
    return True, prefix if prefix.endswith("/") else prefix + "/"


def prompt_branch_prefix(console: Console) -> str:
    """Prompt user for branch prefix configuration.

    Args:
        console: Console for output.

    Returns:
        The validated and normalized branch prefix.
    """
    # Placeholder - will be implemented in Task 4
    _ = console  # Suppress unused warning
    return "feature/"


def prompt_auto_create_pr(console: Console) -> bool:
    """Prompt user for auto-PR creation setting.

    Args:
        console: Console for output.

    Returns:
        True if user wants auto-PR creation, False otherwise.
    """
    # Placeholder - will be implemented in Task 4
    _ = console  # Suppress unused warning
    return True
