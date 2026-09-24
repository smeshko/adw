"""Tests for core PR creation (adw.core.pr).

create_pr runs against a real local git repo with a bare `origin` and a
fake `gh` on PATH (the `fake_gh` fixture), so the push and the gh argv
are observed, not mocked.
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from adw.core.pr import create_pr, generate_pr_title, load_pr_description
from adw.exceptions import ADWError
from adw.models import RunContext
from adw.models.task import TaskInfo
from tests.conftest import FakeGh

RUN_ID = "01KDSG2VDHNK0W4HSCZWJZXWSQ"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo on branch feature/x with one commit, entered as cwd."""
    monkeypatch.chdir(git_repo)
    _git(git_repo, "checkout", "-b", "feature/x")
    (git_repo / "change.txt").write_text("change\n")
    _git(git_repo, "add", "change.txt")
    _git(git_repo, "commit", "-m", "Add change")
    return git_repo


@pytest.fixture
def origin(repo: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A local bare repository added as the repo's `origin`."""
    bare = tmp_path_factory.mktemp("origin") / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(bare)], check=True, capture_output=True
    )
    _git(repo, "remote", "add", "origin", str(bare))
    return bare


def _context(repo: Path, **overrides: Any) -> RunContext:
    fields: dict[str, Any] = {
        "run_id": RUN_ID,
        "feature_description": "Add login",
        "current_phase": "document",
        "started_at": datetime.now(UTC),
        "branch_name": "feature/x",
        "worktree_path": repo,
    }
    fields.update(overrides)
    return RunContext(**fields)


class TestCreatePr:
    """create_pr pushes the branch, runs gh pr create and returns the URL."""

    @pytest.mark.usefixtures("origin")
    def test_success_pushes_branch_and_returns_url(
        self, repo: Path, fake_gh: FakeGh
    ) -> None:
        """The branch lands on origin and gh gets the exact argv."""
        url = create_pr(_context(repo), "Body", base="main")

        assert url == "https://github.com/o/r/pull/1"
        remote = _git(repo, "ls-remote", "origin", "feature/x")
        assert remote.split()[0] == _git(repo, "rev-parse", "HEAD")
        assert fake_gh.calls() == [
            [
                "pr",
                "create",
                "--title",
                "Add login",
                "--body",
                "Body",
                "--base",
                "main",
                "--head",
                "feature/x",
            ]
        ]

    @pytest.mark.usefixtures("origin")
    def test_draft_appends_flag(self, repo: Path, fake_gh: FakeGh) -> None:
        """draft=True ends the argv with --draft."""
        create_pr(_context(repo), "Body", base="main", draft=True)

        assert fake_gh.calls()[0][-1] == "--draft"

    @pytest.mark.usefixtures("origin")
    def test_appends_linear_link_to_body(self, repo: Path, fake_gh: FakeGh) -> None:
        """A run with task info gets the Linear issue link at the end of the body."""
        context = _context(
            repo,
            task_id="ADW-13",
            task_info=TaskInfo(id="uuid-13", identifier="ADW-13", title="Carry PR"),
        )

        create_pr(context, "Body", base="main")

        argv = fake_gh.calls()[0]
        body = argv[argv.index("--body") + 1]
        assert body.endswith("Linear: https://linear.app/adw/issue/ADW-13")
        assert body.startswith("Body\n\n---\n")

    def test_no_branch_skips_push_and_head(self, repo: Path, fake_gh: FakeGh) -> None:
        """Without branch_name there is no push (no origin exists) and no --head."""
        url = create_pr(_context(repo, branch_name=None), "Body", base="main")

        assert url == "https://github.com/o/r/pull/1"
        assert "--head" not in fake_gh.calls()[0]

    @pytest.mark.parametrize(
        ("stdout", "stderr", "exit_code", "code"),
        [
            ("", "HTTP 401: run gh auth login to authenticate", 1, "GH_AUTH_ERROR"),
            ("", "GraphQL: No commits between main and feature/x", 1, "GH_NO_COMMITS"),
            ("", "GraphQL: something unexpected broke", 1, "GH_PR_FAILED"),
            ("", "", 0, "GH_NO_URL"),
        ],
    )
    @pytest.mark.usefixtures("origin")
    def test_gh_failures_map_to_codes(
        self,
        repo: Path,
        fake_gh: FakeGh,
        stdout: str,
        stderr: str,
        exit_code: int,
        code: str,
    ) -> None:
        """Each gh failure raises a bare ADWError with its mapped code."""
        fake_gh.reply(stdout=stdout, stderr=stderr, exit_code=exit_code)

        with pytest.raises(ADWError) as exc_info:
            create_pr(_context(repo), "Body", base="main")

        assert type(exc_info.value) is ADWError
        assert exc_info.value.code == code
        if code == "GH_PR_FAILED":
            assert "something unexpected broke" in exc_info.value.message

    @pytest.mark.usefixtures("origin")
    def test_already_exists_returns_existing_url(
        self, repo: Path, fake_gh: FakeGh
    ) -> None:
        """gh's 'already exists' error with a PR URL returns that URL."""
        fake_gh.reply(
            stdout="",
            stderr=(
                'a pull request for branch "feature/x" into branch "main" '
                "already exists:\nhttps://github.com/o/r/pull/7\n"
            ),
            exit_code=1,
        )

        url = create_pr(_context(repo), "Body", base="main")

        assert url == "https://github.com/o/r/pull/7"

    @pytest.mark.usefixtures("origin")
    def test_already_exists_without_url_fails(
        self, repo: Path, fake_gh: FakeGh
    ) -> None:
        """'already exists' with no PR URL falls back to GH_PR_FAILED."""
        fake_gh.reply(stdout="", stderr="a pull request already exists", exit_code=1)

        with pytest.raises(ADWError) as exc_info:
            create_pr(_context(repo), "Body", base="main")

        assert exc_info.value.code == "GH_PR_FAILED"

    def test_missing_gh_raises_not_installed(
        self,
        repo: Path,
        tmp_path_factory: pytest.TempPathFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With no gh on PATH, create_pr raises GH_NOT_INSTALLED."""
        monkeypatch.setenv("PATH", str(tmp_path_factory.mktemp("empty_path")))

        with pytest.raises(ADWError) as exc_info:
            create_pr(_context(repo, branch_name=None), "Body", base="main")

        assert exc_info.value.code == "GH_NOT_INSTALLED"
        assert exc_info.value.suggestion is not None
        assert "cli.github.com" in exc_info.value.suggestion

    def test_push_failure_raises_before_gh(self, repo: Path, fake_gh: FakeGh) -> None:
        """A failed push (no origin) raises GIT_PUSH_FAILED and never calls gh."""
        with pytest.raises(ADWError) as exc_info:
            create_pr(_context(repo), "Body", base="main")

        assert exc_info.value.code == "GIT_PUSH_FAILED"
        assert "origin" in exc_info.value.message
        assert fake_gh.calls() == []

    def test_timeout_raises_recoverable(self, repo: Path) -> None:
        """A gh timeout raises a recoverable GH_TIMEOUT."""
        timeout = ADWError(
            "GH_TIMEOUT", "`gh pr create` timed out after 60s", recoverable=True
        )
        with (
            patch("adw.core.pr.gh", side_effect=timeout),
            pytest.raises(ADWError) as exc_info,
        ):
            create_pr(_context(repo, branch_name=None), "Body", base="main")

        assert exc_info.value.code == "GH_TIMEOUT"
        assert exc_info.value.recoverable is True

    def test_push_timeout_raises_git_push_failed(self, repo: Path) -> None:
        """A timed-out push is a GIT_PUSH_FAILED that keeps the credentials hint."""
        timeout = ADWError(
            "GIT_TIMEOUT",
            "`git push` timed out after 600s",
            suggestion="check your credentials or ssh-agent",
            recoverable=True,
        )
        with (
            patch("adw.core.pr.git", side_effect=timeout),
            pytest.raises(ADWError) as exc_info,
        ):
            create_pr(_context(repo), "Body", base="main")

        assert exc_info.value.code == "GIT_PUSH_FAILED"
        assert "timed out" in exc_info.value.message
        assert "credential" in (exc_info.value.suggestion or "")


class TestLoadPrDescription:
    """load_pr_description finds, validates and renders pr_description.md."""

    VALID = (
        "## Summary\n\nAdd user auth\n\n## Changes\n\n- Add login endpoint\n\n"
        "## Testing\n\nAll tests pass\n"
    )

    def test_loads_from_document_artifacts(self, tmp_path: Path) -> None:
        """Reads artifacts/document/pr_description.md and returns markdown."""
        doc_dir = tmp_path / "artifacts" / "document"
        doc_dir.mkdir(parents=True)
        (doc_dir / "pr_description.md").write_text(self.VALID)

        body = load_pr_description(tmp_path)

        assert "## Summary" in body
        assert "Add user auth" in body

    def test_falls_back_to_artifacts_root(self, tmp_path: Path) -> None:
        """Falls back to artifacts/pr_description.md."""
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "artifacts" / "pr_description.md").write_text(self.VALID)

        assert "Add user auth" in load_pr_description(tmp_path)

    def test_missing_raises_not_found(self, tmp_path: Path) -> None:
        """No description anywhere raises PR_DESCRIPTION_NOT_FOUND."""
        with pytest.raises(ADWError) as exc_info:
            load_pr_description(tmp_path)

        assert exc_info.value.code == "PR_DESCRIPTION_NOT_FOUND"

    def test_unparseable_raises_invalid(self, tmp_path: Path) -> None:
        """A description without the required sections raises PR_DESCRIPTION_INVALID."""
        doc_dir = tmp_path / "artifacts" / "document"
        doc_dir.mkdir(parents=True)
        (doc_dir / "pr_description.md").write_text("Mock response")

        with pytest.raises(ADWError) as exc_info:
            load_pr_description(tmp_path)

        assert exc_info.value.code == "PR_DESCRIPTION_INVALID"


class TestGeneratePrTitle:
    """Tests for generate_pr_title."""

    @staticmethod
    def _title_context(**overrides: Any) -> RunContext:
        fields: dict[str, Any] = {
            "run_id": RUN_ID,
            "feature_description": "RULE-123",
            "current_phase": "document",
            "started_at": datetime.now(UTC),
            "task_id": "RULE-123",
        }
        fields.update(overrides)
        return RunContext(**fields)

    def test_uses_task_info_title_when_feature_equals_task_id(self) -> None:
        """A run started from a bare task ID is titled with the task's title."""
        context = self._title_context(
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Add remote configuration module",
            ),
        )

        assert generate_pr_title(context) == "RULE-123: Add remote configuration module"

    def test_fallback_to_task_id_when_no_task_info(self) -> None:
        """Without task info the title is the bare task ID, not duplicated."""
        assert generate_pr_title(self._title_context(task_info=None)) == "RULE-123"

    def test_uses_feature_description_when_different_from_task_id(self) -> None:
        """A real feature description is prefixed with the task ID."""
        context = self._title_context(
            feature_description="Add user authentication",
            task_info=TaskInfo(id="uuid-123", identifier="RULE-123", title="Add auth"),
        )

        assert generate_pr_title(context) == "RULE-123: Add user authentication"

    def test_uses_feature_description_when_no_task_id(self) -> None:
        """Without a task ID the title is the feature description."""
        context = self._title_context(
            feature_description="Add user authentication", task_id=None
        )

        assert generate_pr_title(context) == "Add user authentication"

    def test_truncates_long_titles_at_72_chars(self) -> None:
        """Titles over 72 characters are truncated with an ellipsis."""
        context = self._title_context(
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="This is a very long task title that exceeds seventy two "
                "characters limit",
            ),
        )

        title = generate_pr_title(context)

        assert len(title) <= 72
        assert title.endswith("...")

    @pytest.mark.parametrize("task_title", ["", "   "])
    def test_fallback_when_task_info_title_blank(self, task_title: str) -> None:
        """An empty or whitespace-only task title falls back to the task ID."""
        context = self._title_context(
            task_info=TaskInfo(id="uuid-123", identifier="RULE-123", title=task_title),
        )

        assert generate_pr_title(context) == "RULE-123"
