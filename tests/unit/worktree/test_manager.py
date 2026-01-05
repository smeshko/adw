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


class TestWorktreeAdwStructure:
    """Tests for WorktreeManager.ensure_worktree_adw_structure()."""

    def test_creates_adw_directory(self, tmp_path: Path) -> None:
        """Creates .adw directory in worktree."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        worktree = tmp_path / "trees" / "01HQTEST"
        worktree.mkdir(parents=True)

        manager.ensure_worktree_adw_structure(worktree, "01HQTEST")

        assert (worktree / ".adw").exists()
        assert (worktree / ".adw").is_dir()

    def test_creates_runs_directory(self, tmp_path: Path) -> None:
        """Creates .adw/runs/<run_id> directory."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        worktree = tmp_path / "trees" / "01HQTEST"
        worktree.mkdir(parents=True)

        run_dir = manager.ensure_worktree_adw_structure(worktree, "01HQTEST")

        assert run_dir == worktree / ".adw" / "runs" / "01HQTEST"
        assert run_dir.exists()

    def test_creates_subdirectories(self, tmp_path: Path) -> None:
        """Creates artifacts, logs, and llm subdirectories."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        worktree = tmp_path / "trees" / "01HQTEST"
        worktree.mkdir(parents=True)

        run_dir = manager.ensure_worktree_adw_structure(worktree, "01HQTEST")

        assert (run_dir / "artifacts").exists()
        assert (run_dir / "logs").exists()
        assert (run_dir / "llm").exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        """Multiple calls don't fail or duplicate."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        worktree = tmp_path / "trees" / "01HQTEST"
        worktree.mkdir(parents=True)

        # Call multiple times
        run_dir1 = manager.ensure_worktree_adw_structure(worktree, "01HQTEST")
        run_dir2 = manager.ensure_worktree_adw_structure(worktree, "01HQTEST")

        assert run_dir1 == run_dir2
        assert run_dir1.exists()


class TestArtifactPreservation:
    """Tests for WorktreeManager.preserve_artifacts()."""

    @pytest.fixture
    def worktree_with_artifacts(self, tmp_path: Path) -> tuple[Path, str, Path]:
        """Create a worktree with sample artifacts for testing."""
        run_id = "01HQXK5TEST"
        worktree = tmp_path / "trees" / run_id
        adw_dir = worktree / ".adw" / "runs" / run_id

        adw_dir.mkdir(parents=True)
        (adw_dir / "context.json").write_text('{"run_id": "test"}')
        (adw_dir / "logs").mkdir()
        (adw_dir / "logs" / "run.log").write_text("log content")
        (adw_dir / "artifacts").mkdir()
        (adw_dir / "artifacts" / "output.txt").write_text("artifact content")
        (adw_dir / "llm").mkdir()
        (adw_dir / "llm" / "interaction.json").write_text('{"prompt": "test"}')

        return worktree, run_id, tmp_path

    def test_preserve_copies_context_json(
        self, worktree_with_artifacts: tuple[Path, str, Path]
    ) -> None:
        """context.json is copied to main project."""
        from adw.worktree.manager import WorktreeManager

        worktree, run_id, project_root = worktree_with_artifacts
        manager = WorktreeManager(project_root=project_root)

        preserved = manager.preserve_artifacts(worktree, run_id)

        target = project_root / ".adw" / "runs" / run_id / "context.json"
        assert target.exists()
        assert target in preserved
        assert target.read_text() == '{"run_id": "test"}'

    def test_preserve_copies_log_directory(
        self, worktree_with_artifacts: tuple[Path, str, Path]
    ) -> None:
        """logs/ directory is copied recursively."""
        from adw.worktree.manager import WorktreeManager

        worktree, run_id, project_root = worktree_with_artifacts
        manager = WorktreeManager(project_root=project_root)

        preserved = manager.preserve_artifacts(worktree, run_id)

        logs_dir = project_root / ".adw" / "runs" / run_id / "logs"
        assert logs_dir.exists()
        assert logs_dir in preserved
        assert (logs_dir / "run.log").exists()
        assert (logs_dir / "run.log").read_text() == "log content"

    def test_preserve_creates_manifest(
        self, worktree_with_artifacts: tuple[Path, str, Path]
    ) -> None:
        """worktree-artifacts.json manifest is created."""
        import json

        from adw.worktree.manager import WorktreeManager

        worktree, run_id, project_root = worktree_with_artifacts
        manager = WorktreeManager(project_root=project_root)

        preserved = manager.preserve_artifacts(worktree, run_id)

        manifest = project_root / ".adw" / "runs" / run_id / "worktree-artifacts.json"
        assert manifest.exists()
        assert manifest in preserved

        data = json.loads(manifest.read_text())
        assert data["run_id"] == run_id
        assert "source_worktree" in data
        assert "preserved_at" in data
        assert "artifacts" in data
        assert len(data["artifacts"]) == 4  # context.json, logs, artifacts, llm

    def test_preserve_handles_missing_artifacts(self, tmp_path: Path) -> None:
        """Missing artifacts are skipped without error."""
        from adw.worktree.manager import WorktreeManager

        run_id = "01HQTEST"
        worktree = tmp_path / "trees" / run_id
        adw_dir = worktree / ".adw" / "runs" / run_id
        adw_dir.mkdir(parents=True)
        # Only create context.json, not logs/artifacts/llm
        (adw_dir / "context.json").write_text('{"run_id": "test"}')

        manager = WorktreeManager(project_root=tmp_path)

        # Should not raise
        preserved = manager.preserve_artifacts(worktree, run_id)

        # Only context.json and manifest should be preserved
        assert len(preserved) == 2  # context.json + manifest

    def test_preserve_respects_config(
        self, worktree_with_artifacts: tuple[Path, str, Path]
    ) -> None:
        """Only configured artifacts are preserved."""
        from adw.worktree.manager import WorktreeManager

        worktree, run_id, project_root = worktree_with_artifacts
        manager = WorktreeManager(project_root=project_root)

        # Only preserve context.json
        preserved = manager.preserve_artifacts(
            worktree, run_id, artifacts_to_preserve=["context.json"]
        )

        target_dir = project_root / ".adw" / "runs" / run_id
        assert (target_dir / "context.json").exists()
        assert not (target_dir / "logs").exists()
        assert not (target_dir / "artifacts").exists()
        # manifest + context.json = 2
        assert len(preserved) == 2

    def test_preserve_manifest_format(
        self, worktree_with_artifacts: tuple[Path, str, Path]
    ) -> None:
        """Manifest has correct format with artifact details."""
        import json

        from adw.worktree.manager import WorktreeManager

        worktree, run_id, project_root = worktree_with_artifacts
        manager = WorktreeManager(project_root=project_root)

        manager.preserve_artifacts(worktree, run_id)

        manifest = project_root / ".adw" / "runs" / run_id / "worktree-artifacts.json"
        data = json.loads(manifest.read_text())

        # Check artifact entries
        artifacts = {a["path"]: a for a in data["artifacts"]}
        assert "context.json" in artifacts
        assert artifacts["context.json"]["type"] == "file"
        assert artifacts["context.json"]["size"] > 0
        assert "logs" in artifacts
        assert artifacts["logs"]["type"] == "directory"


class TestWorktreeLifecycleIntegration:
    """Tests for worktree lifecycle integration."""

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

    def test_create_worktree_calls_ensure_trees_directory(self, git_repo: Path) -> None:
        """create_worktree sets up trees directory with gitignore."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQTEST"

        manager.create_worktree(run_id)

        # Trees directory should have .gitignore
        assert (git_repo / "trees" / ".gitignore").exists()
        # Project .gitignore should have trees/ entry
        assert (git_repo / ".gitignore").exists()
        assert "trees/" in (git_repo / ".gitignore").read_text()

    def test_create_worktree_creates_adw_structure(self, git_repo: Path) -> None:
        """create_worktree creates .adw/runs/<run_id>/ structure."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQTEST"

        worktree = manager.create_worktree(run_id)

        # ADW structure should exist in worktree
        adw_run_dir = worktree / ".adw" / "runs" / run_id
        assert adw_run_dir.exists()
        assert (adw_run_dir / "artifacts").exists()
        assert (adw_run_dir / "logs").exists()
        assert (adw_run_dir / "llm").exists()

    def test_remove_worktree_preserves_artifacts(self, git_repo: Path) -> None:
        """remove_worktree preserves artifacts to main project."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQTEST"

        # Create worktree and add artifacts
        worktree = manager.create_worktree(run_id)
        run_dir = worktree / ".adw" / "runs" / run_id
        (run_dir / "context.json").write_text('{"run_id": "test"}')
        (run_dir / "logs" / "run.log").write_text("log content")

        # Remove with preservation (force=True due to uncommitted .adw changes)
        manager.remove_worktree(run_id, preserve=True, force=True)

        # Artifacts should be in main project
        main_run_dir = git_repo / ".adw" / "runs" / run_id
        assert main_run_dir.exists()
        assert (main_run_dir / "context.json").exists()
        assert (main_run_dir / "worktree-artifacts.json").exists()

    def test_remove_worktree_skip_preservation(self, git_repo: Path) -> None:
        """remove_worktree can skip artifact preservation."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQTEST"

        # Create worktree
        worktree = manager.create_worktree(run_id)
        run_dir = worktree / ".adw" / "runs" / run_id
        (run_dir / "context.json").write_text('{"run_id": "test"}')

        # Remove without preservation (force=True due to uncommitted .adw changes)
        manager.remove_worktree(run_id, preserve=False, force=True)

        # Artifacts should NOT be in main project
        main_run_dir = git_repo / ".adw" / "runs" / run_id
        assert not main_run_dir.exists()


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
        worktree_removed, branch_deleted = manager.remove_worktree(run_id)

        assert worktree_removed is True
        assert branch_deleted is False  # Branch preserved by default
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
        worktree_removed, branch_deleted = manager.remove_worktree(run_id, force=True)

        assert worktree_removed is True
        assert branch_deleted is False  # Branch preserved by default
        assert not worktree_path.exists()

    def test_remove_worktree_delete_branch(self, git_repo: Path) -> None:
        """Branch is deleted when delete_branch=True and no PR exists."""
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

        # Mock check_pr_exists to return False (no PR)
        # Without this mock, gh CLI being unavailable returns None,
        # which preserves the branch as a safety measure
        with patch.object(
            manager._branch_manager, "check_pr_exists", return_value=False
        ):
            # Remove with delete_branch=True
            worktree_removed, branch_deleted = manager.remove_worktree(
                run_id, delete_branch=True
            )

        assert worktree_removed is True
        assert branch_deleted is True

        # Verify branch is deleted
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name not in result.stdout

    def test_remove_worktree_preserve_branch_when_gh_unavailable(
        self, git_repo: Path
    ) -> None:
        """Branch is preserved when gh CLI is unavailable (check_pr_exists returns None)."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"
        branch_name = f"adw/{run_id}"

        # Create a worktree
        manager.create_worktree(run_id)

        # Mock check_pr_exists to return None (gh CLI unavailable)
        with patch.object(
            manager._branch_manager, "check_pr_exists", return_value=None
        ):
            # Remove with delete_branch=True but gh unavailable
            worktree_removed, branch_deleted = manager.remove_worktree(
                run_id, delete_branch=True
            )

        assert worktree_removed is True
        assert branch_deleted is False  # Branch preserved when gh unavailable

        # Verify branch still exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name in result.stdout

    def test_remove_worktree_force_delete_branch_when_gh_unavailable(
        self, git_repo: Path
    ) -> None:
        """Branch is deleted with force=True even when gh CLI is unavailable."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQ1234567890ABCDEFGHIJK"
        branch_name = f"adw/{run_id}"

        # Create a worktree
        manager.create_worktree(run_id)

        # Mock check_pr_exists to return None (gh CLI unavailable)
        with patch.object(
            manager._branch_manager, "check_pr_exists", return_value=None
        ):
            # Remove with delete_branch=True and force=True
            worktree_removed, branch_deleted = manager.remove_worktree(
                run_id, delete_branch=True, force=True
            )

        assert worktree_removed is True
        assert branch_deleted is True

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


class TestWorktreeManagerBranchIntegration:
    """Tests for WorktreeManager branch manager integration."""

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

    def test_branch_manager_property_returns_manager(self, git_repo: Path) -> None:
        """branch_manager property returns WorktreeBranchManager instance."""
        from adw.worktree.branch import WorktreeBranchManager
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)

        assert isinstance(manager.branch_manager, WorktreeBranchManager)

    def test_get_branch_name_returns_expected_format(self, git_repo: Path) -> None:
        """get_branch_name returns adw/<run_id> format."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQTEST12345678901234567"

        branch_name = manager.get_branch_name(run_id)

        assert branch_name == f"adw/{run_id}"

    def test_get_branch_name_matches_created_worktree_branch(
        self, git_repo: Path
    ) -> None:
        """get_branch_name returns the same name as the worktree branch."""
        from adw.worktree.manager import WorktreeManager

        manager = WorktreeManager(project_root=git_repo)
        run_id = "01HQTEST12345678901234567"

        # Create worktree
        manager.create_worktree(run_id)

        # Branch name should match
        branch_name = manager.get_branch_name(run_id)

        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name in result.stdout
