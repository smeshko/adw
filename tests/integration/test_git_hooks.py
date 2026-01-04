"""Integration tests for git hook functionality.

Tests for git branch management with real git repositories,
verifying end-to-end behavior of branch creation, switching,
and uncommitted changes detection.
"""

import subprocess
from pathlib import Path

import pytest

from adw.exceptions import HookError
from adw.hooks.git_branch import (
    check_uncommitted_changes,
    create_or_switch_branch,
    sanitize_branch_name,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create an isolated git repository for testing.

    Creates a minimal git repository with an initial commit
    so that branch operations can be performed.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the initialized git repository.
    """
    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Configure git user for commits
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Create initial file and commit
    (tmp_path / "README.md").write_text("# Test Project\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    return tmp_path


class TestGitBranchIntegration:
    """Integration tests for git branch operations."""

    def test_create_new_branch(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should create a new branch when it doesn't exist."""
        monkeypatch.chdir(git_repo)

        create_or_switch_branch("feature/test-branch")

        # Verify we're on the new branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/test-branch"

    def test_switch_to_existing_branch(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should switch to an existing branch."""
        monkeypatch.chdir(git_repo)

        # Create branch first
        subprocess.run(
            ["git", "checkout", "-b", "feature/existing"],
            capture_output=True,
            check=True,
        )
        # Switch back to main/master
        subprocess.run(
            ["git", "checkout", "-"],
            capture_output=True,
            check=True,
        )

        # Now use our function to switch to existing branch
        create_or_switch_branch("feature/existing")

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/existing"

    def test_idempotent_creation(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should be safe to call multiple times (idempotent)."""
        monkeypatch.chdir(git_repo)

        # Call twice - should not raise
        create_or_switch_branch("feature/idempotent")
        create_or_switch_branch("feature/idempotent")

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/idempotent"

    def test_sanitized_branch_names(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should work with sanitized branch names."""
        monkeypatch.chdir(git_repo)

        # Sanitize and create
        branch_name = "feature/" + sanitize_branch_name("Add User Authentication")
        create_or_switch_branch(branch_name)

        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "feature/add-user-authentication"


class TestUncommittedChangesIntegration:
    """Integration tests for uncommitted changes detection."""

    def test_clean_repo_returns_false(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return False for a clean working tree."""
        monkeypatch.chdir(git_repo)

        assert check_uncommitted_changes() is False

    def test_modified_file_returns_true(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return True when a file is modified."""
        monkeypatch.chdir(git_repo)

        # Modify a file
        (git_repo / "README.md").write_text("# Modified\n")

        assert check_uncommitted_changes() is True

    def test_new_untracked_file_returns_true(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return True for untracked files."""
        monkeypatch.chdir(git_repo)

        # Create new file
        (git_repo / "new_file.txt").write_text("new content")

        assert check_uncommitted_changes() is True

    def test_staged_changes_returns_true(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return True for staged changes."""
        monkeypatch.chdir(git_repo)

        # Create and stage new file
        (git_repo / "staged.txt").write_text("staged content")
        subprocess.run(
            ["git", "add", "staged.txt"],
            capture_output=True,
            check=True,
        )

        assert check_uncommitted_changes() is True

    def test_committed_changes_returns_false(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return False after committing changes."""
        monkeypatch.chdir(git_repo)

        # Create, stage, and commit
        (git_repo / "committed.txt").write_text("committed content")
        subprocess.run(
            ["git", "add", "committed.txt"],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add committed file"],
            capture_output=True,
            check=True,
        )

        assert check_uncommitted_changes() is False


class TestGitHookErrorHandling:
    """Integration tests for error handling in git operations."""

    def test_error_in_non_git_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should raise HookError when not in a git repository."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(HookError) as exc_info:
            create_or_switch_branch("feature/test")

        assert exc_info.value.code == "GIT_BRANCH_FAILED"
        assert "not a git repository" in exc_info.value.stderr.lower() or "not a git repository" in exc_info.value.message.lower()
