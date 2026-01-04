"""Integration tests for git diff capture (Story 9.3).

These tests use actual git operations to verify diff capture behavior
in real git repositories.
"""

import subprocess
from pathlib import Path

import pytest

from adw.hooks.git_diff import (
    DiffStats,
    capture_diff,
    capture_staged_diff,
    get_diff_stats,
    truncate_diff,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with initial commit."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    # Configure git user for commits
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial file and commit
    (repo / "initial.txt").write_text("initial content")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


class TestCaptureDiffIntegration:
    """Integration tests for capture_diff with real git operations."""

    def test_capture_diff_with_real_commit(self, git_repo: Path) -> None:
        """Test capture_diff returns actual git diff content."""
        # Make a change and commit
        (git_repo / "new_file.py").write_text("print('hello')\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Capture diff since previous commit
        diff = capture_diff(since="HEAD~1", working_dir=git_repo)

        assert "diff --git" in diff
        assert "new_file.py" in diff
        assert "print('hello')" in diff

    def test_capture_diff_empty_when_no_changes(self, git_repo: Path) -> None:
        """Test capture_diff returns empty string when no changes since ref."""
        # No changes since HEAD~0 (current commit)
        diff = capture_diff(since="HEAD~0", working_dir=git_repo)

        assert diff == ""

    def test_capture_diff_with_modified_file(self, git_repo: Path) -> None:
        """Test capture_diff captures modifications to existing files."""
        # Modify existing file
        (git_repo / "initial.txt").write_text("modified content\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Modify file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        diff = capture_diff(since="HEAD~1", working_dir=git_repo)

        assert "diff --git" in diff
        assert "initial.txt" in diff
        assert "-initial content" in diff
        assert "+modified content" in diff

    def test_capture_diff_with_deleted_file(self, git_repo: Path) -> None:
        """Test capture_diff captures file deletions."""
        # Delete file
        (git_repo / "initial.txt").unlink()
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Delete file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        diff = capture_diff(since="HEAD~1", working_dir=git_repo)

        assert "diff --git" in diff
        assert "initial.txt" in diff
        assert "deleted file mode" in diff


class TestCaptureStagedDiffIntegration:
    """Integration tests for capture_staged_diff with real git operations."""

    def test_capture_staged_diff_returns_staged_changes(self, git_repo: Path) -> None:
        """Test capture_staged_diff returns only staged changes."""
        # Make changes and stage them
        (git_repo / "staged.py").write_text("# Staged file\n")
        subprocess.run(["git", "add", "staged.py"], cwd=git_repo, check=True)

        # Make unstaged changes (shouldn't appear)
        (git_repo / "unstaged.py").write_text("# Unstaged file\n")

        diff = capture_staged_diff(working_dir=git_repo)

        assert "staged.py" in diff
        assert "Staged file" in diff
        assert "unstaged.py" not in diff

    def test_capture_staged_diff_empty_when_nothing_staged(
        self, git_repo: Path
    ) -> None:
        """Test capture_staged_diff returns empty when nothing staged."""
        # Make unstaged changes only
        (git_repo / "unstaged.py").write_text("# Unstaged\n")

        diff = capture_staged_diff(working_dir=git_repo)

        assert diff == ""


class TestGetDiffStatsIntegration:
    """Integration tests for get_diff_stats with real git output."""

    def test_get_diff_stats_parses_real_git_output(self, git_repo: Path) -> None:
        """Test parsing actual git diff --stat output."""
        # Create multiple files with different changes
        (git_repo / "file1.py").write_text("line1\nline2\nline3\n")
        (git_repo / "file2.py").write_text("a\nb\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get real stat output
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )

        stats = get_diff_stats(result.stdout)

        assert stats.files_changed == 2
        assert stats.insertions == 5  # 3 + 2 lines
        assert stats.deletions == 0

    def test_diff_stats_summary(self, git_repo: Path) -> None:
        """Test DiffStats.summary() method."""
        stats = DiffStats(files_changed=3, insertions=42, deletions=13)
        summary = stats.summary()

        assert "3 files" in summary
        assert "+42" in summary
        assert "-13" in summary


class TestTruncateDiffIntegration:
    """Integration tests for truncate_diff with large diffs."""

    def test_truncate_diff_preserves_small_real_diff(self, git_repo: Path) -> None:
        """Test small real diffs are not truncated."""
        # Create a small change
        (git_repo / "small.txt").write_text("small change\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Small change"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        diff = capture_diff(since="HEAD~1", working_dir=git_repo)
        truncated = truncate_diff(diff)

        # Small diff should be unchanged
        assert truncated == diff
        assert "[TRUNCATED]" not in truncated

    def test_truncate_diff_truncates_large_real_diff(self, git_repo: Path) -> None:
        """Test large real diffs are truncated with notice."""
        # Create a large file
        large_content = "\n".join([f"line {i}" for i in range(5000)])
        (git_repo / "large.txt").write_text(large_content)
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Large file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        diff = capture_diff(since="HEAD~1", working_dir=git_repo)

        # Truncate to 10KB for testing
        truncated = truncate_diff(diff, max_bytes=10240)

        assert len(truncated.encode("utf-8")) < len(diff.encode("utf-8"))
        assert "[TRUNCATED]" in truncated
        assert "diff --git" in truncated  # Header preserved
