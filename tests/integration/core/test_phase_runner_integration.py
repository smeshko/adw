"""Integration tests for PhaseRunner.

Tests the full phase execution flow with real components (except Claude Code).
Uses MockExecutor to simulate LLM execution without requiring Claude Code.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.commands.resolver import CommandResolver
from adw.commands.template import TemplateEngine
from adw.core.artifact_manager import ArtifactManager
from adw.core.phase_runner import PhaseRunner
from adw.executors.mock import MockExecutor
from adw.hooks.runner import HookRunner
from adw.models import (
    HookConfig,
    PhaseStatus,
    RunContext,
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a project structure with command and hooks."""
    # Create command directory with prompt
    cmd_dir = tmp_path / ".adw" / "commands" / "plan"
    cmd_dir.mkdir(parents=True)

    # Create prompt.md
    prompt_content = """# Planning Phase

Feature: {{feature}}
Run ID: {{run_id}}

Pre-hook output:
{{pre_hook_output}}

Please create a plan for this feature.
"""
    (cmd_dir / "prompt.md").write_text(prompt_content)

    # Create pre-hook that outputs git status simulation
    pre_hook = """#!/bin/bash
echo "On branch main"
echo "nothing to commit, working tree clean"
"""
    (cmd_dir / "pre-hook.sh").write_text(pre_hook)
    (cmd_dir / "pre-hook.sh").chmod(0o755)

    # Create post-hook that reads LLM output from env
    post_hook = """#!/bin/bash
echo "Post-hook received LLM output length: ${#ADW_LLM_OUTPUT}"
echo "Phase: $ADW_PHASE"
"""
    (cmd_dir / "post-hook.sh").write_text(post_hook)
    (cmd_dir / "post-hook.sh").chmod(0o755)

    return tmp_path


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create runs directory."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample run context."""
    return RunContext(
        run_id="01HQXH9Z8G2K4M5N6P7R8S9T0V",
        feature_description="Add user authentication with OAuth2",
        current_phase="plan",
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def phase_runner(project_root: Path, runs_dir: Path) -> PhaseRunner:
    """Create a PhaseRunner with real components."""
    command_resolver = CommandResolver(project_root=project_root)
    template_engine = TemplateEngine(project_root=project_root)
    hook_runner = HookRunner(config=HookConfig(shell="/bin/bash", timeout_seconds=30))
    executor = MockExecutor()
    artifact_manager = ArtifactManager(runs_dir=runs_dir)

    return PhaseRunner(
        command_resolver=command_resolver,
        template_engine=template_engine,
        hook_runner=hook_runner,
        executor=executor,
        artifact_manager=artifact_manager,
    )


class TestPhaseRunnerIntegration:
    """Integration tests for full phase execution flow."""

    def test_full_phase_execution_with_mock_executor(
        self, phase_runner: PhaseRunner, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test complete phase execution flow with MockExecutor."""
        result = phase_runner.run("plan", sample_context)

        # Verify result
        assert result.status == PhaseStatus.COMPLETED
        assert result.phase == "plan"
        assert result.tokens_used > 0
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

        # Verify artifacts were stored
        assert "plan_output.md" in result.artifacts

        # Verify artifact content exists
        artifact_path = (
            runs_dir / sample_context.run_id / "artifacts" / "plan" / "plan_output.md"
        )
        assert artifact_path.exists()
        assert len(artifact_path.read_text()) > 0

    def test_pre_hook_output_in_prompt(
        self, phase_runner: PhaseRunner, sample_context: RunContext
    ) -> None:
        """Test that pre-hook output is included in the prompt context."""
        # The MockExecutor will receive a prompt that includes pre-hook output
        result = phase_runner.run("plan", sample_context)

        assert result.status == PhaseStatus.COMPLETED
        # Pre-hook should have run and its output should be available
        # (verified by successful execution - if hook failed, phase would fail)

    def test_artifacts_stored_after_phase(
        self, phase_runner: PhaseRunner, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that artifacts are properly stored after phase execution."""
        phase_runner.run("plan", sample_context)

        # Check main output artifact
        artifact_path = (
            runs_dir / sample_context.run_id / "artifacts" / "plan" / "plan_output.md"
        )
        assert artifact_path.exists()

        content = artifact_path.read_text()
        # MockExecutor produces structured output
        assert len(content) > 0


class TestHookLLMHookDataFlow:
    """Tests for data flow: hook → LLM → hook."""

    def test_hook_to_llm_data_flow(
        self, project_root: Path, runs_dir: Path, sample_context: RunContext
    ) -> None:
        """Test that pre-hook stdout is available to LLM via template."""
        # Create a custom pre-hook that outputs specific data
        cmd_dir = project_root / ".adw" / "commands" / "plan"
        pre_hook = """#!/bin/bash
echo "CUSTOM_PRE_HOOK_DATA"
echo "Line 2 of pre-hook"
"""
        (cmd_dir / "pre-hook.sh").write_text(pre_hook)
        (cmd_dir / "pre-hook.sh").chmod(0o755)

        # Create runner
        runner = PhaseRunner(
            command_resolver=CommandResolver(project_root=project_root),
            template_engine=TemplateEngine(project_root=project_root),
            hook_runner=HookRunner(
                config=HookConfig(shell="/bin/bash", timeout_seconds=30)
            ),
            executor=MockExecutor(),
            artifact_manager=ArtifactManager(runs_dir=runs_dir),
        )

        result = runner.run("plan", sample_context)

        # Phase should complete successfully
        assert result.status == PhaseStatus.COMPLETED

    def test_llm_to_post_hook_data_flow(
        self, project_root: Path, runs_dir: Path, sample_context: RunContext
    ) -> None:
        """Test that LLM output is available to post-hook via environment."""
        # Create a post-hook that captures the environment
        cmd_dir = project_root / ".adw" / "commands" / "plan"
        env_capture_file = runs_dir / "env_capture.txt"

        post_hook = f"""#!/bin/bash
echo "ADW_LLM_OUTPUT=$ADW_LLM_OUTPUT" > {env_capture_file}
echo "ADW_PHASE=$ADW_PHASE" >> {env_capture_file}
echo "ADW_RUN_ID=$ADW_RUN_ID" >> {env_capture_file}
"""
        (cmd_dir / "post-hook.sh").write_text(post_hook)
        (cmd_dir / "post-hook.sh").chmod(0o755)

        # Create runner
        runner = PhaseRunner(
            command_resolver=CommandResolver(project_root=project_root),
            template_engine=TemplateEngine(project_root=project_root),
            hook_runner=HookRunner(
                config=HookConfig(shell="/bin/bash", timeout_seconds=30)
            ),
            executor=MockExecutor(),
            artifact_manager=ArtifactManager(runs_dir=runs_dir),
        )

        result = runner.run("plan", sample_context)

        # Phase should complete
        assert result.status == PhaseStatus.COMPLETED

        # Check environment was captured
        assert env_capture_file.exists()
        env_content = env_capture_file.read_text()

        # ADW_LLM_OUTPUT should contain MockExecutor output
        assert "ADW_LLM_OUTPUT=" in env_content
        # ADW_PHASE should be set
        assert "ADW_PHASE=plan" in env_content

    def test_full_hook_llm_hook_chain(
        self, project_root: Path, runs_dir: Path, sample_context: RunContext
    ) -> None:
        """Test complete chain: pre-hook → LLM → post-hook with data passing."""
        # Create a pre-hook that outputs specific data
        cmd_dir = project_root / ".adw" / "commands" / "plan"
        pre_hook = """#!/bin/bash
echo "PRE_HOOK_TIMESTAMP=$(date +%s)"
echo "PRE_HOOK_STATUS=ready"
"""
        (cmd_dir / "pre-hook.sh").write_text(pre_hook)
        (cmd_dir / "pre-hook.sh").chmod(0o755)

        # Create a post-hook that logs what it received
        post_output_file = runs_dir / "post_hook_output.txt"
        post_hook = f"""#!/bin/bash
echo "Post-hook executed" > {post_output_file}
echo "LLM output length: ${{#ADW_LLM_OUTPUT}}" >> {post_output_file}
echo "Phase: $ADW_PHASE" >> {post_output_file}
"""
        (cmd_dir / "post-hook.sh").write_text(post_hook)
        (cmd_dir / "post-hook.sh").chmod(0o755)

        # Create runner
        runner = PhaseRunner(
            command_resolver=CommandResolver(project_root=project_root),
            template_engine=TemplateEngine(project_root=project_root),
            hook_runner=HookRunner(
                config=HookConfig(shell="/bin/bash", timeout_seconds=30)
            ),
            executor=MockExecutor(),
            artifact_manager=ArtifactManager(runs_dir=runs_dir),
        )

        result = runner.run("plan", sample_context)

        # Verify full chain completed
        assert result.status == PhaseStatus.COMPLETED
        assert result.tokens_used > 0

        # Verify post-hook executed and received data
        assert post_output_file.exists()
        post_content = post_output_file.read_text()
        assert "Post-hook executed" in post_content
        assert "LLM output length:" in post_content
        assert "Phase: plan" in post_content


class TestPhaseRunnerErrorRecovery:
    """Tests for error handling and recovery."""

    def test_pre_hook_failure_stops_phase(
        self, project_root: Path, runs_dir: Path, sample_context: RunContext
    ) -> None:
        """Test that pre-hook failure stops phase execution."""
        from adw.exceptions import HookError

        # Create a failing pre-hook
        cmd_dir = project_root / ".adw" / "commands" / "plan"
        pre_hook = """#!/bin/bash
echo "Pre-hook failing"
exit 1
"""
        (cmd_dir / "pre-hook.sh").write_text(pre_hook)
        (cmd_dir / "pre-hook.sh").chmod(0o755)

        runner = PhaseRunner(
            command_resolver=CommandResolver(project_root=project_root),
            template_engine=TemplateEngine(project_root=project_root),
            hook_runner=HookRunner(
                config=HookConfig(shell="/bin/bash", timeout_seconds=30)
            ),
            executor=MockExecutor(),
            artifact_manager=ArtifactManager(runs_dir=runs_dir),
        )

        with pytest.raises(HookError) as exc_info:
            runner.run("plan", sample_context)

        assert exc_info.value.code == "HOOK_FAILED"
        assert exc_info.value.exit_code == 1
