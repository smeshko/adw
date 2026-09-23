"""Shared pytest fixtures for ADW tests.

This module provides common fixtures for testing ADW components:
- isolated_home: Points HOME at a per-test directory (autouse)
- git_repo: Creates isolated git repository with worktree cleanup

IMPORTANT: ADW_MOCK_EXECUTOR is set at module load time to ensure all tests
(including subprocess-based integration tests) use MockExecutor instead of
hitting the real Claude API.
"""

import os
import shutil
import subprocess
from collections.abc import Generator

# Force mock executor for ALL tests - prevents hitting real Claude API
# This MUST be set before any test imports or runs
os.environ["ADW_MOCK_EXECUTOR"] = "1"

# Set dummy Linear credentials for tests that trigger task manager initialization
# This prevents ConfigError when running CLI commands that load project config
# with task_manager.type: linear (the real project config uses Linear)
os.environ.setdefault("LINEAR_API_KEY", "test-linear-api-key-for-tests")
os.environ.setdefault("LINEAR_TEAM_ID", "test-team-id-for-tests")

from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="function")
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Automatically give each test its own HOME.

    This fixture runs automatically for every test (autouse=True) and points
    HOME at a per-test directory, so everything under ~/.adw (index, project
    registry, stats cache, user-level commands) resolves there instead of the
    user's real home. Subprocesses inherit the redirected HOME.

    A fake HOME hides the user's global git identity, so the git author and
    committer are set through the environment.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.
        monkeypatch: Pytest's monkeypatch fixture for environment manipulation.

    Returns:
        Path to the isolated home directory.

    Note:
        Never clear os.environ in a test: without HOME, Path.home() falls
        back to the passwd entry, which is the real home.
    """
    # A subdirectory, not tmp_path itself: tests that chdir to tmp_path
    # would otherwise see ~/.adw as the project's .adw/
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_AUTHOR_NAME", "ADW Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "adw-test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "ADW Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "adw-test@example.com")
    return home


@pytest.fixture
def git_repo(tmp_path: Path) -> Generator[Path]:
    """Create an isolated git repository for testing with automatic cleanup.

    This fixture creates a temporary git repository with an initial commit,
    then cleans up any worktrees and branches created during the test.

    The fixture tracks worktrees created by tests and ensures they are
    properly removed during teardown, even if the test fails. This prevents
    orphaned worktrees from accumulating after test runs.

    Args:
        tmp_path: Pytest's built-in temporary path fixture.

    Yields:
        Path to the created git repository.

    Example:
        >>> def test_worktree_creation(git_repo):
        ...     from adw.worktree.manager import WorktreeManager
        ...     manager = WorktreeManager(project_root=git_repo)
        ...     worktree = manager.create_worktree("test-run-id")
        ...     assert worktree.exists()
        ...     # Worktree is automatically cleaned up after test
    """
    # Initialize git repository
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit (required for worktree creation)
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repository")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    try:
        yield tmp_path
    finally:
        # Cleanup: Remove all worktrees and their branches
        _cleanup_worktrees(tmp_path)


def _cleanup_worktrees(repo_path: Path) -> None:
    """Clean up all worktrees and associated branches in a git repository.

    This helper function removes all git worktrees in the trees/ directory
    and deletes their associated adw/* branches.

    Args:
        repo_path: Path to the git repository root.
    """
    trees_dir = repo_path / "trees"
    if not trees_dir.exists():
        return

    # Get list of all worktrees before cleanup
    worktree_result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    # Parse worktree paths from porcelain output
    worktree_paths: list[str] = []
    for line in worktree_result.stdout.splitlines():
        if line.startswith("worktree "):
            path = line[9:]  # Remove "worktree " prefix
            # Skip the main worktree (repo_path itself)
            if Path(path) != repo_path:
                worktree_paths.append(path)

    # Remove each worktree with force flag
    for worktree_path in worktree_paths:
        subprocess.run(
            ["git", "worktree", "remove", worktree_path, "--force"],
            cwd=repo_path,
            capture_output=True,
        )

    # Clean up any remaining directories in trees/
    for item in trees_dir.iterdir():
        if item.is_dir() and item.name != ".locks" and item.name != ".gitignore":
            # Force remove directory if it still exists
            shutil.rmtree(item, ignore_errors=True)

    # Delete all adw/* branches
    branch_result = subprocess.run(
        ["git", "branch", "--list", "adw/*"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    for line in branch_result.stdout.splitlines():
        branch_name = line.strip().lstrip("* ")
        if branch_name:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=repo_path,
                capture_output=True,
            )


# NOTE: Session-scoped cleanup_orphaned_worktrees was removed (ISS-024 review).
# The git_repo fixture already cleans up worktrees via yield/finally.
# A session-scoped cleanup that scans the real project's trees/ directory
# is dangerous because it would delete legitimate developer worktrees
# (ADW production also creates ULID-named worktrees in trees/).
# Tests use tmp_path so they don't create orphans in the real project.
