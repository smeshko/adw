"""Git commit utilities for ADW hooks.

This module provides utilities for staging changes and creating
commits during ADW workflow execution, including:
- Staging all changes
- Checking for staged changes
- Creating commits with formatted messages

All git operations use subprocess.run() for simplicity and
avoid external dependencies like gitpython.
"""

import subprocess

from adw.exceptions import HookError

# Default commit message template
DEFAULT_COMMIT_TEMPLATE = "[adw] {Phase}: {feature}\n\nRun: {run_id}"


def format_commit_message(
    phase: str,
    feature: str,
    run_id: str,
    *,
    template: str | None = None,
) -> str:
    """Format a commit message for an ADW phase.

    Creates a commit message using the provided phase name, feature
    description, and run ID. Supports custom templates for projects
    that need different commit message formats.

    Args:
        phase: The phase name (e.g., "build", "verify").
        feature: The feature description for this run.
        run_id: The unique run identifier.
        template: Optional custom template. Supports placeholders:
            {phase}, {Phase} (capitalized), {feature}, {run_id}

    Returns:
        Formatted commit message string (UTF-8 encoded).

    Example:
        >>> format_commit_message("build", "Add auth", "01HQ123")
        '[adw] Build: Add auth\\n\\nRun: 01HQ123'
        >>> format_commit_message("build", "Add auth", "01HQ123",
        ...                       template="{phase}: {feature}")
        'build: Add auth'
    """
    if template is None:
        template = DEFAULT_COMMIT_TEMPLATE

    # Create format dict with both lowercase and capitalized phase
    format_dict = {
        "phase": phase,
        "Phase": phase.capitalize(),
        "feature": feature,
        "run_id": run_id,
    }

    return template.format(**format_dict)


def stage_changes() -> list[str]:
    """Stage all changes in the working tree.

    Uses `git add -A` to stage all changes including new files,
    modifications, and deletions.

    Returns:
        List of staged file paths.

    Raises:
        HookError: If git add command fails (e.g., not a git repo).

    Example:
        >>> files = stage_changes()
        >>> print(files)
        ['src/main.py', 'tests/test_main.py']
    """
    # Stage all changes
    add_result = subprocess.run(
        ["git", "add", "-A"],
        capture_output=True,
        text=True,
        check=False,
    )

    if add_result.returncode != 0:
        raise HookError(
            code="GIT_STAGE_FAILED",
            message=f"Failed to stage changes: {add_result.stderr.strip()}",
            phase="post-hook",
            exit_code=add_result.returncode,
            stderr=add_result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    # Get list of staged files
    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )

    if diff_result.returncode != 0:
        raise HookError(
            code="GIT_STAGE_FAILED",
            message=f"Failed to list staged files: {diff_result.stderr.strip()}",
            phase="post-hook",
            exit_code=diff_result.returncode,
            stderr=diff_result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    # Parse file list, filtering empty lines
    files = [f for f in diff_result.stdout.strip().split("\n") if f]
    return files


def has_staged_changes() -> bool:
    """Check if there are staged changes ready to commit.

    Uses `git diff --cached --quiet` which exits with:
    - 0 if no staged changes
    - 1 if there are staged changes

    Returns:
        True if staged changes exist, False otherwise.

    Raises:
        HookError: If git diff command fails unexpectedly (exit code > 1).

    Example:
        >>> if has_staged_changes():
        ...     print("Ready to commit")
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Exit code 0 = no changes, 1 = has changes, >1 = error
    if result.returncode == 0:
        return False
    elif result.returncode == 1:
        return True
    else:
        raise HookError(
            code="GIT_DIFF_FAILED",
            message=f"Failed to check staged changes: {result.stderr.strip()}",
            phase="post-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )


def create_commit(
    phase: str,
    feature: str,
    run_id: str,
    *,
    template: str | None = None,
) -> str | None:
    """Create a commit with the staged changes.

    If there are no staged changes, returns None without error.
    Handles pre-commit hook failures gracefully by raising HookError.

    Args:
        phase: The phase name (e.g., "build", "verify").
        feature: The feature description for this run.
        run_id: The unique run identifier.
        template: Optional custom commit message template.

    Returns:
        Commit SHA if commit was created, None if no changes to commit.

    Raises:
        HookError: If commit fails (e.g., pre-commit hook rejects).

    Example:
        >>> sha = create_commit("build", "Add auth", "01HQ123")
        >>> if sha:
        ...     print(f"Created commit: {sha}")
        ... else:
        ...     print("No changes to commit")
    """
    # Check if there are staged changes first
    if not has_staged_changes():
        return None

    # Format the commit message
    message = format_commit_message(
        phase=phase,
        feature=feature,
        run_id=run_id,
        template=template,
    )

    # Create the commit
    commit_result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )

    if commit_result.returncode != 0:
        raise HookError(
            code="GIT_COMMIT_FAILED",
            message=f"Failed to create commit: {commit_result.stderr.strip()}",
            phase="post-hook",
            exit_code=commit_result.returncode,
            stdout=commit_result.stdout,
            stderr=commit_result.stderr,
            suggestion="Check pre-commit hooks or commit message format",
        )

    # Get the commit SHA
    sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )

    if sha_result.returncode != 0:
        stderr = sha_result.stderr.strip()
        raise HookError(
            code="GIT_COMMIT_FAILED",
            message=f"Commit created but failed to get SHA: {stderr}",
            phase="post-hook",
            exit_code=sha_result.returncode,
            stderr=sha_result.stderr,
            suggestion="Commit may have succeeded - check git log",
        )

    return sha_result.stdout.strip()
