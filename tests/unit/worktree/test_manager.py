"""Unit tests for WorktreeManager class.

Tests cover:
- Trees directory management (ensure_trees_directory)
- Worktree creation with branch naming
- Worktree removal with cleanup options
- Error handling for existing branches/worktrees
- Git not available error handling
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestTreesDirectory:
    """Tests for WorktreeManager.ensure_trees_directory()."""

    def test_ensure_creates_directory(self, tmp_path: Path) -> None:
        """Creates trees/ directory when it doesn't exist."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        trees_path = manager.ensure_trees_directory()

        assert trees_path.exists()
        assert trees_path.is_dir()
        assert trees_path == tmp_path / "trees"

    def test_ensure_creates_gitignore(self, tmp_path: Path) -> None:
        """Creates trees/.gitignore with * content."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        manager.ensure_trees_directory()

        gitignore = tmp_path / "trees" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "*" in content
        assert "Ignore all worktree contents" in content

    def test_ensure_adds_to_root_gitignore(self, tmp_path: Path) -> None:
        """Adds trees/ to project .gitignore if not present."""
        from adw.worktree.manager import WorktreeManager

        # Create existing .gitignore
        root_gitignore = tmp_path / ".gitignore"
        root_gitignore.write_text("node_modules/\n.env\n")

        manager = WorktreeManager(project_root=tmp_path)
        manager.ensure_trees_directory()

        content = root_gitignore.read_text()
        assert "trees/" in content
        assert "node_modules/" in content  # Existing content preserved

    def test_ensure_creates_root_gitignore_if_missing(self, tmp_path: Path) -> None:
        """Creates project .gitignore with trees/ if it doesn't exist."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        manager.ensure_trees_directory()

        root_gitignore = tmp_path / ".gitignore"
        assert root_gitignore.exists()
        assert "trees/" in root_gitignore.read_text()

    def test_ensure_idempotent(self, tmp_path: Path) -> None:
        """Multiple calls don't duplicate .gitignore entries."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        # Call multiple times
        manager.ensure_trees_directory()
        manager.ensure_trees_directory()
        manager.ensure_trees_directory()

        # Check root .gitignore
        root_gitignore = tmp_path / ".gitignore"
        content = root_gitignore.read_text()
        # Count occurrences of "trees/"
        count = content.count("trees/")
        assert count == 1, f"Expected 1 occurrence, found {count}"

    def test_ensure_custom_base_dir(self, tmp_path: Path) -> None:
        """Works with custom base directory name."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path, base_dir="worktrees")
        trees_path = manager.ensure_trees_directory()

        assert trees_path == tmp_path / "worktrees"
        assert trees_path.exists()
        assert (trees_path / ".gitignore").exists()

        root_gitignore = tmp_path / ".gitignore"
        assert "worktrees/" in root_gitignore.read_text()

    def test_ensure_preserves_existing_trees_gitignore(self, tmp_path: Path) -> None:
        """Doesn't overwrite existing trees/.gitignore."""
        from adw.worktree.manager import WorktreeManager

        # Create trees dir with custom gitignore
        trees_dir = tmp_path / "trees"
        trees_dir.mkdir()
        trees_gitignore = trees_dir / ".gitignore"
        trees_gitignore.write_text("# Custom content\n*\n!.gitkeep\n")

        manager = WorktreeManager(project_root=tmp_path)
        manager.ensure_trees_directory()

        # Original content should be preserved
        content = trees_gitignore.read_text()
        assert "Custom content" in content
        assert "!.gitkeep" in content

    def test_ensure_handles_entry_without_slash(self, tmp_path: Path) -> None:
        """Doesn't add duplicate if entry exists without trailing slash."""
        from adw.worktree.manager import WorktreeManager

        # Create .gitignore with entry without trailing slash
        root_gitignore = tmp_path / ".gitignore"
        root_gitignore.write_text("trees\n")

        manager = WorktreeManager(project_root=tmp_path)
        manager.ensure_trees_directory()

        content = root_gitignore.read_text()
        # Should not add duplicate
        assert content.count("tree") == 1  # Only original entry


class TestWorktreeManagerCreation:
    """Tests for WorktreeManager.create_worktree()."""

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
        # Create initial commit
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

    def test_create_worktree_success(self, git_repo: Path) -> None:
        """Worktree is created at expected path with correct branch."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"

        worktree_path = manager.create_worktree(run_id)

        # Verify worktree was created
        assert worktree_path.exists()
        assert worktree_path.is_dir()
        assert worktree_path == git_repo / "trees" / run_id

        # Verify the worktree has a .git file (not directory - worktrees use gitfile)
        git_file = worktree_path / ".git"
        assert git_file.exists()

        # Verify branch was created
        result = subprocess.run(
            ["git", "branch", "--list", f"adw/{run_id}"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert f"adw/{run_id}" in result.stdout

    def test_create_worktree_custom_base_dir(self, git_repo: Path) -> None:
        """Worktree is created in custom base directory."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo, base_dir="worktrees")
        run_id = "01HQ1234567890ABCDEFGHIJK"

        worktree_path = manager.create_worktree(run_id)

        assert worktree_path == git_repo / "worktrees" / run_id
        assert worktree_path.exists()

    def test_create_worktree_from_source_branch(self, git_repo: Path) -> None:
        """Worktree is created from specified source branch."""
        from adw.worktree.manager import WorktreeManager

        # Get the default branch name (main or master depending on git config)
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        default_branch = result.stdout.strip()

        # Create a source branch
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
        subprocess.run(
            ["git", "checkout", default_branch],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"

        worktree_path = manager.create_worktree(run_id, source_branch="feature/source")

        # The worktree should have the feature.txt file from source branch
        assert (worktree_path / "feature.txt").exists()

    def test_create_worktree_branch_exists_error(self, git_repo: Path) -> None:
        """Raises WorktreeError when branch already exists."""
        from adw.exceptions import WorktreeError
        from adw.worktree.manager import WorktreeManager

        # Create the branch first
        run_id = "01HQ1234567890ABCDEFGHIJK"
        subprocess.run(
            ["git", "branch", f"adw/{run_id}"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(project_root=git_repo)

        with pytest.raises(WorktreeError) as exc_info:
            manager.create_worktree(run_id)

        assert exc_info.value.code == "BRANCH_EXISTS"
        assert run_id in exc_info.value.message

    def test_create_worktree_worktree_exists_error(self, git_repo: Path) -> None:
        """Raises WorktreeError when worktree path already exists."""
        from adw.exceptions import WorktreeError
        from adw.worktree.manager import WorktreeManager

        run_id = "01HQ1234567890ABCDEFGHIJK"

        # Create the directory first
        worktree_dir = git_repo / "trees" / run_id
        worktree_dir.mkdir(parents=True)

        manager = WorktreeManager(project_root=git_repo)

        with pytest.raises(WorktreeError) as exc_info:
            manager.create_worktree(run_id)

        assert exc_info.value.code == "WORKTREE_PATH_EXISTS"
        assert str(worktree_dir) in exc_info.value.message

    def test_create_worktree_git_not_available(self, tmp_path: Path) -> None:
        """Raises ConfigError when git is not installed."""
        from adw.exceptions import ConfigError
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            with pytest.raises(ConfigError) as exc_info:
                manager.create_worktree("01HQ1234567890ABCDEFGHIJK")

            assert exc_info.value.code == "GIT_NOT_FOUND"

    def test_create_worktree_returns_absolute_path(self, git_repo: Path) -> None:
        """Returned path is always absolute."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"

        worktree_path = manager.create_worktree(run_id)

        assert worktree_path.is_absolute()

    def test_create_worktree_creates_base_dir_if_missing(self, git_repo: Path) -> None:
        """Base directory is created if it doesn't exist."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo, base_dir="new/nested/dir")
        run_id = "01HQ1234567890ABCDEFGHIJK"

        worktree_path = manager.create_worktree(run_id)

        assert (git_repo / "new" / "nested" / "dir").exists()
        assert worktree_path.exists()


class TestWorktreeManagerRemoval:
    """Tests for WorktreeManager.remove_worktree()."""

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
        # Create initial commit
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

    def test_remove_worktree_success(self, git_repo: Path) -> None:
        """Worktree is removed successfully."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"

        # Create a worktree first
        worktree_path = manager.create_worktree(run_id)
        assert worktree_path.exists()

        # Remove it
        result = manager.remove_worktree(run_id)

        assert result is True
        assert not worktree_path.exists()

    def test_remove_worktree_not_found(self, git_repo: Path) -> None:
        """Raises WorktreeError when worktree doesn't exist."""
        from adw.exceptions import WorktreeError
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)

        with pytest.raises(WorktreeError) as exc_info:
            manager.remove_worktree("nonexistent-run-id")

        assert exc_info.value.code == "WORKTREE_NOT_FOUND"

    def test_remove_worktree_uncommitted_changes_without_force(self, git_repo: Path) -> None:
        """Raises WorktreeError when worktree has uncommitted changes and force=False."""
        from adw.exceptions import WorktreeError
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"

        # Create a worktree and make uncommitted changes
        worktree_path = manager.create_worktree(run_id)
        (worktree_path / "new_file.txt").write_text("uncommitted content")

        with pytest.raises(WorktreeError) as exc_info:
            manager.remove_worktree(run_id, force=False)

        assert exc_info.value.code == "WORKTREE_HAS_CHANGES"
        assert worktree_path.exists()  # Worktree should be preserved

    def test_remove_worktree_uncommitted_changes_with_force(self, git_repo: Path) -> None:
        """Worktree is removed when force=True despite uncommitted changes."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"

        # Create a worktree and make uncommitted changes
        worktree_path = manager.create_worktree(run_id)
        (worktree_path / "new_file.txt").write_text("uncommitted content")

        # Force remove should succeed
        result = manager.remove_worktree(run_id, force=True)

        assert result is True
        assert not worktree_path.exists()

    def test_remove_worktree_cleanup_branch(self, git_repo: Path) -> None:
        """Branch is deleted when cleanup_branch=True."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"
        branch_name = f"adw/{run_id}"

        # Create a worktree
        manager.create_worktree(run_id)

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name in result.stdout

        # Remove with cleanup_branch=True
        manager.remove_worktree(run_id, cleanup_branch=True)

        # Verify branch is deleted
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name not in result.stdout

    def test_remove_worktree_preserve_branch_by_default(self, git_repo: Path) -> None:
        """Branch is preserved by default when removing worktree."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"
        branch_name = f"adw/{run_id}"

        # Create and remove worktree
        manager.create_worktree(run_id)
        manager.remove_worktree(run_id)

        # Branch should still exist
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name in result.stdout
