"""Unit tests for WorktreeBranchManager class.

Tests cover:
- Branch name generation (adw/<run_id> format)
- Branch existence checking
- Branch creation from various refs
- Error handling for existing branches
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBranchNaming:
    """Tests for branch name generation."""

    def test_get_branch_name_format(self, tmp_path: Path) -> None:
        """Branch name follows adw/<run_id> format."""
        from adw.worktree.branch import WorktreeBranchManager

        manager = WorktreeBranchManager(tmp_path)
        name = manager.get_branch_name("01HQTEST12345678901234567")

        assert name == "adw/01HQTEST12345678901234567"

    def test_get_branch_name_preserves_ulid(self, tmp_path: Path) -> None:
        """Branch name preserves the full ULID without modification."""
        from adw.worktree.branch import WorktreeBranchManager

        manager = WorktreeBranchManager(tmp_path)
        run_id = "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        name = manager.get_branch_name(run_id)

        assert name == f"adw/{run_id}"
        assert run_id in name


class TestBranchExists:
    """Tests for branch existence checking."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository for testing."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
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
        readme = tmp_path / "README.md"
        readme.write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        return tmp_path

    def test_existing_branch_returns_true(self, git_repo: Path) -> None:
        """Returns True for existing branch."""
        from adw.worktree.branch import WorktreeBranchManager

        # Create a branch first
        subprocess.run(
            ["git", "branch", "adw/01HQTEST12345678901234567"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeBranchManager(git_repo)
        exists = manager.branch_exists("adw/01HQTEST12345678901234567")

        assert exists is True

    def test_missing_branch_returns_false(self, git_repo: Path) -> None:
        """Returns False for non-existent branch."""
        from adw.worktree.branch import WorktreeBranchManager

        manager = WorktreeBranchManager(git_repo)
        exists = manager.branch_exists("adw/nonexistent-branch-12345")

        assert exists is False

    def test_branch_exists_handles_git_not_available(self, tmp_path: Path) -> None:
        """Returns False when git is not available."""
        from adw.worktree.branch import WorktreeBranchManager

        manager = WorktreeBranchManager(tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            result = manager.branch_exists("adw/01HQTEST")

        assert result is False


class TestBranchCreation:
    """Tests for branch creation."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository for testing."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
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
        readme = tmp_path / "README.md"
        readme.write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        return tmp_path

    def test_creates_branch_from_head(self, git_repo: Path) -> None:
        """Creates branch from HEAD when no base specified."""
        from adw.worktree.branch import WorktreeBranchManager

        manager = WorktreeBranchManager(git_repo)
        run_id = "01HQTEST12345678901234567"

        branch_name = manager.create_branch(run_id)

        assert branch_name == f"adw/{run_id}"

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name in result.stdout

    def test_creates_branch_from_ref(self, git_repo: Path) -> None:
        """Creates branch from specified base ref."""
        from adw.worktree.branch import WorktreeBranchManager

        # Create a feature branch with extra content
        subprocess.run(
            ["git", "checkout", "-b", "feature/source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "feature.txt").write_text("feature content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        feature_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Get default branch name
        result = subprocess.run(
            ["git", "config", "init.defaultBranch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        default_branch = result.stdout.strip() or "master"
        subprocess.run(
            ["git", "checkout", default_branch],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeBranchManager(git_repo)
        run_id = "01HQTEST12345678901234567"

        branch_name = manager.create_branch(run_id, base_ref="feature/source")

        # Verify the new branch points to the feature branch commit
        new_branch_sha = subprocess.run(
            ["git", "rev-parse", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        assert new_branch_sha == feature_sha

    def test_raises_if_branch_exists(self, git_repo: Path) -> None:
        """Raises WorktreeError if branch already exists."""
        from adw.exceptions import WorktreeError
        from adw.worktree.branch import WorktreeBranchManager

        run_id = "01HQTEST12345678901234567"

        # Create the branch first
        subprocess.run(
            ["git", "branch", f"adw/{run_id}"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeBranchManager(git_repo)

        with pytest.raises(WorktreeError) as exc_info:
            manager.create_branch(run_id)

        assert exc_info.value.code == "BRANCH_EXISTS"
        assert f"adw/{run_id}" in exc_info.value.message
