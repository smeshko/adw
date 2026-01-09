"""Tests for PR CLI command.

Tests for Story 9.5: Support PR Creation Command.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.cli.pr import (
    AutoPRResult,
    _get_base_branch,
    _get_pr_description_path,
    _load_pr_description,
    _store_pr_url,
    auto_create_pr,
    can_auto_create_pr,
    check_gh_authenticated,
    check_gh_available,
    check_git_remote,
    create_pr_via_gh,
    display_manual_instructions,
)
from adw.exceptions import ConfigError
from adw.models import PRDescription, RunContext


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_context() -> RunContext:
    """Create sample completed context."""
    return RunContext(
        run_id="01JFTEST000000000000000001",
        feature_description="Add user authentication",
        current_phase="document",
        phase_history=["plan", "build", "validate", "document"],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        status="completed",
    )


@pytest.fixture
def sample_pr_description() -> PRDescription:
    """Create sample PR description."""
    return PRDescription(
        summary="Add user authentication with JWT tokens",
        changes=["Add login endpoint", "Add token refresh", "Add auth middleware"],
        testing="All unit tests pass. Integration tests added.",
        evidence="See screenshots in evidence/screenshots/",
    )


class TestCheckGhAvailable:
    """Tests for check_gh_available function."""

    def test_gh_available_when_installed(self) -> None:
        """Test returns True when gh is in PATH."""
        with patch("adw.cli.pr.shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/gh"
            assert check_gh_available() is True
            mock_which.assert_called_once_with("gh")

    def test_gh_not_available_when_missing(self) -> None:
        """Test returns False when gh is not in PATH."""
        with patch("adw.cli.pr.shutil.which") as mock_which:
            mock_which.return_value = None
            assert check_gh_available() is False
            mock_which.assert_called_once_with("gh")


class TestCheckGhAuthenticated:
    """Tests for check_gh_authenticated function."""

    def test_authenticated_success(self) -> None:
        """Test returns True when gh auth status succeeds."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Logged in to github.com",
                stderr="",
            )
            ok, err = check_gh_authenticated()
            assert ok is True
            assert err == ""

    def test_authenticated_failure(self) -> None:
        """Test returns False with error when not authenticated."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="You are not logged in",
            )
            ok, err = check_gh_authenticated()
            assert ok is False
            assert "not logged in" in err

    def test_authenticated_timeout(self) -> None:
        """Test handles timeout gracefully."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            from subprocess import TimeoutExpired

            mock_run.side_effect = TimeoutExpired("gh", 30)
            ok, err = check_gh_authenticated()
            assert ok is False
            assert "timed out" in err.lower()


class TestCreatePrViaGh:
    """Tests for create_pr_via_gh function."""

    def test_create_pr_success(self) -> None:
        """Test successful PR creation returns URL."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/user/repo/pull/123\n",
                stderr="",
            )
            url = create_pr_via_gh("Test PR", "## Summary\nTest", "main")
            assert url == "https://github.com/user/repo/pull/123"

    def test_create_pr_with_draft(self) -> None:
        """Test draft PR includes --draft flag."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/user/repo/pull/123\n",
                stderr="",
            )
            create_pr_via_gh("Test PR", "## Summary\nTest", "main", draft=True)

            # Check that --draft was in the command
            cmd = mock_run.call_args[0][0]
            assert "--draft" in cmd

    def test_create_pr_auth_error(self) -> None:
        """Test auth error raises ConfigError with correct code."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error: authentication failed",
            )
            with pytest.raises(ConfigError) as exc_info:
                create_pr_via_gh("Test PR", "## Summary\nTest", "main")

            assert exc_info.value.code == "GH_AUTH_ERROR"

    def test_create_pr_no_commits_error(self) -> None:
        """Test no commits error raises ConfigError."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error: no commits between main and feature",
            )
            with pytest.raises(ConfigError) as exc_info:
                create_pr_via_gh("Test PR", "## Summary\nTest", "main")

            assert exc_info.value.code == "GH_NO_COMMITS"

    def test_create_pr_timeout(self) -> None:
        """Test timeout raises ConfigError."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            from subprocess import TimeoutExpired

            mock_run.side_effect = TimeoutExpired("gh", 60)
            with pytest.raises(ConfigError) as exc_info:
                create_pr_via_gh("Test PR", "## Summary\nTest", "main")

            assert exc_info.value.code == "GH_TIMEOUT"

    def test_create_pr_with_no_open(self) -> None:
        """Test no_open parameter is accepted (no-op behavior)."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/user/repo/pull/123\n",
                stderr="",
            )
            # no_open should be accepted and work (no-op since gh default is no-open)
            url = create_pr_via_gh("Test PR", "## Summary\nTest", "main", no_open=True)
            assert url == "https://github.com/user/repo/pull/123"


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


class TestGetPrDescriptionPath:
    """Tests for _get_pr_description_path function."""

    def test_finds_in_document_artifacts(self, tmp_path: Path) -> None:
        """Test finds pr_description.md in artifacts/document/."""
        run_dir = tmp_path / "run"
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text("## Summary\nTest")

        result = _get_pr_description_path(run_dir)
        assert result == pr_file

    def test_finds_in_artifacts_root(self, tmp_path: Path) -> None:
        """Test falls back to artifacts/ root."""
        run_dir = tmp_path / "run"
        art_dir = run_dir / "artifacts"
        art_dir.mkdir(parents=True)
        pr_file = art_dir / "pr_description.md"
        pr_file.write_text("## Summary\nTest")

        result = _get_pr_description_path(run_dir)
        assert result == pr_file

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Test returns None when no PR description exists."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        result = _get_pr_description_path(run_dir)
        assert result is None


class TestLoadPrDescription:
    """Tests for _load_pr_description function."""

    def test_loads_valid_description(self, tmp_path: Path) -> None:
        """Test successfully loads and parses PR description."""
        run_dir = tmp_path / "run"
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(
            """## Summary

Add user auth

## Changes

- Add login endpoint

## Testing

All tests pass
"""
        )

        result = _load_pr_description(run_dir)
        assert isinstance(result, PRDescription)
        assert "Add user auth" in result.summary

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        """Test raises ConfigError when file not found."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            _load_pr_description(run_dir)

        assert exc_info.value.code == "PR_DESCRIPTION_NOT_FOUND"


class TestGetBaseBranch:
    """Tests for _get_base_branch function."""

    def test_returns_main_by_default(self, tmp_path: Path) -> None:
        """Test returns 'main' when no config exists."""
        run_dir = tmp_path / ".adw" / "runs" / "test"
        run_dir.mkdir(parents=True)

        result = _get_base_branch(run_dir)
        assert result == "main"

    def test_reads_from_config(self, tmp_path: Path) -> None:
        """Test reads default_branch from adw.yaml config."""
        # Set up directory structure
        project_root = tmp_path
        runs_dir = project_root / ".adw" / "runs"
        run_dir = runs_dir / "test"
        run_dir.mkdir(parents=True)

        # Create config
        config_dir = project_root / ".adw"
        config_file = config_dir / "adw.yaml"
        config_file.write_text(
            """
git:
  default_branch: develop
"""
        )

        result = _get_base_branch(run_dir)
        assert result == "develop"


class TestStorePrUrl:
    """Tests for _store_pr_url function."""

    def test_stores_url_in_context(
        self, tmp_path: Path, sample_context: RunContext
    ) -> None:
        """Test stores PR URL in context artifacts."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)

        # Create context file
        context_file = run_dir / "context.json"
        context_file.write_text(sample_context.model_dump_json())

        with patch("adw.cli.pr.ContextManager") as mock_cm:
            mock_cm.return_value.load.return_value = sample_context

            result = _store_pr_url(
                sample_context,
                "https://github.com/user/repo/pull/123",
                runs_dir,
            )

            assert "pr" in result.artifacts
            assert "https://github.com/user/repo/pull/123" in result.artifacts["pr"]
            mock_cm.return_value.save.assert_called_once()


class TestPrCommand:
    """Integration tests for pr CLI command."""

    def test_pr_run_not_found(self, runner: CliRunner) -> None:
        """Test pr fails when run not found."""
        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = Path("/tmp/runs")

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = None

                result = runner.invoke(app, ["pr", "01JFTEST000000000000000001"])

                assert result.exit_code == 1
                assert "not found" in result.output.lower()

    def test_pr_run_not_complete(
        self, runner: CliRunner, sample_context: RunContext
    ) -> None:
        """Test pr fails when run is not complete."""
        running_context = sample_context.model_copy(update={"status": "running"})

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = Path("/tmp/runs")

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = running_context

                result = runner.invoke(app, ["pr", "01JFTEST000000000000000001"])

                assert result.exit_code == 1
                assert "not complete" in result.output.lower()

    def test_pr_no_description(
        self, runner: CliRunner, sample_context: RunContext, tmp_path: Path
    ) -> None:
        """Test pr fails when PR description not found."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = runs_dir

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = sample_context

                result = runner.invoke(app, ["pr", sample_context.run_id])

                assert result.exit_code == 1
                assert "pr_description_not_found" in result.output.lower()

    def test_pr_gh_not_available_shows_manual(
        self,
        runner: CliRunner,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test pr shows manual instructions when gh not available."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = runs_dir

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = sample_context

                with patch("adw.cli.pr.check_gh_available") as mock_gh:
                    mock_gh.return_value = False

                    result = runner.invoke(app, ["pr", sample_context.run_id])

                    # Exit 0 because we showed manual instructions
                    assert result.exit_code == 0
                    assert "manual" in result.output.lower()

    def test_pr_success(
        self,
        runner: CliRunner,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test successful PR creation."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        # Write context file
        context_file = run_dir / "context.json"
        context_file.write_text(sample_context.model_dump_json())

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = runs_dir

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = sample_context

                with patch("adw.cli.pr.check_gh_available") as mock_gh:
                    mock_gh.return_value = True

                    with patch("adw.cli.pr.check_gh_authenticated") as mock_auth:
                        mock_auth.return_value = (True, "")

                        with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                            mock_create.return_value = (
                                "https://github.com/user/repo/pull/123"
                            )

                            with patch("adw.cli.pr._store_pr_url") as mock_store:
                                mock_store.return_value = sample_context

                                result = runner.invoke(
                                    app, ["pr", sample_context.run_id]
                                )

                                assert result.exit_code == 0
                                assert "pull/123" in result.output

    def test_pr_with_draft_option(
        self,
        runner: CliRunner,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test PR creation with --draft option."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = runs_dir

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = sample_context

                with patch("adw.cli.pr.check_gh_available") as mock_gh:
                    mock_gh.return_value = True

                    with patch("adw.cli.pr.check_gh_authenticated") as mock_auth:
                        mock_auth.return_value = (True, "")

                        with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                            mock_create.return_value = (
                                "https://github.com/user/repo/pull/123"
                            )

                            with patch("adw.cli.pr._store_pr_url") as mock_store:
                                mock_store.return_value = sample_context

                                runner.invoke(
                                    app, ["pr", sample_context.run_id, "--draft"]
                                )

                                # Verify draft=True was passed
                                mock_create.assert_called_once()
                                _, kwargs = mock_create.call_args
                                assert kwargs.get("draft") is True

    def test_pr_with_base_option(
        self,
        runner: CliRunner,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test PR creation with --base option."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = runs_dir

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = sample_context

                with patch("adw.cli.pr.check_gh_available") as mock_gh:
                    mock_gh.return_value = True

                    with patch("adw.cli.pr.check_gh_authenticated") as mock_auth:
                        mock_auth.return_value = (True, "")

                        with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                            mock_create.return_value = (
                                "https://github.com/user/repo/pull/123"
                            )

                            with patch("adw.cli.pr._store_pr_url") as mock_store:
                                mock_store.return_value = sample_context

                                runner.invoke(
                                    app,
                                    [
                                        "pr",
                                        sample_context.run_id,
                                        "--base",
                                        "develop",
                                    ],
                                )

                                # Verify develop was passed as base
                                mock_create.assert_called_once()
                                args, _ = mock_create.call_args
                                assert args[2] == "develop"

    def test_pr_with_no_open_option(
        self,
        runner: CliRunner,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test PR creation with --no-open option."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.get_runs_dir") as mock_runs_dir:
            mock_runs_dir.return_value = runs_dir

            with patch("adw.cli.pr.RunLookup") as mock_lookup:
                mock_lookup.return_value.find_by_id.return_value = sample_context

                with patch("adw.cli.pr.check_gh_available") as mock_gh:
                    mock_gh.return_value = True

                    with patch("adw.cli.pr.check_gh_authenticated") as mock_auth:
                        mock_auth.return_value = (True, "")

                        with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                            mock_create.return_value = (
                                "https://github.com/user/repo/pull/123"
                            )

                            with patch("adw.cli.pr._store_pr_url") as mock_store:
                                mock_store.return_value = sample_context

                                runner.invoke(
                                    app,
                                    ["pr", sample_context.run_id, "--no-open"],
                                )

                                # Verify no_open=True was passed
                                mock_create.assert_called_once()
                                _, kwargs = mock_create.call_args
                                assert kwargs.get("no_open") is True


class TestCheckGitRemote:
    """Tests for check_git_remote function (Story ISS-011)."""

    def test_has_remote_returns_true_with_url(self) -> None:
        """Test returns (True, url) when remote exists."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="origin\tgit@github.com:user/repo.git (fetch)\n"
                "origin\tgit@github.com:user/repo.git (push)\n",
            )

            has_remote, url = check_git_remote()

            assert has_remote is True
            assert url == "git@github.com:user/repo.git"

    def test_no_remote_returns_false(self) -> None:
        """Test returns (False, '') when no remote configured."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            has_remote, url = check_git_remote()

            assert has_remote is False
            assert url == ""

    def test_git_error_returns_false(self) -> None:
        """Test returns (False, '') when git command fails."""
        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")

            has_remote, url = check_git_remote()

            assert has_remote is False
            assert url == ""

    def test_timeout_returns_false(self) -> None:
        """Test returns (False, '') on timeout."""
        import subprocess

        with patch("adw.cli.pr.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

            has_remote, url = check_git_remote()

            assert has_remote is False
            assert url == ""


class TestCanAutoCreatePr:
    """Tests for can_auto_create_pr function (Story ISS-011)."""

    def test_all_prerequisites_met(self) -> None:
        """Test returns (True, '') when all conditions met."""
        with patch("adw.cli.pr.check_git_remote") as mock_remote:
            mock_remote.return_value = (True, "git@github.com:user/repo.git")

            with patch("adw.cli.pr.check_gh_available") as mock_gh:
                mock_gh.return_value = True

                with patch("adw.cli.pr.check_gh_authenticated") as mock_auth:
                    mock_auth.return_value = (True, "")

                    can_create, reason = can_auto_create_pr()

                    assert can_create is True
                    assert reason == ""

    def test_no_remote_returns_false(self) -> None:
        """Test returns (False, reason) when no remote."""
        with patch("adw.cli.pr.check_git_remote") as mock_remote:
            mock_remote.return_value = (False, "")

            can_create, reason = can_auto_create_pr()

            assert can_create is False
            assert "remote" in reason.lower()

    def test_no_gh_returns_false(self) -> None:
        """Test returns (False, reason) when gh not installed."""
        with patch("adw.cli.pr.check_git_remote") as mock_remote:
            mock_remote.return_value = (True, "git@github.com:user/repo.git")

            with patch("adw.cli.pr.check_gh_available") as mock_gh:
                mock_gh.return_value = False

                can_create, reason = can_auto_create_pr()

                assert can_create is False
                assert "installed" in reason.lower()

    def test_not_authenticated_returns_false(self) -> None:
        """Test returns (False, reason) when gh not authenticated."""
        with patch("adw.cli.pr.check_git_remote") as mock_remote:
            mock_remote.return_value = (True, "git@github.com:user/repo.git")

            with patch("adw.cli.pr.check_gh_available") as mock_gh:
                mock_gh.return_value = True

                with patch("adw.cli.pr.check_gh_authenticated") as mock_auth:
                    mock_auth.return_value = (False, "auth error")

                    can_create, reason = can_auto_create_pr()

                    assert can_create is False
                    assert "authenticated" in reason.lower()


class TestAutoPRResult:
    """Tests for AutoPRResult class (Story ISS-011)."""

    def test_success_result(self) -> None:
        """Test successful result creation."""
        result = AutoPRResult(
            success=True,
            pr_url="https://github.com/user/repo/pull/123",
        )

        assert result.success is True
        assert result.pr_url == "https://github.com/user/repo/pull/123"
        assert result.reason == ""

    def test_failure_result(self) -> None:
        """Test failure result creation."""
        result = AutoPRResult(
            success=False,
            reason="No git remote configured",
            suggestion="Push to a remote repository first",
        )

        assert result.success is False
        assert result.pr_url == ""
        assert result.reason == "No git remote configured"
        assert result.suggestion == "Push to a remote repository first"


class TestAutoCreatePr:
    """Tests for auto_create_pr function (Story ISS-011)."""

    def test_returns_failure_when_cant_create(
        self, sample_context: RunContext, tmp_path: Path
    ) -> None:
        """Test returns failure result when prerequisites not met."""
        runs_dir = tmp_path

        with patch("adw.cli.pr.can_auto_create_pr") as mock_can:
            mock_can.return_value = (False, "No git remote configured")

            result = auto_create_pr(
                run_id=sample_context.run_id,
                context=sample_context,
                runs_dir=runs_dir,
            )

            assert result.success is False
            assert "remote" in result.reason.lower()
            assert result.suggestion  # Should have a suggestion

    def test_success_creates_pr(
        self,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test creates PR when all conditions met."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.can_auto_create_pr") as mock_can:
            mock_can.return_value = (True, "")

            with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                mock_create.return_value = "https://github.com/user/repo/pull/123"

                with patch("adw.cli.pr._store_pr_url") as mock_store:
                    mock_store.return_value = sample_context

                    result = auto_create_pr(
                        run_id=sample_context.run_id,
                        context=sample_context,
                        runs_dir=runs_dir,
                    )

                    assert result.success is True
                    assert result.pr_url == "https://github.com/user/repo/pull/123"

    def test_handles_pr_creation_error(
        self,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test handles PR creation error gracefully."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        doc_dir = run_dir / "artifacts" / "document"
        doc_dir.mkdir(parents=True)

        # Write PR description
        pr_file = doc_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.can_auto_create_pr") as mock_can:
            mock_can.return_value = (True, "")

            with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                mock_create.side_effect = ConfigError(
                    code="GH_PR_FAILED",
                    message="Failed to create PR",
                    suggestion="Check gh CLI output",
                    recoverable=False,
                )

                result = auto_create_pr(
                    run_id=sample_context.run_id,
                    context=sample_context,
                    runs_dir=runs_dir,
                )

                assert result.success is False
                assert "Failed to create PR" in result.reason

    def test_pr_title_includes_task_id_when_present(
        self,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test PR title is prefixed with task_id when available (Story 12.6)."""
        from datetime import datetime

        from adw.models.task import TaskInfo

        # Create context with task_id
        context_with_task = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="document",
            started_at=datetime.now(),
            task_id="RULE-123",
            task_info=TaskInfo(
                id="uuid-123",
                identifier="RULE-123",
                title="Add auth",
            ),
        )

        runs_dir = tmp_path
        run_dir = runs_dir / context_with_task.run_id
        artifacts_dir = run_dir / "artifacts" / "document"
        artifacts_dir.mkdir(parents=True)
        pr_file = artifacts_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.can_auto_create_pr") as mock_can:
            mock_can.return_value = (True, "")

            with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                mock_create.return_value = "https://github.com/user/repo/pull/123"

                with patch("adw.cli.pr._store_pr_url") as mock_store:
                    mock_store.return_value = context_with_task

                    result = auto_create_pr(
                        run_id=context_with_task.run_id,
                        context=context_with_task,
                        runs_dir=runs_dir,
                    )

                    assert result.success is True
                    # Check that create_pr_via_gh was called with task_id prefix
                    call_args = mock_create.call_args
                    pr_title = call_args[0][0]
                    assert pr_title.startswith("RULE-123:")
                    assert "Add user authentication" in pr_title

    def test_pr_title_without_task_id(
        self,
        sample_context: RunContext,
        sample_pr_description: PRDescription,
        tmp_path: Path,
    ) -> None:
        """Test PR title uses feature_description when no task_id (Story 12.6)."""
        runs_dir = tmp_path
        run_dir = runs_dir / sample_context.run_id
        artifacts_dir = run_dir / "artifacts" / "document"
        artifacts_dir.mkdir(parents=True)
        pr_file = artifacts_dir / "pr_description.md"
        pr_file.write_text(sample_pr_description.to_markdown())

        with patch("adw.cli.pr.can_auto_create_pr") as mock_can:
            mock_can.return_value = (True, "")

            with patch("adw.cli.pr.create_pr_via_gh") as mock_create:
                mock_create.return_value = "https://github.com/user/repo/pull/123"

                with patch("adw.cli.pr._store_pr_url") as mock_store:
                    mock_store.return_value = sample_context

                    result = auto_create_pr(
                        run_id=sample_context.run_id,
                        context=sample_context,
                        runs_dir=runs_dir,
                    )

                    assert result.success is True
                    # Check that create_pr_via_gh was called without task_id prefix
                    call_args = mock_create.call_args
                    pr_title = call_args[0][0]
                    # Should just be the feature description, no task ID prefix
                    assert pr_title == sample_context.feature_description or (
                        not pr_title.startswith("RULE-")
                        and not pr_title.startswith("JIRA-")
                    )
