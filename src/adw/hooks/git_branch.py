"""Git branch management utilities for ADW hooks.

This module provides utilities for managing git branches during
ADW workflow execution, including:
- Branch name sanitization
- Uncommitted changes detection
- Branch creation and switching
- Switching a non-worktree run to its branch (ensure_on_branch)

All git operations use subprocess.run() for simplicity and
avoid external dependencies like gitpython.
"""

import re
import subprocess
from pathlib import Path

from adw.exceptions import HookError
from adw.hooks.git_commit import get_current_branch

# Maximum length for branch names.
# Git allows ~256 chars, but we use 50 to keep branch names readable
# in terminal prompts, git log output, and CI/CD dashboards.
MAX_BRANCH_LENGTH = 50


def sanitize_branch_name(feature: str) -> str:
    """Convert a feature description to a valid git branch name.

    Sanitization rules:
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove special characters (keep alphanumeric and hyphens)
    - Collapse multiple consecutive hyphens
    - Truncate to MAX_BRANCH_LENGTH (50) characters
    - Trim leading/trailing hyphens

    Args:
        feature: The feature description (e.g., "Add user authentication")

    Returns:
        A sanitized branch name (e.g., "add-user-authentication")

    Example:
        >>> sanitize_branch_name("Add User Auth")
        'add-user-auth'
        >>> sanitize_branch_name("Fix bug #123!")
        'fix-bug-123'
    """
    if not feature:
        return ""

    # Convert to lowercase
    name = feature.lower()

    # Replace spaces with hyphens
    name = re.sub(r"\s+", "-", name)

    # Remove special characters (keep alphanumeric and hyphens)
    name = re.sub(r"[^a-z0-9-]", "", name)

    # Collapse multiple consecutive hyphens
    name = re.sub(r"-+", "-", name)

    # Trim leading/trailing hyphens
    name = name.strip("-")

    # Truncate to max length
    if len(name) > MAX_BRANCH_LENGTH:
        name = name[:MAX_BRANCH_LENGTH]
        # Ensure we don't end with a hyphen after truncation
        name = name.rstrip("-")

    return name


def check_uncommitted_changes(*, working_dir: Path | None = None) -> bool:
    """Check if the working tree has uncommitted changes.

    Uses `git status --porcelain` to detect any uncommitted changes
    including staged, unstaged, and untracked files.

    Args:
        working_dir: Directory to run git commands in (default: current dir).

    Returns:
        True if uncommitted changes exist, False otherwise.

    Raises:
        HookError: If git status command fails (e.g., not a git repo).

    Example:
        >>> if check_uncommitted_changes():
        ...     print("Please commit or stash your changes first")
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
        cwd=working_dir,
    )

    if result.returncode != 0:
        raise HookError(
            code="GIT_STATUS_FAILED",
            message=f"Failed to check git status: {result.stderr.strip()}",
            phase="pre-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    # Any output means there are changes
    return bool(result.stdout.strip())


def create_or_switch_branch(
    branch_name: str, *, working_dir: Path | None = None
) -> None:
    """Create a new branch or switch to an existing one.

    This function is idempotent: it will create the branch if it
    doesn't exist, or switch to it if it already exists.

    Args:
        branch_name: The full branch name (e.g., "feature/add-auth")
        working_dir: Directory to run git commands in (default: current dir).

    Raises:
        HookError: If git operations fail (e.g., not a git repo)

    Example:
        >>> create_or_switch_branch("feature/add-authentication")
    """
    # Check if branch already exists
    result = subprocess.run(
        ["git", "branch", "--list", branch_name],
        capture_output=True,
        text=True,
        check=False,
        cwd=working_dir,
    )

    if result.returncode != 0:
        raise HookError(
            code="GIT_BRANCH_FAILED",
            message=f"Failed to list branches: {result.stderr.strip()}",
            phase="pre-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    branch_exists = bool(result.stdout.strip())

    if branch_exists:
        # Switch to existing branch
        checkout_result = subprocess.run(
            ["git", "checkout", branch_name],
            capture_output=True,
            text=True,
            check=False,
            cwd=working_dir,
        )
    else:
        # Create and switch to new branch
        checkout_result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True,
            text=True,
            check=False,
            cwd=working_dir,
        )

    if checkout_result.returncode != 0:
        action = "switch to" if branch_exists else "create"
        err_msg = checkout_result.stderr.strip()
        raise HookError(
            code="GIT_BRANCH_FAILED",
            message=f"Failed to {action} branch '{branch_name}': {err_msg}",
            phase="pre-hook",
            exit_code=checkout_result.returncode,
            stderr=checkout_result.stderr,
            suggestion="Check for uncommitted changes or ensure branch name is valid",
        )


def ensure_on_branch(branch_name: str, *, working_dir: Path | None = None) -> None:
    """Make sure the repository in working_dir has branch_name checked out.

    Already on the branch, this does nothing, whatever the state of the tree.
    Otherwise it refuses to switch away from uncommitted changes, and creates
    or switches to the branch on a clean tree.

    Args:
        branch_name: The full branch name (e.g., "feature/add-auth").
        working_dir: Directory to run git commands in (default: current dir).

    Raises:
        HookError: GIT_BRANCH_CHECK_FAILED outside a git repository,
            GIT_UNCOMMITTED_CHANGES on a dirty tree, or GIT_BRANCH_FAILED
            if the checkout fails.

    Example:
        >>> ensure_on_branch("feature/add-auth", working_dir=Path("."))
    """
    if get_current_branch(working_dir=working_dir) == branch_name:
        return

    if check_uncommitted_changes(working_dir=working_dir):
        raise HookError(
            code="GIT_UNCOMMITTED_CHANGES",
            message=(
                f"Cannot switch to branch '{branch_name}': "
                "the working tree has uncommitted changes"
            ),
            phase="run-start",
            suggestion=(
                "Commit or stash your changes, or run with worktree isolation "
                "(drop --no-worktree)"
            ),
        )

    create_or_switch_branch(branch_name, working_dir=working_dir)
