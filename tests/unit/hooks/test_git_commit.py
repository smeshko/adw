"""Unit tests for git commit module.

Tests for stage_changes, has_staged_changes, create_commit,
and commit message formatting functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from adw.exceptions import HookError
from adw.hooks.git_commit import (
    create_commit,
    format_commit_message,
    get_unstaged_modifications,
    has_staged_changes,
    stage_changes,
)


class TestFormatCommitMessage:
    """Tests for commit message formatting."""

    def test_basic_format(self) -> None:
        """Should format message with phase, feature, and run_id."""
        result = format_commit_message(
            phase="build",
            feature="Add user auth",
            run_id="01HQ123456",
        )
        assert result == "[adw] Build: Add user auth\n\nRun: 01HQ123456"

    def test_phase_capitalization(self) -> None:
        """Should capitalize the phase name."""
        result = format_commit_message(
            phase="verify",
            feature="Test login",
            run_id="01HQ789",
        )
        assert "[adw] Verify:" in result

    def test_unicode_feature_description(self) -> None:
        """Should handle unicode in feature description."""
        result = format_commit_message(
            phase="build",
            feature="Add émoji support 🚀",
            run_id="01HQ123",
        )
        assert "Add émoji support 🚀" in result

    def test_special_characters_preserved(self) -> None:
        """Should preserve special characters in feature."""
        result = format_commit_message(
            phase="build",
            feature="Fix bug #123 (critical)",
            run_id="01HQ456",
        )
        assert "Fix bug #123 (critical)" in result

    def test_custom_template(self) -> None:
        """Should use custom template when provided."""
        template = "{phase}: {feature} [{run_id}]"
        result = format_commit_message(
            phase="build",
            feature="Add auth",
            run_id="01HQ123",
            template=template,
        )
        assert result == "build: Add auth [01HQ123]"

    def test_long_feature_preserved(self) -> None:
        """Should preserve long feature descriptions."""
        long_feature = "A" * 100
        result = format_commit_message(
            phase="build",
            feature=long_feature,
            run_id="01HQ123",
        )
        # Feature should be preserved in message
        assert long_feature in result
        # Should still have proper structure
        assert "[adw] Build:" in result
        assert "Run: 01HQ123" in result


class TestStageChanges:
    """Tests for stage_changes function."""

    def test_stage_all_changes(self) -> None:
        """Should run git add -A and return staged files."""
        with patch("subprocess.run") as mock_run:
            # First call: git add -A
            # Second call: git diff --cached --name-only
            mock_run.side_effect = [
                MagicMock(returncode=0),
                MagicMock(stdout="file1.py\nfile2.py\n", returncode=0),
            ]
            result = stage_changes()
            assert result == ["file1.py", "file2.py"]
            assert mock_run.call_count == 2
            # Verify git add -A command was called (stages ALL changes including untracked)
            add_call = mock_run.call_args_list[0]
            assert add_call[0][0] == ["git", "add", "-A"]

    def test_stage_with_working_dir(self) -> None:
        """Should pass working_dir to subprocess.run cwd."""
        from pathlib import Path

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),
                MagicMock(stdout="file.py\n", returncode=0),
            ]
            worktree = Path("/my/worktree")
            stage_changes(working_dir=worktree)
            # Both subprocess calls should use cwd=worktree
            for call in mock_run.call_args_list:
                assert call.kwargs.get("cwd") == worktree

    def test_no_changes_to_stage(self) -> None:
        """Should return empty list when no changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),
                MagicMock(stdout="", returncode=0),
            ]
            result = stage_changes()
            assert result == []

    def test_raises_on_git_error(self) -> None:
        """Should raise HookError when git add fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="fatal: not a git repository",
                returncode=128,
            )
            with pytest.raises(HookError) as exc_info:
                stage_changes()
            assert exc_info.value.code == "GIT_STAGE_FAILED"


class TestHasStagedChanges:
    """Tests for has_staged_changes function."""

    def test_has_staged_changes_true(self) -> None:
        """Should return True when staged changes exist."""
        with patch("subprocess.run") as mock_run:
            # git diff --cached --quiet exits with 1 when there are changes
            mock_run.return_value = MagicMock(returncode=1)
            assert has_staged_changes() is True

    def test_has_staged_changes_false(self) -> None:
        """Should return False when no staged changes."""
        with patch("subprocess.run") as mock_run:
            # git diff --cached --quiet exits with 0 when no changes
            mock_run.return_value = MagicMock(returncode=0)
            assert has_staged_changes() is False

    def test_raises_on_git_error(self) -> None:
        """Should raise HookError when git diff fails unexpectedly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="fatal: not a git repository",
                returncode=128,
            )
            with pytest.raises(HookError) as exc_info:
                has_staged_changes()
            assert exc_info.value.code == "GIT_DIFF_FAILED"


class TestGetUnstagedModifications:
    """Tests for get_unstaged_modifications function."""

    def test_returns_modified_files(self) -> None:
        """Should return list of files with unstaged modifications."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="file1.py\nfile2.py\n",
                returncode=0,
            )
            result = get_unstaged_modifications()
            assert result == ["file1.py", "file2.py"]

    def test_returns_empty_list_when_no_modifications(self) -> None:
        """Should return empty list when no unstaged modifications."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            result = get_unstaged_modifications()
            assert result == []

    def test_raises_on_git_error(self) -> None:
        """Should raise HookError when git diff fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="fatal: not a git repository",
                returncode=128,
            )
            with pytest.raises(HookError) as exc_info:
                get_unstaged_modifications()
            assert exc_info.value.code == "GIT_DIFF_FAILED"


class TestCreateCommit:
    """Tests for create_commit function."""

    def test_creates_commit_with_staged_changes(self) -> None:
        """Should create commit and return SHA when changes exist."""
        with patch("subprocess.run") as mock_run:
            # First call: git diff --cached --name-only (get staged files before)
            # Second call: git commit
            # Third call: git diff --name-only (check for unstaged modifications)
            # Fourth call: git rev-parse HEAD
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="file.py\n"),  # staged files
                MagicMock(returncode=0, stdout=""),  # commit
                MagicMock(returncode=0, stdout=""),  # no unstaged mods
                MagicMock(returncode=0, stdout="abc123def456\n"),  # rev-parse
            ]
            with patch("adw.hooks.git_commit.has_staged_changes", return_value=True):
                result = create_commit(
                    phase="build",
                    feature="Add auth",
                    run_id="01HQ123",
                )
            assert result == "abc123def456"

    def test_returns_none_when_no_changes(self) -> None:
        """Should return None when no staged changes."""
        with patch("adw.hooks.git_commit.has_staged_changes", return_value=False):
            result = create_commit(
                phase="build",
                feature="Add auth",
                run_id="01HQ123",
            )
            assert result is None

    def test_raises_on_commit_failure(self) -> None:
        """Should raise HookError when commit fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="file.py\n"),  # staged files
                MagicMock(
                    stdout="",
                    stderr="error: pre-commit hook rejected",
                    returncode=1,
                ),  # commit fails
                MagicMock(returncode=0, stdout=""),  # no unstaged mods (no retry)
            ]
            with patch("adw.hooks.git_commit.has_staged_changes", return_value=True):
                with pytest.raises(HookError) as exc_info:
                    create_commit(
                        phase="build",
                        feature="Add auth",
                        run_id="01HQ123",
                    )
                assert exc_info.value.code == "GIT_COMMIT_FAILED"
                assert "pre-commit" in exc_info.value.stderr

    def test_uses_custom_template(self) -> None:
        """Should use custom commit template when provided."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="file.py\n"),  # staged files
                MagicMock(returncode=0, stdout=""),  # commit
                MagicMock(returncode=0, stdout=""),  # no unstaged mods
                MagicMock(returncode=0, stdout="abc123\n"),  # rev-parse
            ]
            with patch("adw.hooks.git_commit.has_staged_changes", return_value=True):
                create_commit(
                    phase="build",
                    feature="Add auth",
                    run_id="01HQ123",
                    template="{phase}: {feature}",
                )
            # Verify the commit message used (second call is the commit)
            commit_call = mock_run.call_args_list[1]
            commit_msg = commit_call[0][0][3]
            assert commit_msg == "build: Add auth"

    def test_skip_hooks_adds_no_verify(self) -> None:
        """Should add --no-verify flag when skip_hooks=True."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="file.py\n"),  # staged files
                MagicMock(returncode=0, stdout=""),  # commit
                MagicMock(returncode=0, stdout=""),  # no unstaged mods
                MagicMock(returncode=0, stdout="abc123\n"),  # rev-parse
            ]
            with patch("adw.hooks.git_commit.has_staged_changes", return_value=True):
                create_commit(
                    phase="build",
                    feature="Add auth",
                    run_id="01HQ123",
                    skip_hooks=True,
                )
            # Verify --no-verify is in the commit command
            commit_call = mock_run.call_args_list[1]
            commit_cmd = commit_call[0][0]
            assert "--no-verify" in commit_cmd

    def test_creates_commit_with_working_dir(self) -> None:
        """Should pass working_dir to all subprocess calls for worktree support."""
        from pathlib import Path

        worktree = Path("/my/worktree")
        with patch("subprocess.run") as mock_run:
            # staged files before commit, commit, unstaged mods, rev-parse HEAD
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="file.py\n"),  # staged files before
                MagicMock(returncode=0, stdout=""),  # commit
                MagicMock(returncode=0, stdout="abc123def456\n"),  # rev-parse HEAD
            ]
            with patch(
                "adw.hooks.git_commit.has_staged_changes", return_value=True
            ) as mock_has_staged, patch(
                "adw.hooks.git_commit.get_unstaged_modifications", return_value=[]
            ) as mock_unstaged:
                result = create_commit(
                    phase="build",
                    feature="Add auth",
                    run_id="01HQ123",
                    working_dir=worktree,
                )

                # Verify working_dir passed to has_staged_changes
                mock_has_staged.assert_called_once_with(working_dir=worktree)

                # Verify working_dir passed to get_unstaged_modifications
                mock_unstaged.assert_called_once_with(working_dir=worktree)

                assert result == "abc123def456"

                # Verify cwd passed to all subprocess.run calls
                for call in mock_run.call_args_list:
                    assert call.kwargs.get("cwd") == worktree
