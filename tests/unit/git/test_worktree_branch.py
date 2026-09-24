"""Unit tests for the worktree branch helpers in adw.git.

Covers branch_exists, delete_branch and pr_exists, including how each one
treats a missing binary and a timeout.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from adw.exceptions import ADWError
from adw.git import branch_exists, delete_branch, pr_exists

BRANCH = "adw/01HQTEST12345678901234567"


def _git_timeout() -> ADWError:
    return ADWError("GIT_TIMEOUT", "`git branch --list` timed out after 60s")


def _branches(repo: Path, name: str) -> str:
    result = subprocess.run(
        ["git", "branch", "--list", name],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture
def repo_with_branch(git_repo: Path) -> Path:
    """Git repo with an adw/ branch created."""
    subprocess.run(
        ["git", "branch", BRANCH], cwd=git_repo, check=True, capture_output=True
    )
    return git_repo


class TestBranchExists:
    def test_existing_branch_returns_true(self, repo_with_branch: Path) -> None:
        assert branch_exists(BRANCH, working_dir=repo_with_branch) is True

    def test_missing_branch_returns_false(self, git_repo: Path) -> None:
        assert branch_exists("adw/nonexistent", working_dir=git_repo) is False

    def test_missing_git_returns_false(self, tmp_path: Path) -> None:
        with patch("adw.git.git", side_effect=FileNotFoundError("git not found")):
            assert branch_exists(BRANCH, working_dir=tmp_path) is False

    def test_branch_exists_propagates_a_timeout(self, tmp_path: Path) -> None:
        # "unknown" must never read as "absent": callers delete branches on False
        with (
            patch("adw.git.git", side_effect=_git_timeout()),
            pytest.raises(ADWError, match="timed out"),
        ):
            branch_exists(BRANCH, working_dir=tmp_path)


class TestDeleteBranch:
    def test_force_deletes_branch(self, repo_with_branch: Path) -> None:
        assert delete_branch(BRANCH, working_dir=repo_with_branch) is True
        assert BRANCH not in _branches(repo_with_branch, BRANCH)

    def test_deletes_any_named_branch(self, git_repo: Path) -> None:
        feature_branch = "feature/add-user-auth"
        subprocess.run(
            ["git", "branch", feature_branch],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        assert delete_branch(feature_branch, working_dir=git_repo) is True
        assert feature_branch not in _branches(git_repo, feature_branch)

    def test_missing_branch_counts_as_deleted(self, git_repo: Path) -> None:
        assert delete_branch("adw/nonexistent", working_dir=git_repo) is True

    def test_checked_out_branch_is_refused(self, git_repo: Path) -> None:
        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        assert delete_branch(current, working_dir=git_repo) is False

    def test_delete_branch_reports_failure_when_the_check_times_out(
        self, tmp_path: Path
    ) -> None:
        with patch("adw.git.git", side_effect=_git_timeout()):
            assert delete_branch(BRANCH, working_dir=tmp_path) is False


class TestPrExists:
    def test_returns_none_when_gh_is_missing(self, tmp_path: Path) -> None:
        with patch("adw.git.gh", side_effect=FileNotFoundError("gh not found")):
            assert pr_exists(BRANCH, working_dir=tmp_path) is None

    def test_returns_none_when_gh_times_out(self, tmp_path: Path) -> None:
        timeout = ADWError("GH_TIMEOUT", "`gh pr view` timed out after 300s")
        with patch("adw.git.gh", side_effect=timeout):
            assert pr_exists(BRANCH, working_dir=tmp_path) is None

    def test_returns_none_when_gh_fails(self, tmp_path: Path) -> None:
        failed = subprocess.CompletedProcess(["gh"], 1, "", "no pull requests found")
        with patch("adw.git.gh", return_value=failed):
            assert pr_exists(BRANCH, working_dir=tmp_path) is None

    @pytest.mark.parametrize(
        ("state", "expected"),
        [("OPEN", True), ("MERGED", True), ("CLOSED", False)],
    )
    def test_reads_the_pr_state(
        self, tmp_path: Path, state: str, expected: bool
    ) -> None:
        found = subprocess.CompletedProcess(["gh"], 0, f'{{"state":"{state}"}}', "")
        with patch("adw.git.gh", return_value=found):
            assert pr_exists(BRANCH, working_dir=tmp_path) is expected
