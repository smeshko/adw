"""Unit tests for git_diff module.

Tests for capturing git diffs, parsing diff statistics,
and truncating large diffs.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.exceptions import HookError
from adw.hooks.git_diff import (
    capture_diff,
    capture_staged_diff,
    count_binary_files,
    get_diff_stats,
    has_commits,
    truncate_diff,
)
from adw.models.artifacts import DiffStats


class TestCaptureDiff:
    """Tests for capture_diff function."""

    def test_capture_diff_returns_diff_content(self) -> None:
        """Test that capture_diff returns diff content from git."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/file.py b/file.py\n+added line"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = capture_diff()

            assert "diff --git" in result
            mock_run.assert_called()

    def test_capture_diff_with_custom_since(self) -> None:
        """Test capture_diff with custom since parameter."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff content"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            capture_diff(since="HEAD~3")

            # Verify the command includes HEAD~3
            call_args = mock_run.call_args[0][0]
            assert "HEAD~3" in call_args

    def test_capture_diff_handles_no_changes(self) -> None:
        """Test capture_diff returns empty string when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = capture_diff()

            assert result == ""

    def test_capture_diff_handles_git_error(self) -> None:
        """Test capture_diff raises HookError on git failure."""
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_result.stderr = "fatal: bad revision 'HEAD~1'"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(HookError) as exc_info:
                capture_diff()

            assert exc_info.value.code == "GIT_DIFF_FAILED"

    def test_capture_diff_uses_no_color_flag(self) -> None:
        """Test capture_diff disables colorized output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            capture_diff()

            call_args = mock_run.call_args[0][0]
            assert "--no-color" in call_args

    def test_capture_diff_with_working_dir(self) -> None:
        """Test capture_diff uses specified working directory."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            capture_diff(working_dir=Path("/test/project"))

            assert mock_run.call_args[1]["cwd"] == Path("/test/project")


class TestCaptureStagedDiff:
    """Tests for capture_staged_diff function."""

    def test_capture_staged_diff_returns_cached_diff(self) -> None:
        """Test that capture_staged_diff returns staged changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/staged.py b/staged.py\n+staged line"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = capture_staged_diff()

            assert "staged.py" in result
            call_args = mock_run.call_args[0][0]
            assert "--cached" in call_args

    def test_capture_staged_diff_handles_no_staged_changes(self) -> None:
        """Test capture_staged_diff returns empty when nothing staged."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = capture_staged_diff()

            assert result == ""


class TestTruncateDiff:
    """Tests for truncate_diff function."""

    def test_truncate_diff_preserves_small_diff(self) -> None:
        """Test that small diffs are not truncated."""
        small_diff = "diff --git a/file.py b/file.py\n+added line"
        result = truncate_diff(small_diff)

        assert result == small_diff

    def test_truncate_diff_truncates_large_diff(self) -> None:
        """Test that large diffs are truncated."""
        large_content = "x" * 200000  # 200KB
        large_diff = f"diff --git a/file.py b/file.py\n{large_content}"

        result = truncate_diff(large_diff, max_bytes=1024)

        assert len(result.encode("utf-8")) <= 1024 + 200  # Allow for truncation notice
        assert "[TRUNCATED]" in result

    def test_truncate_diff_preserves_file_headers(self) -> None:
        """Test that file headers are preserved when truncating."""
        header = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n"
        large_content = "x" * 200000
        large_diff = f"{header}{large_content}"

        result = truncate_diff(large_diff, max_bytes=1024)

        assert "diff --git" in result

    def test_truncate_diff_adds_truncation_notice(self) -> None:
        """Test that truncation notice includes line count."""
        large_diff = "\n".join([f"line {i}" for i in range(10000)])

        result = truncate_diff(large_diff, max_bytes=1024)

        assert "[TRUNCATED]" in result

    def test_truncate_diff_handles_empty_diff(self) -> None:
        """Test truncate_diff handles empty input."""
        result = truncate_diff("")

        assert result == ""

    def test_truncate_diff_respects_max_bytes(self) -> None:
        """Test truncate_diff respects the max_bytes parameter."""
        large_diff = "a" * 200000
        max_bytes = 50000

        result = truncate_diff(large_diff, max_bytes=max_bytes)

        # Result should be smaller than max_bytes + truncation notice
        assert len(result.encode("utf-8")) < max_bytes + 500


class TestGetDiffStats:
    """Tests for get_diff_stats function."""

    def test_get_diff_stats_parses_stat_output(self) -> None:
        """Test parsing of git diff --stat output."""
        stat_output = """\
 src/main.py | 10 +++++++---
 src/utils.py | 5 ++---
 2 files changed, 9 insertions(+), 4 deletions(-)
"""
        stats = get_diff_stats(stat_output)

        assert stats.files_changed == 2
        assert stats.insertions == 9
        assert stats.deletions == 4

    def test_get_diff_stats_handles_single_file(self) -> None:
        """Test parsing stats for single file change."""
        stat_output = """\
 README.md | 1 +
 1 file changed, 1 insertion(+)
"""
        stats = get_diff_stats(stat_output)

        assert stats.files_changed == 1
        assert stats.insertions == 1
        assert stats.deletions == 0

    def test_get_diff_stats_handles_deletions_only(self) -> None:
        """Test parsing stats with only deletions."""
        stat_output = """\
 old_file.py | 50 --------------------------------------------------
 1 file changed, 50 deletions(-)
"""
        stats = get_diff_stats(stat_output)

        assert stats.files_changed == 1
        assert stats.insertions == 0
        assert stats.deletions == 50

    def test_get_diff_stats_handles_empty_stat(self) -> None:
        """Test get_diff_stats with empty input."""
        stats = get_diff_stats("")

        assert stats.files_changed == 0
        assert stats.insertions == 0
        assert stats.deletions == 0

    def test_diff_stats_model_validation(self) -> None:
        """Test DiffStats model validation."""
        stats = DiffStats(files_changed=5, insertions=100, deletions=50)

        assert stats.files_changed == 5
        assert stats.insertions == 100
        assert stats.deletions == 50

    def test_diff_stats_to_summary(self) -> None:
        """Test DiffStats summary generation."""
        stats = DiffStats(files_changed=3, insertions=42, deletions=13)

        summary = stats.summary()

        assert "3 files" in summary
        assert "+42" in summary
        assert "-13" in summary

    def test_diff_stats_with_binary_files(self) -> None:
        """Test DiffStats includes binary files in summary."""
        stats = DiffStats(files_changed=3, insertions=42, deletions=13, binary_files=2)

        summary = stats.summary()

        assert "3 files" in summary
        assert "(2 binary)" in summary

    def test_diff_stats_binary_files_default_zero(self) -> None:
        """Test DiffStats defaults binary_files to 0."""
        stats = DiffStats(files_changed=1, insertions=1, deletions=0)

        assert stats.binary_files == 0


class TestHasCommits:
    """Tests for has_commits function."""

    def test_has_commits_returns_true_for_repository_with_commits(self) -> None:
        """Test has_commits returns True when repository has commits."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = has_commits()

            assert result is True

    def test_has_commits_returns_false_for_empty_repository(self) -> None:
        """Test has_commits returns False for initial commit case."""
        mock_result = MagicMock()
        mock_result.returncode = 128  # git rev-parse fails with no commits

        with patch("subprocess.run", return_value=mock_result):
            result = has_commits()

            assert result is False

    def test_has_commits_with_working_dir(self) -> None:
        """Test has_commits uses specified working directory."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            has_commits(working_dir=Path("/test/repo"))

            assert mock_run.call_args[1]["cwd"] == Path("/test/repo")


class TestCountBinaryFiles:
    """Tests for count_binary_files function."""

    def test_count_binary_files_detects_binary_markers(self) -> None:
        """Test count_binary_files counts binary file markers in diff."""
        diff_with_binaries = """
diff --git a/image.png b/image.png
Binary files a/image.png and b/image.png differ
diff --git a/code.py b/code.py
--- a/code.py
+++ b/code.py
+print("hello")
diff --git a/doc.pdf b/doc.pdf
Binary files /dev/null and b/doc.pdf differ
"""
        count = count_binary_files(diff_with_binaries)

        assert count == 2

    def test_count_binary_files_returns_zero_for_no_binaries(self) -> None:
        """Test count_binary_files returns 0 when no binary files."""
        text_diff = """
diff --git a/code.py b/code.py
--- a/code.py
+++ b/code.py
+print("hello")
"""
        count = count_binary_files(text_diff)

        assert count == 0

    def test_count_binary_files_handles_empty_diff(self) -> None:
        """Test count_binary_files handles empty input."""
        assert count_binary_files("") == 0

    def test_count_binary_files_handles_none_like_input(self) -> None:
        """Test count_binary_files handles falsy input."""
        assert count_binary_files("") == 0


class TestGetDiffStatsWithBinaryFiles:
    """Tests for get_diff_stats with binary file detection."""

    def test_get_diff_stats_includes_binary_count(self) -> None:
        """Test get_diff_stats parses and includes binary file count."""
        stat_output = "2 files changed, 10 insertions(+), 5 deletions(-)"
        diff_content = "Binary files a/image.png and b/image.png differ"

        stats = get_diff_stats(stat_output, diff_content)

        assert stats.files_changed == 2
        assert stats.insertions == 10
        assert stats.deletions == 5
        assert stats.binary_files == 1

    def test_get_diff_stats_without_diff_content(self) -> None:
        """Test get_diff_stats works without diff content (backwards compatible)."""
        stat_output = "1 file changed, 5 insertions(+)"

        stats = get_diff_stats(stat_output)

        assert stats.files_changed == 1
        assert stats.insertions == 5
        assert stats.binary_files == 0
