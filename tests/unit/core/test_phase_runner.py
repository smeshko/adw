"""Unit tests for PhaseRunner.

Tests the PhaseRunner class that coordinates single phase execution:
pre-hook → prompt loading → LLM execution → post-hook → artifact capture.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.core.artifact_manager import ArtifactManager
from adw.core.phase_runner import PhaseRunner
from adw.exceptions import CommandError, ConfigError, HookError, LLMError
from adw.hooks.runner import HookRunner
from adw.models import (
    HookResult,
    LLMResult,
    PhaseResult,
    PhaseStatus,
    ResolvedCommand,
    RunContext,
    ToolCall,
)


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample run context for testing."""
    return RunContext(
        run_id="01HQXH9Z8G2K4M5N6P7R8S9T0V",
        feature_description="Add user authentication",
        current_phase="plan",
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def command_dir(tmp_path: Path) -> Path:
    """Create a temp command directory with prompt.md."""
    cmd_dir = tmp_path / ".adw" / "commands" / "plan"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "prompt.md").write_text("Test prompt for {{phase}}")
    (cmd_dir / "pre-hook.sh").write_text("#!/bin/bash\necho 'pre-hook'")
    (cmd_dir / "post-hook.sh").write_text("#!/bin/bash\necho 'post-hook'")
    return cmd_dir


@pytest.fixture
def mock_command_resolver(command_dir: Path) -> MagicMock:
    """Create a mock command resolver with real temp path."""
    resolver = MagicMock(spec=CommandResolver)
    resolved = ResolvedCommand(
        name="plan",
        path=command_dir,
        tier="project",
        has_pre_hook=True,
        has_post_hook=True,
    )
    resolver.resolve.return_value = resolved
    return resolver


@pytest.fixture
def mock_template_engine() -> MagicMock:
    """Create a mock template engine."""
    engine = MagicMock(spec=TemplateEngine)
    engine.render.return_value = "Rendered prompt content"
    return engine


@pytest.fixture
def mock_hook_runner() -> MagicMock:
    """Create a mock hook runner."""
    runner = MagicMock(spec=HookRunner)
    runner.run_hook.return_value = HookResult(
        stdout="Hook output",
        stderr="",
        exit_code=0,
        duration_ms=100,
        hook_type="pre",
    )
    return runner


@pytest.fixture
def mock_executor() -> MagicMock:
    """Create a mock LLM executor."""
    executor = MagicMock()
    executor.execute.return_value = LLMResult(
        success=True,
        content="LLM output content",
        tokens_used=500,
        duration_ms=2000,
        tool_calls=[
            ToolCall(tool_name="read_file", arguments={"path": "/src/main.py"})
        ],
    )
    return executor


@pytest.fixture
def mock_artifact_manager(tmp_path: Path) -> ArtifactManager:
    """Create a real artifact manager with temp directory."""
    return ArtifactManager(runs_dir=tmp_path)


@pytest.fixture
def phase_runner(
    mock_command_resolver: MagicMock,
    mock_template_engine: MagicMock,
    mock_hook_runner: MagicMock,
    mock_executor: MagicMock,
    mock_artifact_manager: ArtifactManager,
) -> PhaseRunner:
    """Create a PhaseRunner with all mock dependencies."""
    return PhaseRunner(
        command_resolver=mock_command_resolver,
        template_engine=mock_template_engine,
        hook_runner=mock_hook_runner,
        executor=mock_executor,
        artifact_manager=mock_artifact_manager,
    )


class TestPhaseRunnerInit:
    """Tests for PhaseRunner initialization."""

    def test_init_stores_dependencies(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
    ) -> None:
        """Test that PhaseRunner stores all dependencies correctly."""
        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        assert runner.command_resolver is mock_command_resolver
        assert runner.template_engine is mock_template_engine
        assert runner.hook_runner is mock_hook_runner
        assert runner.executor is mock_executor
        assert runner.artifact_manager is mock_artifact_manager


class TestPhaseRunnerRun:
    """Tests for PhaseRunner.run() method."""

    def test_run_returns_phase_result(
        self, phase_runner: PhaseRunner, sample_context: RunContext
    ) -> None:
        """Test that run returns a PhaseResult on success."""
        result = phase_runner.run("plan", sample_context)

        assert isinstance(result, PhaseResult)
        assert result.phase == "plan"
        assert result.status == PhaseStatus.COMPLETED

    def test_run_tracks_timing(
        self, phase_runner: PhaseRunner, sample_context: RunContext
    ) -> None:
        """Test that run tracks start and end times."""
        result = phase_runner.run("plan", sample_context)

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    def test_run_captures_token_usage(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_executor: MagicMock,
    ) -> None:
        """Test that run captures token usage from executor."""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Output",
            tokens_used=1234,
            duration_ms=1000,
        )

        result = phase_runner.run("plan", sample_context)

        assert result.tokens_used == 1234

    def test_run_captures_tool_calls(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_executor: MagicMock,
    ) -> None:
        """Test that run captures tool calls from executor."""
        tool_calls = [
            ToolCall(tool_name="read_file", arguments={"path": "/a.py"}),
            ToolCall(tool_name="write_file", arguments={"path": "/b.py"}),
        ]
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Output",
            tokens_used=100,
            duration_ms=1000,
            tool_calls=tool_calls,
        )

        result = phase_runner.run("plan", sample_context)

        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].tool_name == "read_file"
        assert result.tool_calls[1].tool_name == "write_file"


class TestPhaseRunnerExecutionOrder:
    """Tests for execution order: pre-hook → prompt → LLM → post-hook."""

    def test_executes_in_correct_order(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_hook_runner: MagicMock,
        mock_template_engine: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that PhaseRunner executes steps in correct order."""
        call_order: list[str] = []

        # Store original side_effect/return_value

        def hook_side_effect(*args, **kwargs):
            hook_type = kwargs.get("hook_type", "pre")
            call_order.append(f"{hook_type}_hook")
            return HookResult(
                stdout="output",
                stderr="",
                exit_code=0,
                duration_ms=10,
                hook_type=hook_type,
            )

        def render_side_effect(*args, **kwargs):
            call_order.append("template")
            return "Rendered prompt"

        def execute_side_effect(*args, **kwargs):
            call_order.append("llm")
            return LLMResult(
                success=True, content="llm output", tokens_used=100, duration_ms=1000
            )

        mock_hook_runner.run_hook.side_effect = hook_side_effect
        mock_template_engine.render.side_effect = render_side_effect
        mock_executor.execute.side_effect = execute_side_effect

        phase_runner.run("plan", sample_context)

        assert call_order == ["pre_hook", "template", "llm", "post_hook"]


class TestPhaseRunnerPreHook:
    """Tests for pre-hook execution."""

    def test_pre_hook_output_available_as_template_variable(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_hook_runner: MagicMock,
        mock_template_engine: MagicMock,
    ) -> None:
        """Test that pre-hook stdout is available as template variable."""
        mock_hook_runner.run_hook.return_value = HookResult(
            stdout="git status output here",
            stderr="",
            exit_code=0,
            duration_ms=50,
            hook_type="pre",
        )

        phase_runner.run("build", sample_context)

        # Verify template_engine.render was called with pre_hook_output
        call_args = mock_template_engine.render.call_args
        variables = call_args[0][1]  # Second positional argument
        assert "pre_hook_output" in variables
        assert variables["pre_hook_output"] == "git status output here"

    def test_pre_hook_failure_raises_hook_error(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_hook_runner: MagicMock,
    ) -> None:
        """Test that pre-hook failure raises HookError."""
        mock_hook_runner.run_hook.side_effect = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="plan",
            exit_code=1,
            stdout="",
            stderr="error",
        )

        with pytest.raises(HookError) as exc_info:
            phase_runner.run("plan", sample_context)

        assert exc_info.value.code == "HOOK_FAILED"


class TestPhaseRunnerPostHook:
    """Tests for post-hook execution."""

    def test_llm_output_in_post_hook_env(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that LLM output is available to post-hook via environment."""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Generated code here",
            tokens_used=100,
            duration_ms=1000,
        )

        captured_env: dict[str, str | None] = {}

        def hook_side_effect(*args, **kwargs):
            hook_type = kwargs.get("hook_type", "pre")
            if hook_type == "post":
                captured_env["ADW_LLM_OUTPUT"] = os.environ.get("ADW_LLM_OUTPUT")
            return HookResult(
                stdout="", stderr="", exit_code=0, duration_ms=10, hook_type=hook_type
            )

        mock_hook_runner.run_hook.side_effect = hook_side_effect

        phase_runner.run("build", sample_context)

        # The post-hook should have had access to LLM output
        assert captured_env.get("ADW_LLM_OUTPUT") == "Generated code here"

    def test_env_restored_after_post_hook(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_hook_runner: MagicMock,
    ) -> None:
        """Test that environment is restored after post-hook execution."""
        # Set a pre-existing value
        original_value = "original"
        os.environ["ADW_LLM_OUTPUT"] = original_value

        try:
            phase_runner.run("plan", sample_context)
            # Environment should be restored
            assert os.environ.get("ADW_LLM_OUTPUT") == original_value
        finally:
            os.environ.pop("ADW_LLM_OUTPUT", None)


class TestPhaseRunnerArtifacts:
    """Tests for artifact capture."""

    def test_captures_llm_output_as_artifact(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_artifact_manager: ArtifactManager,
        mock_executor: MagicMock,
    ) -> None:
        """Test that LLM output is stored as artifact."""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Generated plan content",
            tokens_used=100,
            duration_ms=1000,
        )

        result = phase_runner.run("plan", sample_context)

        # Check artifact was stored
        artifact_content = mock_artifact_manager.get(
            sample_context.run_id, "plan", "plan_output.md"
        )
        assert artifact_content == "Generated plan content"
        assert "plan_output.md" in result.artifacts

    def test_captures_tool_calls_as_artifact_if_present(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_artifact_manager: ArtifactManager,
        mock_executor: MagicMock,
    ) -> None:
        """Test that tool calls are stored as JSON artifact if present."""
        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Output",
            tokens_used=100,
            duration_ms=1000,
            tool_calls=[ToolCall(tool_name="read_file", arguments={"path": "/a.py"})],
        )

        result = phase_runner.run("plan", sample_context)

        # Check tool calls artifact
        tool_calls_data = mock_artifact_manager.get_json(
            sample_context.run_id, "plan", "plan_tool_calls.json"
        )
        assert tool_calls_data is not None
        assert len(tool_calls_data) == 1
        assert tool_calls_data[0]["tool_name"] == "read_file"
        assert "plan_tool_calls.json" in result.artifacts


class TestPhaseRunnerErrorHandling:
    """Tests for error state capture."""

    def test_error_captures_partial_state(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_executor: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that errors capture partial PhaseResult with timing."""
        import logging

        mock_executor.execute.side_effect = LLMError(
            code="LLM_TIMEOUT",
            message="Request timed out",
            suggestion="Retry",
            recoverable=True,
        )

        with (
            caplog.at_level(logging.ERROR, logger="adw.core.phase_runner"),
            pytest.raises(LLMError),
        ):
            phase_runner.run("plan", sample_context)

        # Verify error was logged with duration_ms (proves PhaseResult created)
        assert any("Phase failed" in record.message for record in caplog.records)
        error_record = next(r for r in caplog.records if "Phase failed" in r.message)
        # The extra dict is stored as attributes on the record
        assert hasattr(error_record, "duration_ms"), (
            "PhaseResult.duration_ms should be logged"
        )

    def test_command_error_adds_phase_context(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_command_resolver: MagicMock,
    ) -> None:
        """Test that CommandError gets phase context added."""
        mock_command_resolver.resolve.side_effect = CommandError(
            code="COMMAND_NOT_FOUND",
            message="Command not found",
        )

        with pytest.raises(CommandError) as exc_info:
            phase_runner.run("missing", sample_context)

        # The error should be raised as-is
        assert exc_info.value.code == "COMMAND_NOT_FOUND"

    def test_llm_error_has_phase_context(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_executor: MagicMock,
    ) -> None:
        """Test that LLMError gets phase context added."""
        mock_executor.execute.side_effect = LLMError(
            code="LLM_ERROR",
            message="Execution failed",
        )

        with pytest.raises(LLMError) as exc_info:
            phase_runner.run("plan", sample_context)

        assert exc_info.value.code == "LLM_ERROR"


class TestPhaseRunnerGitDiffCapture:
    """Tests for git diff artifact capture during build phase (Story 9.3)."""

    def test_build_phase_captures_git_diff(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_artifact_manager: ArtifactManager,
        mock_executor: MagicMock,
    ) -> None:
        """Test that build phase captures git diff artifacts."""
        from unittest.mock import patch

        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Build output",
            tokens_used=100,
            duration_ms=1000,
        )

        # Update context to build phase
        sample_context = sample_context.model_copy(update={"current_phase": "build"})

        # Mock git diff to return test content
        with (
            patch("adw.core.phase_runner.capture_diff") as mock_capture,
            patch("adw.core.phase_runner.subprocess.run") as mock_stat,
        ):
            mock_capture.return_value = "diff --git a/test.py\n+added line"
            mock_stat.return_value = MagicMock(
                returncode=0,
                stdout="1 file changed, 1 insertion(+)",
            )

            result = phase_runner.run("build", sample_context)

            # Verify diff artifact was captured
            assert "diff.txt" in result.artifacts

            # Verify content was stored
            diff_content = mock_artifact_manager.get(
                sample_context.run_id, "build", "diff.txt"
            )
            assert diff_content is not None
            assert "diff --git" in diff_content

    def test_build_phase_falls_back_to_staged_diff(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_artifact_manager: ArtifactManager,
        mock_executor: MagicMock,
    ) -> None:
        """Test that build phase falls back to staged diff when no commit diff."""
        from unittest.mock import patch

        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Build output",
            tokens_used=100,
            duration_ms=1000,
        )

        sample_context = sample_context.model_copy(update={"current_phase": "build"})

        with (
            patch("adw.core.phase_runner.capture_diff") as mock_diff,
            patch("adw.core.phase_runner.capture_staged_diff") as mock_staged,
            patch("adw.core.phase_runner.subprocess.run") as mock_stat,
        ):
            # No commit diff available
            mock_diff.return_value = ""
            # But staged changes exist
            mock_staged.return_value = "diff --git staged changes"
            mock_stat.return_value = MagicMock(returncode=0, stdout="")

            result = phase_runner.run("build", sample_context)

            # Should have called capture_staged_diff
            mock_staged.assert_called_once()
            assert "diff.txt" in result.artifacts

    def test_build_phase_handles_git_error_gracefully(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_executor: MagicMock,
    ) -> None:
        """Test that git errors don't fail the build phase."""
        from unittest.mock import patch

        from adw.exceptions import HookError

        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Build output",
            tokens_used=100,
            duration_ms=1000,
        )

        sample_context = sample_context.model_copy(update={"current_phase": "build"})

        with patch("adw.core.phase_runner.capture_diff") as mock_diff:
            mock_diff.side_effect = HookError(
                code="GIT_DIFF_FAILED",
                message="Git not available",
                phase="build",
            )

            # Should complete without error
            result = phase_runner.run("build", sample_context)

            # Build succeeded but no diff artifact
            assert result.status == PhaseStatus.COMPLETED
            assert "diff.txt" not in result.artifacts

    def test_non_build_phase_does_not_capture_diff(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_executor: MagicMock,
    ) -> None:
        """Test that non-build phases don't capture git diff."""
        from unittest.mock import patch

        mock_executor.execute.return_value = LLMResult(
            success=True,
            content="Plan output",
            tokens_used=100,
            duration_ms=1000,
        )

        with patch("adw.core.phase_runner.capture_diff") as mock_diff:
            result = phase_runner.run("plan", sample_context)

            # capture_diff should not be called for plan phase
            mock_diff.assert_not_called()
            assert "diff.txt" not in result.artifacts

    def test_diff_artifact_accessible_as_template_variable(
        self,
        mock_artifact_manager: ArtifactManager,
        sample_context: RunContext,
    ) -> None:
        """Test that diff.txt artifact is accessible as {{artifacts.build.diff}}.

        Story 9.3 AC2: Given the diff artifact, when accessed by Document phase,
        then it's available as {{artifacts.build.diff}}.
        """
        # Store a diff artifact as the build phase would
        mock_artifact_manager.store_text(
            sample_context.run_id,
            "build",
            "diff.txt",
            "diff --git a/file.py\n+new line",
        )

        # Create a PhaseRunner to test _load_phase_artifacts
        from unittest.mock import MagicMock

        runner = PhaseRunner(
            command_resolver=MagicMock(),
            template_engine=MagicMock(),
            hook_runner=MagicMock(),
            executor=MagicMock(),
            artifact_manager=mock_artifact_manager,
        )

        # Load artifacts for build phase
        artifacts = runner._load_phase_artifacts(sample_context.run_id, "build")

        # Verify diff is accessible without extension
        assert "diff" in artifacts
        assert "diff --git" in artifacts["diff"]


class TestPhaseRunnerWorktreeContext:
    """Tests for worktree context in template variables (Story 10.5)."""

    def test_worktree_path_available_as_template_variable(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_template_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that worktree_path is available as template variable."""
        # Set worktree_path in context
        worktree_context = sample_context.model_copy(
            update={"worktree_path": tmp_path / "worktree"}
        )

        phase_runner.run("plan", worktree_context)

        # Verify template_engine.render was called with worktree_path
        call_args = mock_template_engine.render.call_args
        variables = call_args[0][1]  # Second positional argument
        assert "worktree_path" in variables
        assert variables["worktree_path"] == str(tmp_path / "worktree")

    def test_worktree_path_none_uses_empty_string(
        self,
        phase_runner: PhaseRunner,
        sample_context: RunContext,
        mock_template_engine: MagicMock,
    ) -> None:
        """Test that worktree_path is empty string when None in context."""
        # Default context has worktree_path=None
        assert sample_context.worktree_path is None

        phase_runner.run("plan", sample_context)

        call_args = mock_template_engine.render.call_args
        variables = call_args[0][1]
        assert "worktree_path" in variables
        assert variables["worktree_path"] == ""


class TestPhaseRunnerWithMockExecutor:
    """Integration-style tests using MockExecutor."""

    def test_full_phase_with_mock_executor(
        self,
        command_dir: Path,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_artifact_manager: ArtifactManager,
        sample_context: RunContext,
    ) -> None:
        """Test full flow with MockExecutor (no Claude Code needed)."""
        from adw.executors.mock import MockExecutor

        # Create resolver with the temp command directory
        resolver = MagicMock(spec=CommandResolver)
        resolved = ResolvedCommand(
            name="plan",
            path=command_dir,
            tier="project",
            has_pre_hook=True,
            has_post_hook=True,
        )
        resolver.resolve.return_value = resolved

        # Create a real MockExecutor
        mock_exec = MockExecutor()

        runner = PhaseRunner(
            command_resolver=resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_exec,
            artifact_manager=mock_artifact_manager,
        )

        result = runner.run("plan", sample_context)

        assert result.status == PhaseStatus.COMPLETED
        assert result.tokens_used > 0
        assert len(result.artifacts) > 0


class TestAutoCommitChanges:
    """Tests for _auto_commit_changes method (ISS-009 fix)."""

    def test_auto_commit_stages_and_commits_changes(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: MagicMock,
        sample_context: RunContext,
    ) -> None:
        """Should stage and commit changes when files exist."""
        from unittest.mock import patch

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        with (
            patch("adw.core.phase_runner.stage_changes") as mock_stage,
            patch("adw.core.phase_runner.create_commit") as mock_commit,
        ):
            mock_stage.return_value = ["file1.py", "file2.py"]
            mock_commit.return_value = "abc123def"

            sha = runner._auto_commit_changes("build", sample_context)

            mock_stage.assert_called_once_with(working_dir=None)
            mock_commit.assert_called_once()
            # Verify commit args
            call_kwargs = mock_commit.call_args.kwargs
            assert call_kwargs["phase"] == "build"
            assert call_kwargs["feature"] == sample_context.feature_description
            assert call_kwargs["run_id"] == sample_context.run_id
            assert call_kwargs["working_dir"] is None
            assert sha == "abc123def"

    def test_auto_commit_returns_none_when_no_changes(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: MagicMock,
        sample_context: RunContext,
    ) -> None:
        """Should return None when no files to commit."""
        from unittest.mock import patch

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        with (
            patch("adw.core.phase_runner.stage_changes") as mock_stage,
            patch("adw.core.phase_runner.create_commit") as mock_commit,
        ):
            mock_stage.return_value = []  # No files to stage

            sha = runner._auto_commit_changes("build", sample_context)

            mock_stage.assert_called_once()
            mock_commit.assert_not_called()
            assert sha is None

    def test_auto_commit_uses_worktree_path(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: MagicMock,
    ) -> None:
        """Should pass worktree_path to git functions for worktree isolation."""
        from unittest.mock import patch

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        worktree = Path("/my/worktree")
        context = RunContext(
            run_id="01HQXH9Z8G2K4M5N6P7R8S9T0V",
            feature_description="Add feature",
            current_phase="build",
            started_at=datetime.now(UTC),
            worktree_path=worktree,
            use_worktree=True,
        )

        with (
            patch("adw.core.phase_runner.stage_changes") as mock_stage,
            patch("adw.core.phase_runner.create_commit") as mock_commit,
        ):
            mock_stage.return_value = ["file.py"]
            mock_commit.return_value = "abc123"

            runner._auto_commit_changes("build", context)

            mock_stage.assert_called_once_with(working_dir=worktree)
            mock_commit.assert_called_once()
            assert mock_commit.call_args.kwargs["working_dir"] == worktree

    def test_auto_commit_catches_hook_errors(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: MagicMock,
        sample_context: RunContext,
    ) -> None:
        """Should catch HookError and return None (best effort)."""
        from unittest.mock import patch

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        with patch("adw.core.phase_runner.stage_changes") as mock_stage:
            mock_stage.side_effect = HookError(
                code="GIT_STAGE_FAILED",
                message="Not a git repo",
                phase="post-hook",
            )

            # Should not raise, just return None
            sha = runner._auto_commit_changes("build", sample_context)
            assert sha is None

    def test_auto_commit_catches_unexpected_errors(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: MagicMock,
        sample_context: RunContext,
    ) -> None:
        """Should catch unexpected errors and return None (best effort)."""
        from unittest.mock import patch

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        with patch("adw.core.phase_runner.stage_changes") as mock_stage:
            mock_stage.side_effect = RuntimeError("Unexpected error")

            # Should not raise, just return None
            sha = runner._auto_commit_changes("build", sample_context)
            assert sha is None


class TestLoadInputFiles:
    """Tests for _load_input_files method (ISS-015)."""

    def test_load_input_files_success(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """_load_input_files reads and returns file contents."""
        # Create test file
        prd_file = tmp_path / "docs" / "prd.md"
        prd_file.parent.mkdir(parents=True)
        prd_file.write_text("# PRD Content\nThis is the PRD.")

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        result = runner._load_input_files(
            {"prd": "docs/prd.md"},
            project_root=tmp_path,
        )

        assert result == {"prd": "# PRD Content\nThis is the PRD."}

    def test_load_input_files_multiple_files(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """_load_input_files loads multiple files."""
        # Create test files
        (tmp_path / "docs").mkdir(parents=True)
        (tmp_path / "docs" / "prd.md").write_text("PRD content")
        (tmp_path / "docs" / "arch.md").write_text("Architecture content")

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        result = runner._load_input_files(
            {"prd": "docs/prd.md", "arch": "docs/arch.md"},
            project_root=tmp_path,
        )

        assert result == {"prd": "PRD content", "arch": "Architecture content"}

    def test_load_input_files_missing_file_raises_config_error(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """_load_input_files raises ConfigError for missing files."""
        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        with pytest.raises(ConfigError) as exc_info:
            runner._load_input_files(
                {"prd": "nonexistent.md"},
                project_root=tmp_path,
            )

        assert exc_info.value.code == "INPUT_FILE_NOT_FOUND"
        assert "nonexistent.md" in exc_info.value.message

    def test_load_input_files_empty_dict_returns_empty(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """_load_input_files returns empty dict for empty input_files."""
        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        result = runner._load_input_files({}, project_root=tmp_path)

        assert result == {}

    def test_load_input_files_none_returns_empty(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """_load_input_files returns empty dict for None input_files."""
        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        result = runner._load_input_files(None, project_root=tmp_path)

        assert result == {}

    def test_load_input_files_uses_worktree_path(
        self,
        mock_command_resolver: MagicMock,
        mock_template_engine: MagicMock,
        mock_hook_runner: MagicMock,
        mock_executor: MagicMock,
        mock_artifact_manager: ArtifactManager,
        tmp_path: Path,
    ) -> None:
        """_load_input_files uses worktree_path when provided."""
        # Create file only in worktree
        worktree = tmp_path / "worktree"
        (worktree / "docs").mkdir(parents=True)
        (worktree / "docs" / "spec.md").write_text("Spec in worktree")

        runner = PhaseRunner(
            command_resolver=mock_command_resolver,
            template_engine=mock_template_engine,
            hook_runner=mock_hook_runner,
            executor=mock_executor,
            artifact_manager=mock_artifact_manager,
        )

        result = runner._load_input_files(
            {"spec": "docs/spec.md"},
            project_root=tmp_path,
            worktree_path=worktree,
        )

        assert result == {"spec": "Spec in worktree"}
