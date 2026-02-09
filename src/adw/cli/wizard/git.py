"""Git integration step for the wizard.

This module handles the git integration step of the wizard where users
configure git branch management. Git is mandatory for ADW - the wizard
will exit if not in a git repository.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState

# Branch prefix validation pattern:
# - Must start with a letter (a-zA-Z)
# - Can contain alphanumeric, hyphens, underscores, and slashes
# - Must end with a slash
BRANCH_PREFIX_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_/-]*/$")


class GitStepHandler:
    """Handler for the git integration wizard step.

    This step:
    - Requires a git repository (exits wizard if not)
    - Prompts for branch prefix configuration
    - Git is always enabled (not optional)
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the git integration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - git_branch_prefix: The configured branch prefix

        Raises:
            SystemExit: If not in a git repository.
        """
        return run_git_step(state, console)


def prompt_skip_hooks(console: Console) -> bool:
    """Prompt user whether to skip pre-commit hooks.

    Args:
        console: Console for output.

    Returns:
        True if hooks should be skipped, False otherwise.
    """
    return Confirm.ask(
        "Skip pre-commit hooks?",
        default=False,
        console=console,
    )


def prompt_base_branch(console: Console) -> str | None:
    """Prompt user for PR base branch.

    Args:
        console: Console for output.

    Returns:
        Branch name string, or None if left empty (use default).
    """
    value = Prompt.ask(
        "PR base branch (empty for default)",
        default="",
        console=console,
    )
    return value if value else None


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
        Configuration dict containing git settings.

    Raises:
        SystemExit: If not in a git repository.
    """
    # Step 1: Require git repository (exits if not)
    require_git_repo(console)

    # Step 2: Configure branch prefix
    branch_prefix = prompt_branch_prefix(console)

    # Step 3: Configure skip_hooks and base_branch
    skip_hooks = prompt_skip_hooks(console)
    base_branch = prompt_base_branch(console)

    return {
        "git_branch_prefix": branch_prefix,
        "git_skip_hooks": skip_hooks,
        "git_base_branch": base_branch if base_branch else None,
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
    inside a git working tree. A bare repository returns "false" with
    exit code 0, so we must check stdout to distinguish properly.

    Returns:
        True if inside a git working tree, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Check both returncode and stdout - bare repos return "false" with exit 0
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
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
    if not prefix:
        return False, "Branch prefix cannot be empty"

    # Strip whitespace
    prefix = prefix.strip()

    if not prefix:
        return False, "Branch prefix cannot be empty"

    # Check for spaces
    if " " in prefix:
        return False, "Branch prefix cannot contain spaces"

    # Auto-append trailing slash if missing
    if not prefix.endswith("/"):
        prefix = prefix + "/"

    # Check for consecutive slashes (Git rejects refs with //)
    if "//" in prefix:
        return False, "Branch prefix cannot contain consecutive slashes"

    # Check for invalid start character
    if prefix.startswith("-"):
        return False, "Branch prefix cannot start with '-'"

    # Validate against pattern
    if not BRANCH_PREFIX_PATTERN.match(prefix):
        return (
            False,
            "Invalid branch prefix format. Use alphanumeric, hyphens, "
            "underscores, and slashes only. Must start with a letter.",
        )

    return True, prefix


def prompt_branch_prefix(console: Console) -> str:
    """Prompt user for branch prefix configuration.

    Prompts the user to enter a branch prefix with "feature/" as default.
    Re-prompts if the input is invalid.

    Args:
        console: Console for output.

    Returns:
        The validated and normalized branch prefix.
    """
    console.print()

    while True:
        prefix = Prompt.ask(
            "Branch prefix",
            default="feature/",
            console=console,
        )

        valid, result = validate_branch_prefix(prefix)
        if valid:
            return result

        # Show error and re-prompt
        console.print(f"[red]Error:[/] {result}")
