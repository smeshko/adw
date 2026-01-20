"""Integration tests for hook execution.

These tests verify hook execution with real shell scripts,
environment variable propagation, and timeout behavior.
"""

import os
import stat
from datetime import datetime
from pathlib import Path

import pytest

from adw.exceptions import HookError
from adw.hooks.runner import HookRunner, find_hook
from adw.models import HookConfig, RunContext


class TestHookIntegration:
    """Integration tests for hook execution with real scripts."""

    @pytest.fixture
    def hook_config(self) -> HookConfig:
        """Create hook configuration for integration tests."""
        return HookConfig(shell="/bin/bash", timeout_seconds=30)

    @pytest.fixture
    def run_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Integration test feature",
            current_phase="test",
            started_at=datetime.now(),
        )

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Get the path to hook test fixtures."""
        return Path(__file__).parent.parent / "fixtures" / "hooks"

    def test_execute_success_script(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        fixtures_path: Path,
    ) -> None:
        """Test executing the success.sh fixture script."""
        runner = HookRunner(hook_config)
        hook_path = fixtures_path / "success.sh"

        result = runner.run_hook(hook_path, run_context, "test")

        assert result.is_success
        assert result.exit_code == 0
        assert "Hook executed successfully" in result.stdout
        assert "01KDSG2VDHNK0W4HSCZWJZXWSQ" in result.stdout

    def test_execute_failure_script(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        fixtures_path: Path,
    ) -> None:
        """Test executing the failure.sh fixture script."""
        runner = HookRunner(hook_config)
        hook_path = fixtures_path / "failure.sh"

        with pytest.raises(HookError) as exc_info:
            runner.run_hook(hook_path, run_context, "test")

        error = exc_info.value
        assert error.code == "HOOK_FAILED"
        assert error.exit_code == 1
        assert "Something went wrong" in error.stderr

    def test_environment_variable_propagation(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        fixtures_path: Path,
        tmp_path: Path,
    ) -> None:
        """Test that ADW environment variables are correctly propagated."""
        runner = HookRunner(hook_config)
        hook_path = fixtures_path / "env_check.sh"
        artifacts_dir = tmp_path / "artifacts"
        context_file = tmp_path / "context.json"

        result = runner.run_hook(
            hook_path,
            run_context,
            "build",
            artifacts_dir=artifacts_dir,
            context_file=context_file,
        )

        assert result.is_success
        # Verify each environment variable
        assert "ADW_RUN_ID=01KDSG2VDHNK0W4HSCZWJZXWSQ" in result.stdout
        assert "ADW_PHASE=build" in result.stdout
        assert "ADW_FEATURE=Integration test feature" in result.stdout
        assert f"ADW_ARTIFACTS_DIR={artifacts_dir}" in result.stdout
        assert f"ADW_CONTEXT_FILE={context_file}" in result.stdout

    def test_timeout_with_slow_script(
        self,
        run_context: RunContext,
        fixtures_path: Path,
    ) -> None:
        """Test that slow scripts are properly terminated on timeout."""
        # Use short timeout
        config = HookConfig(shell="/bin/bash", timeout_seconds=1)
        runner = HookRunner(config)
        hook_path = fixtures_path / "slow.sh"

        with pytest.raises(HookError) as exc_info:
            runner.run_hook(hook_path, run_context, "test", timeout=1)

        error = exc_info.value
        assert error.code == "HOOK_TIMEOUT"
        assert "timed out" in error.message.lower()

    def test_find_and_execute_hook_workflow(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        tmp_path: Path,
    ) -> None:
        """Test the complete workflow of finding and executing a hook."""
        # Create a command directory with a pre-hook
        command_dir = tmp_path / "commands" / "plan"
        command_dir.mkdir(parents=True)

        pre_hook = command_dir / "pre-hook.sh"
        pre_hook.write_text(
            "#!/bin/bash\n"
            "echo 'Preparing environment for $ADW_PHASE phase'\n"
            "echo 'Run ID: $ADW_RUN_ID'\n"
        )
        pre_hook.chmod(pre_hook.stat().st_mode | stat.S_IEXEC)

        # Find and execute the hook
        found_hook = find_hook(command_dir, "pre")
        assert found_hook is not None
        assert found_hook == pre_hook

        runner = HookRunner(hook_config)
        result = runner.run_hook(found_hook, run_context, "plan")

        assert result.is_success
        assert "Preparing environment" in result.stdout

    def test_missing_hook_returns_none(self, tmp_path: Path) -> None:
        """Test that find_hook returns None for missing hooks."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = find_hook(empty_dir, "pre")
        assert result is None

        result = find_hook(empty_dir, "post")
        assert result is None

    def test_hook_inherits_system_environment(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        tmp_path: Path,
    ) -> None:
        """Test that hooks inherit the system PATH and other env vars."""
        hook_path = tmp_path / "check_path.sh"
        hook_path.write_text('#!/bin/bash\necho "PATH=$PATH"\necho "HOME=$HOME"\n')
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

        runner = HookRunner(hook_config)
        result = runner.run_hook(hook_path, run_context, "test")

        assert result.is_success
        # PATH should be inherited from os.environ
        assert "PATH=" in result.stdout
        assert os.environ.get("PATH", "") in result.stdout
        # HOME should also be inherited
        assert f"HOME={os.environ.get('HOME', '')}" in result.stdout

    def test_working_directory_default_is_cwd(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        tmp_path: Path,
    ) -> None:
        """Test that hook's working directory defaults to current directory."""
        hook_dir = tmp_path / "hooks"
        hook_dir.mkdir()
        hook_path = hook_dir / "check_cwd.sh"
        hook_path.write_text("#!/bin/bash\npwd\n")
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

        runner = HookRunner(hook_config)
        result = runner.run_hook(hook_path, run_context, "test")

        assert result.is_success
        # Default working directory is cwd
        # Use samefile() for macOS case-insensitive filesystem compatibility
        assert Path.cwd().samefile(Path(result.stdout.strip()))

    def test_working_directory_override(
        self,
        hook_config: HookConfig,
        run_context: RunContext,
        tmp_path: Path,
    ) -> None:
        """Test that working_dir parameter overrides default."""
        hook_dir = tmp_path / "hooks"
        hook_dir.mkdir()
        hook_path = hook_dir / "check_cwd.sh"
        hook_path.write_text("#!/bin/bash\npwd\n")
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

        project_root = tmp_path / "project"
        project_root.mkdir()

        runner = HookRunner(hook_config)
        result = runner.run_hook(
            hook_path, run_context, "test", working_dir=project_root
        )

        assert result.is_success
        assert str(project_root) in result.stdout
