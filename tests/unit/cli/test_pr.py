"""Tests for PR CLI command.

Tests for Story 9.5: Support PR Creation Command.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.cli.pr import _get_base_branch, display_manual_instructions
from adw.core.context_manager import ContextManager
from adw.models import PRDescription, RunContext
from adw.models.task import TaskInfo
from tests.conftest import FakeGh


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_pr_description() -> PRDescription:
    """Create sample PR description."""
    return PRDescription(
        summary="Add user authentication with JWT tokens",
        changes=["Add login endpoint", "Add token refresh", "Add auth middleware"],
        testing="All unit tests pass. Integration tests added.",
        evidence="See screenshots in evidence/screenshots/",
    )


class TestDisplayManualInstructions:
    """Tests for display_manual_instructions function."""

    def test_displays_pr_description(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test displays the PR description for manual copy."""
        with patch("adw.cli.pr.console") as mock_console:
            display_manual_instructions(
                "## Summary\nTest PR",
                "Add feature",
                "main",
            )
            # Verify console.print was called with expected content
            assert mock_console.print.called

    def test_displays_install_instructions(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test displays gh installation instructions."""
        with patch("adw.cli.pr.console") as mock_console:
            display_manual_instructions(
                "## Summary\nTest PR",
                "Add feature",
                "main",
            )
            # Verify console.print was called (installation info is in Panel)
            assert mock_console.print.called
            # Check that print was called multiple times for different sections
            assert mock_console.print.call_count >= 3


class TestGetBaseBranch:
    """Tests for _get_base_branch function.

    ISS-026: Base branch is read from git.base_branch in config,
    defaults to 'main' if not configured.
    """

    def test_returns_main_by_default(self, tmp_path: Path) -> None:
        """Test returns 'main' when no config exists (ISS-026)."""
        # Set up directory structure: project_root/.adw/runs/<run_id>
        project_root = tmp_path
        runs_dir = project_root / ".adw" / "runs"
        run_dir = runs_dir / "test-run"
        run_dir.mkdir(parents=True)

        # No project.yaml - should return default 'main'
        result = _get_base_branch(run_dir)
        assert result == "main"

    def test_reads_from_config(self, tmp_path: Path) -> None:
        """Test reads base_branch from project.yaml config (ISS-026)."""
        # Set up directory structure
        project_root = tmp_path
        runs_dir = project_root / ".adw" / "runs"
        run_dir = runs_dir / "test-run"
        run_dir.mkdir(parents=True)

        # Create project.yaml config with custom base_branch
        config_dir = project_root / ".adw"
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: test-project
language: python
git:
  base_branch: develop
""")

        result = _get_base_branch(run_dir)
        assert result == "develop"


RUN_ID = "01JFTEST000000000000000001"
PR_URL = "https://github.com/o/r/pull/1"


def _saved_context(tmp_path: Path) -> dict[str, Any]:
    context_file = tmp_path / ".adw" / "runs" / RUN_ID / "context.json"
    loaded: dict[str, Any] = json.loads(context_file.read_text())
    return loaded


@pytest.fixture
def completed_run(
    tmp_path: Path, sample_pr_description: PRDescription
) -> Callable[..., RunContext]:
    """Seed a completed run under the cwd's .adw/runs, with a PR description."""

    def make(**overrides: Any) -> RunContext:
        runs_dir = tmp_path / ".adw" / "runs"
        fields: dict[str, Any] = {
            "run_id": RUN_ID,
            "feature_description": "Add user authentication",
            "current_phase": "document",
            "phase_history": ["plan", "build", "validate", "document"],
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "status": "completed",
        }
        fields.update(overrides)
        context = RunContext(**fields)
        doc_dir = runs_dir / RUN_ID / "artifacts" / "document"
        doc_dir.mkdir(parents=True)
        (doc_dir / "pr_description.md").write_text(sample_pr_description.to_markdown())
        ContextManager(runs_dir).save(context)
        return context

    return make


class TestPrCommand:
    """adw pr drives core create_pr against a fake gh on PATH."""

    def test_pr_sets_pr_url(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        fake_gh: FakeGh,
        tmp_path: Path,
    ) -> None:
        """A completed run without a PR gets pr_url saved in context.json (B12)."""
        completed_run()

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 0, result.output
        saved = _saved_context(tmp_path)
        assert saved["pr_url"] == PR_URL
        assert "pr" not in saved["artifacts"]
        assert len(fake_gh.calls()) == 1

    @pytest.mark.parametrize(
        ("configured_base", "flags", "expected_base"),
        [("develop", ["--draft"], "develop"), (None, [], "main")],
    )
    def test_pr_uses_configured_base_and_draft(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        fake_gh: FakeGh,
        tmp_path: Path,
        configured_base: str | None,
        flags: list[str],
        expected_base: str,
    ) -> None:
        """--base comes from git.base_branch (default main); --draft passes through."""
        completed_run()
        if configured_base:
            (tmp_path / ".adw" / "project.yaml").write_text(
                "name: test\nlanguage: python\n"
                f"git:\n  base_branch: {configured_base}\n"
            )

        result = runner.invoke(app, ["pr", RUN_ID, *flags])

        assert result.exit_code == 0, result.output
        argv = fake_gh.calls()[0]
        assert argv[argv.index("--base") + 1] == expected_base
        assert ("--draft" in argv) is bool(flags)

    def test_pr_body_includes_linear_link(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        fake_gh: FakeGh,
    ) -> None:
        """A run with task info gets the Linear link, like the document step."""
        completed_run(
            task_id="ADW-13",
            task_info=TaskInfo(id="uuid-13", identifier="ADW-13", title="Carry PR"),
        )

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 0, result.output
        argv = fake_gh.calls()[0]
        body = argv[argv.index("--body") + 1]
        assert body.endswith("Linear: https://linear.app/adw/issue/ADW-13")

    def test_pr_existing_url_short_circuits(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        fake_gh: FakeGh,
    ) -> None:
        """A run that already has a PR prints it and never calls gh."""
        completed_run(pr_url="https://github.com/o/r/pull/99")

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 0, result.output
        assert "https://github.com/o/r/pull/99" in result.output
        assert fake_gh.calls() == []

    def test_pr_gh_missing_shows_manual_instructions(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        tmp_path: Path,
        tmp_path_factory: pytest.TempPathFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without gh the command fails, showing the manual fallback."""
        completed_run()
        monkeypatch.setenv("PATH", str(tmp_path_factory.mktemp("empty_path")))

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 1
        assert "GH_NOT_INSTALLED" in result.output
        assert "Manual PR Creation Required" in result.output
        assert _saved_context(tmp_path).get("pr_url") is None

    def test_pr_gh_failure_exits_1(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        fake_gh: FakeGh,
    ) -> None:
        """A failed gh call exits 1 with the mapped code."""
        completed_run()
        fake_gh.reply(stdout="", stderr="boom", exit_code=1)

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 1
        assert "GH_PR_FAILED" in result.output

    def test_pr_run_not_found(self, runner: CliRunner) -> None:
        """An unknown run ID exits 1."""
        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_pr_run_not_complete(
        self, runner: CliRunner, completed_run: Callable[..., RunContext]
    ) -> None:
        """A run that isn't completed exits 1."""
        completed_run(status="running")

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 1
        assert "not complete" in result.output.lower()

    def test_pr_no_description(
        self,
        runner: CliRunner,
        completed_run: Callable[..., RunContext],
        fake_gh: FakeGh,
        tmp_path: Path,
    ) -> None:
        """A completed run without a PR description exits 1."""
        completed_run()
        run_dir = tmp_path / ".adw" / "runs" / RUN_ID
        (run_dir / "artifacts" / "document" / "pr_description.md").unlink()

        result = runner.invoke(app, ["pr", RUN_ID])

        assert result.exit_code == 1
        assert "pr_description_not_found" in result.output.lower()
        assert fake_gh.calls() == []
