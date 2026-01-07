"""Git commit utilities for ADW hooks.

This module provides utilities for staging changes and creating
commits during ADW workflow execution, including:
- Staging all changes
- Checking for staged changes
- Creating commits with formatted messages
- Handling pre-commit hooks that modify files

All git operations use subprocess.run() for simplicity and
avoid external dependencies like gitpython.
"""

import subprocess
from pathlib import Path

from adw.exceptions import HookError

# Default commit message template
DEFAULT_COMMIT_TEMPLATE = "[adw] {Phase}: {feature}\n\nRun: {run_id}"

# Maximum retries when pre-commit hook modifies files
MAX_HOOK_RETRIES = 3


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
        phase: The phase name (e.g., "build", "validate").
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


def stage_changes(*, working_dir: Path | None = None) -> list[str]:
    """Stage all changes in the working tree.

    Uses `git add -A` to stage all changes including new files,
    modifications, and deletions.

    Args:
        working_dir: Directory to run git commands in (default: current dir).
            Essential for worktree support.

    Returns:
        List of staged file paths.

    Raises:
        HookError: If git add command fails (e.g., not a git repo).

    Example:
        >>> files = stage_changes()
        >>> print(files)
        ['src/main.py', 'tests/test_main.py']
        >>> files = stage_changes(working_dir=Path("/my/worktree"))
    """
    cwd = working_dir if working_dir is not None else None

    # Stage all changes
    add_result = subprocess.run(
        ["git", "add", "-A"],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
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
        cwd=cwd,
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


def has_staged_changes(*, working_dir: Path | None = None) -> bool:
    """Check if there are staged changes ready to commit.

    Uses `git diff --cached --quiet` which exits with:
    - 0 if no staged changes
    - 1 if there are staged changes

    Args:
        working_dir: Directory to run git commands in (default: current dir).

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
        cwd=working_dir,
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


def get_unstaged_modifications(*, working_dir: Path | None = None) -> list[str]:
    """Get list of files with unstaged modifications.

    Uses `git diff --name-only` to find files that have been modified
    but not yet staged. This is useful for detecting when pre-commit
    hooks have modified files after staging.

    Args:
        working_dir: Directory to run git commands in (default: current dir).

    Returns:
        List of file paths with unstaged modifications.

    Raises:
        HookError: If git diff command fails.

    Example:
        >>> modified = get_unstaged_modifications()
        >>> if modified:
        ...     print(f"Files modified: {modified}")
    """
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
        cwd=working_dir,
    )

    if result.returncode != 0:
        raise HookError(
            code="GIT_DIFF_FAILED",
            message=f"Failed to check unstaged changes: {result.stderr.strip()}",
            phase="post-hook",
            exit_code=result.returncode,
            stderr=result.stderr,
            suggestion="Ensure you are in a git repository",
        )

    # Parse file list, filtering empty lines
    files = [f for f in result.stdout.strip().split("\n") if f]
    return files


def create_commit(
    phase: str,
    feature: str,
    run_id: str,
    *,
    template: str | None = None,
    skip_hooks: bool = False,
    working_dir: Path | None = None,
) -> str | None:
    """Create a commit with the staged changes.

    If there are no staged changes, returns None without error.
    Handles pre-commit hook failures gracefully by raising HookError.

    When pre-commit hooks modify files (e.g., formatters), this function
    will automatically re-stage the modified files and retry the commit
    up to MAX_HOOK_RETRIES times.

    Args:
        phase: The phase name (e.g., "build", "validate").
        feature: The feature description for this run.
        run_id: The unique run identifier.
        template: Optional custom commit message template.
        skip_hooks: If True, use --no-verify to skip pre-commit hooks.
        working_dir: Directory to run git commands in (default: current dir).
            Essential for worktree support.

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
        >>> sha = create_commit("build", "Add auth", "01HQ123",
        ...                     working_dir=Path("/my/worktree"))
    """
    cwd = working_dir if working_dir is not None else None

    # Check if there are staged changes first
    if not has_staged_changes(working_dir=working_dir):
        return None

    # Format the commit message
    message = format_commit_message(
        phase=phase,
        feature=feature,
        run_id=run_id,
        template=template,
    )

    # Build commit command
    commit_cmd = ["git", "commit", "-m", message]
    if skip_hooks:
        commit_cmd.insert(2, "--no-verify")

    # Attempt commit with retry for hook-modified files
    for attempt in range(MAX_HOOK_RETRIES):
        # Record files that are currently staged
        staged_before = set(
            subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=False,
                cwd=cwd,
            )
            .stdout.strip()
            .split("\n")
        )

        # Create the commit
        commit_result = subprocess.run(
            commit_cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )

        if commit_result.returncode == 0:
            # Commit succeeded - check if hooks modified any files
            modified = get_unstaged_modifications(working_dir=working_dir)
            hook_modified = [f for f in modified if f in staged_before]

            if hook_modified and attempt < MAX_HOOK_RETRIES - 1:
                # Pre-commit hook modified files - re-stage and amend
                stage_changes(working_dir=working_dir)
                # Amend the commit with the hook-modified files
                amend_result = subprocess.run(
                    ["git", "commit", "--amend", "--no-edit"],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=cwd,
                )
                if amend_result.returncode != 0:
                    stderr = amend_result.stderr.strip()
                    raise HookError(
                        code="GIT_COMMIT_FAILED",
                        message=f"Failed to amend commit with hook changes: {stderr}",
                        phase="post-hook",
                        exit_code=amend_result.returncode,
                        stderr=amend_result.stderr,
                        suggestion="Pre-commit hook modified files but amend failed",
                    )

            # Get the commit SHA
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
                cwd=cwd,
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

        # Commit failed - check if it's due to hook modifying files
        modified = get_unstaged_modifications(working_dir=working_dir)
        hook_modified = [f for f in modified if f in staged_before]

        if hook_modified and attempt < MAX_HOOK_RETRIES - 1:
            # Re-stage modified files and retry
            stage_changes(working_dir=working_dir)
            continue

        # Not a hook modification issue or out of retries
        raise HookError(
            code="GIT_COMMIT_FAILED",
            message=f"Failed to create commit: {commit_result.stderr.strip()}",
            phase="post-hook",
            exit_code=commit_result.returncode,
            stdout=commit_result.stdout,
            stderr=commit_result.stderr,
            suggestion="Check pre-commit hooks or commit message format",
        )

    # Should not reach here, but handle edge case
    raise HookError(
        code="GIT_COMMIT_FAILED",
        message="Commit failed after maximum retries",
        phase="post-hook",
        exit_code=1,
        suggestion="Pre-commit hooks may be continuously modifying files",
    )
