# Test Reduction Notes:
# Following ADR-001, these tests focus on:
#   - Git repo detection (business logic)
#   - Branch prefix validation (validation rules)
#   - Error handling paths (SystemExit on non-git)
#   - State return structure (API contract)
# NOT testing:
#   - Interactive prompt behavior (requires user input)
#   - Default values (visible in code)
#   - Import verification

"""Tests for git integration wizard step."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from adw.cli.wizard.git import (
    GitStepHandler,
    is_git_repo,
    require_git_repo,
    run_git_step,
    validate_branch_prefix,
)


class TestIsGitRepo:
    """Tests for is_git_repo() function."""

    def test_returns_true_when_in_git_working_tree(self) -> None:
        """is_git_repo returns True when inside a working tree (stdout='true')."""
        with patch("adw.cli.wizard.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
            assert is_git_repo() is True

    def test_returns_false_for_bare_repo(self) -> None:
        """is_git_repo returns False for bare repositories (stdout='false', exit 0)."""
        with patch("adw.cli.wizard.git.subprocess.run") as mock_run:
            # Bare repos return "false" with exit code 0
            mock_run.return_value = MagicMock(returncode=0, stdout="false\n")
            assert is_git_repo() is False

    def test_returns_false_when_not_in_git_repo(self) -> None:
        """is_git_repo returns False when git command fails."""
        with patch("adw.cli.wizard.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="")
            assert is_git_repo() is False

    def test_returns_false_when_git_not_found(self) -> None:
        """is_git_repo returns False when git is not installed."""
        with patch("adw.cli.wizard.git.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert is_git_repo() is False

    def test_returns_false_on_subprocess_error(self) -> None:
        """is_git_repo returns False on subprocess timeout or error."""
        import subprocess

        with patch("adw.cli.wizard.git.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
            assert is_git_repo() is False


class TestRequireGitRepo:
    """Tests for require_git_repo() function."""

    def test_returns_true_when_in_git_repo(self) -> None:
        """require_git_repo returns True when in a git repo."""
        console = Console()
        with patch("adw.cli.wizard.git.is_git_repo", return_value=True):
            result = require_git_repo(console)
            assert result is True

    def test_exits_when_not_in_git_repo(self) -> None:
        """require_git_repo exits with SystemExit(1) when not in a git repo."""
        console = Console(force_terminal=True, no_color=True)
        with patch("adw.cli.wizard.git.is_git_repo", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                require_git_repo(console)
            assert exc_info.value.code == 1


class TestValidateBranchPrefix:
    """Tests for validate_branch_prefix() function."""

    @pytest.mark.parametrize(
        ("prefix", "expected_result"),
        [
            ("feature/", "feature/"),
            ("feature", "feature/"),  # Auto-append
            ("feat/task/", "feat/task/"),
            ("bugfix/", "bugfix/"),
            ("my-feature/", "my-feature/"),
            ("my_feature/", "my_feature/"),
            ("Feature/", "Feature/"),
            ("f123/", "f123/"),
            ("story/14-3/", "story/14-3/"),
            ("  feature  ", "feature/"),  # Strips whitespace
        ],
    )
    def test_valid_prefixes(self, prefix: str, expected_result: str) -> None:
        """validate_branch_prefix accepts valid prefixes and normalizes them."""
        valid, result = validate_branch_prefix(prefix)
        assert valid is True
        assert result == expected_result

    @pytest.mark.parametrize(
        ("prefix", "expected_error_substring"),
        [
            ("", "cannot be empty"),
            ("   ", "cannot be empty"),
            ("-feature/", "cannot start with '-'"),
            ("my feature/", "cannot contain spaces"),
            ("123feature/", "Must start with a letter"),
            ("feature//", "cannot contain consecutive slashes"),
            ("foo//bar/", "cannot contain consecutive slashes"),
        ],
    )
    def test_invalid_prefixes(self, prefix: str, expected_error_substring: str) -> None:
        """validate_branch_prefix rejects invalid prefixes with descriptive errors."""
        valid, error = validate_branch_prefix(prefix)
        assert valid is False
        assert expected_error_substring in error


class TestRunGitStep:
    """Tests for run_git_step() function."""

    def test_returns_correct_structure(self) -> None:
        """run_git_step returns dict with all required keys."""
        from adw.models.wizard import WizardState

        state = WizardState()
        console = Console()

        with (
            patch("adw.cli.wizard.git.require_git_repo", return_value=True),
            patch("adw.cli.wizard.git.prompt_branch_prefix", return_value="feature/"),
            patch("adw.cli.wizard.git.prompt_skip_hooks", return_value=False),
            patch("adw.cli.wizard.git.prompt_base_branch", return_value=None),
        ):
            result = run_git_step(state, console)

        assert "git_branch_prefix" in result
        assert "git_skip_hooks" in result
        assert "git_base_branch" in result

    def test_propagates_prompt_values(self) -> None:
        """run_git_step returns values from prompt functions."""
        from adw.models.wizard import WizardState

        state = WizardState()
        console = Console()

        with (
            patch("adw.cli.wizard.git.require_git_repo", return_value=True),
            patch("adw.cli.wizard.git.prompt_branch_prefix", return_value="bugfix/"),
            patch("adw.cli.wizard.git.prompt_skip_hooks", return_value=True),
            patch("adw.cli.wizard.git.prompt_base_branch", return_value="develop"),
        ):
            result = run_git_step(state, console)

        assert result["git_branch_prefix"] == "bugfix/"
        assert result["git_skip_hooks"] is True
        assert result["git_base_branch"] == "develop"

    def test_empty_base_branch_converts_to_none(self) -> None:
        """run_git_step converts empty base_branch to None."""
        from adw.models.wizard import WizardState

        state = WizardState()
        console = Console()

        with (
            patch("adw.cli.wizard.git.require_git_repo", return_value=True),
            patch("adw.cli.wizard.git.prompt_branch_prefix", return_value="feature/"),
            patch("adw.cli.wizard.git.prompt_skip_hooks", return_value=False),
            patch("adw.cli.wizard.git.prompt_base_branch", return_value=None),
        ):
            result = run_git_step(state, console)

        assert result["git_base_branch"] is None


class TestPromptSkipHooks:
    """Tests for prompt_skip_hooks() function."""

    def test_returns_false_by_default(self) -> None:
        """prompt_skip_hooks returns False when user accepts default."""
        from adw.cli.wizard.git import prompt_skip_hooks

        console = Console()
        with patch("adw.cli.wizard.git.Confirm.ask", return_value=False):
            result = prompt_skip_hooks(console)
        assert result is False

    def test_returns_true_when_confirmed(self) -> None:
        """prompt_skip_hooks returns True when user confirms."""
        from adw.cli.wizard.git import prompt_skip_hooks

        console = Console()
        with patch("adw.cli.wizard.git.Confirm.ask", return_value=True):
            result = prompt_skip_hooks(console)
        assert result is True


class TestPromptBaseBranch:
    """Tests for prompt_base_branch() function."""

    def test_returns_none_for_empty_input(self) -> None:
        """prompt_base_branch returns None when user enters empty string."""
        from adw.cli.wizard.git import prompt_base_branch

        console = Console()
        with patch("adw.cli.wizard.git.Prompt.ask", return_value=""):
            result = prompt_base_branch(console)
        assert result is None

    def test_returns_branch_name(self) -> None:
        """prompt_base_branch returns branch name when provided."""
        from adw.cli.wizard.git import prompt_base_branch

        console = Console()
        with patch("adw.cli.wizard.git.Prompt.ask", return_value="develop"):
            result = prompt_base_branch(console)
        assert result == "develop"


class TestGitStepHandler:
    """Tests for GitStepHandler class."""

    def test_execute_delegates_to_run_git_step(self) -> None:
        """GitStepHandler.execute calls run_git_step."""
        from adw.models.wizard import WizardState

        handler = GitStepHandler()
        state = WizardState()
        console = Console()

        with patch(
            "adw.cli.wizard.git.run_git_step",
            return_value={
                "git_branch_prefix": "test/",
                "git_skip_hooks": False,
                "git_base_branch": None,
            },
        ) as mock_run:
            result = handler.execute(state, console)

        mock_run.assert_called_once_with(state, console)
        assert result["git_branch_prefix"] == "test/"
