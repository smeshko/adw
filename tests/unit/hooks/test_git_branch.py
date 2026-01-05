"""Unit tests for git branch management module.

Tests for sanitize_branch_name, check_uncommitted_changes,
and create_or_switch_branch functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from adw.hooks.git_branch import (
    check_uncommitted_changes,
    create_or_switch_branch,
    sanitize_branch_name,
)


class TestSanitizeBranchName:
    """Tests for sanitize_branch_name function."""

    def test_lowercase_conversion(self) -> None:
        """Should convert to lowercase."""
        assert sanitize_branch_name("Add User Auth") == "add-user-auth"

    def test_spaces_to_hyphens(self) -> None:
        """Should replace spaces with hyphens."""
        assert (
            sanitize_branch_name("add user authentication") == "add-user-authentication"
        )

    def test_multiple_spaces_to_single_hyphen(self) -> None:
        """Should collapse multiple spaces to single hyphen."""
        assert sanitize_branch_name("add   user   auth") == "add-user-auth"

    def test_remove_special_characters(self) -> None:
        """Should remove special characters."""
        result = sanitize_branch_name("Add @user! auth#123")
        assert result == "add-user-auth123"

    def test_preserve_alphanumeric_and_hyphens(self) -> None:
        """Should preserve alphanumeric chars and hyphens."""
        assert sanitize_branch_name("add-user-123") == "add-user-123"

    def test_max_length_50(self) -> None:
        """Should truncate to max 50 characters."""
        long_name = "a" * 60
        result = sanitize_branch_name(long_name)
        assert len(result) == 50

    def test_trim_leading_trailing_hyphens(self) -> None:
        """Should trim leading and trailing hyphens."""
        assert sanitize_branch_name("-add-user-") == "add-user"

    def test_collapse_consecutive_hyphens(self) -> None:
        """Should collapse consecutive hyphens."""
        assert sanitize_branch_name("add---user---auth") == "add-user-auth"

    def test_real_world_example(self) -> None:
        """Should handle realistic feature names."""
        assert (
            sanitize_branch_name("Add user authentication") == "add-user-authentication"
        )
        assert sanitize_branch_name("Fix bug #123 in login") == "fix-bug-123-in-login"

    def test_empty_string(self) -> None:
        """Should handle empty string gracefully."""
        assert sanitize_branch_name("") == ""

    def test_only_special_chars(self) -> None:
        """Should handle string with only special characters."""
        assert sanitize_branch_name("@#$%^&*()") == ""


class TestCheckUncommittedChanges:
    """Tests for check_uncommitted_changes function."""

    def test_clean_working_tree(self) -> None:
        """Should return False for clean working tree."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            assert check_uncommitted_changes() is False

    def test_uncommitted_changes_exist(self) -> None:
        """Should return True when changes exist."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=" M src/file.py\n?? new_file.py\n",
                returncode=0,
            )
            assert check_uncommitted_changes() is True

    def test_only_untracked_files(self) -> None:
        """Should detect untracked files as changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="?? new_file.py\n", returncode=0)
            assert check_uncommitted_changes() is True

    def test_only_staged_changes(self) -> None:
        """Should detect staged changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="A  staged_file.py\n", returncode=0
            )
            assert check_uncommitted_changes() is True

    def test_raises_on_git_error(self) -> None:
        """Should raise HookError when git status fails."""
        from adw.exceptions import HookError

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="fatal: not a git repository",
                returncode=128,
            )
            with pytest.raises(HookError) as exc_info:
                check_uncommitted_changes()
            assert exc_info.value.code == "GIT_STATUS_FAILED"


class TestCreateOrSwitchBranch:
    """Tests for create_or_switch_branch function."""

    def test_create_new_branch(self) -> None:
        """Should create new branch when it doesn't exist."""
        with patch("subprocess.run") as mock_run:
            # First call: git branch --list (empty = doesn't exist)
            # Second call: git checkout -b (create)
            mock_run.side_effect = [
                MagicMock(stdout="", returncode=0),
                MagicMock(stdout="", returncode=0),
            ]
            create_or_switch_branch("feature/add-auth")
            assert mock_run.call_count == 2
            # Verify exact commands
            first_call = mock_run.call_args_list[0]
            assert first_call[0][0] == ["git", "branch", "--list", "feature/add-auth"]
            second_call = mock_run.call_args_list[1]
            assert second_call[0][0] == ["git", "checkout", "-b", "feature/add-auth"]

    def test_switch_to_existing_branch(self) -> None:
        """Should switch to existing branch."""
        with patch("subprocess.run") as mock_run:
            # First call: git branch --list (found)
            # Second call: git checkout (switch)
            mock_run.side_effect = [
                MagicMock(stdout="  feature/add-auth\n", returncode=0),
                MagicMock(stdout="", returncode=0),
            ]
            create_or_switch_branch("feature/add-auth")
            assert mock_run.call_count == 2
            # Verify exact commands
            first_call = mock_run.call_args_list[0]
            assert first_call[0][0] == ["git", "branch", "--list", "feature/add-auth"]
            second_call = mock_run.call_args_list[1]
            assert second_call[0][0] == ["git", "checkout", "feature/add-auth"]

    def test_raises_on_git_error(self) -> None:
        """Should raise HookError on git command failure."""
        from adw.exceptions import HookError

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="fatal: not a git repository",
                returncode=128,
            )
            with pytest.raises(HookError) as exc_info:
                create_or_switch_branch("feature/add-auth")
            assert exc_info.value.code == "GIT_BRANCH_FAILED"
