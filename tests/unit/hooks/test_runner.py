"""Unit tests for the HookRunner class."""

import stat
from datetime import datetime
from pathlib import Path

import pytest

from adw.exceptions import HookError
from adw.hooks.runner import HookRunner, find_hook
from adw.models import HookConfig, RunContext


class TestHookRunner:
    """Tests for HookRunner class."""

    @pytest.fixture
    def hook_config(self) -> HookConfig:
        """Create a default hook configuration."""
        return HookConfig(shell="/bin/bash", timeout_seconds=10)

    @pytest.fixture
    def run_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
        )

    @pytest.fixture
    def success_hook(self, tmp_path: Path) -> Path:
        """Create a hook script that succeeds."""
        script = tmp_path / "pre-hook.sh"
        script.write_text("#!/bin/bash\necho 'Hello from hook'\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return script

    @pytest.fixture
    def stderr_hook(self, tmp_path: Path) -> Path:
        """Create a hook script that writes to stderr."""
        script = tmp_path / "pre-hook.sh"
        script.write_text("#!/bin/bash\necho 'stdout message'\necho 'stderr message' >&2\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return script

    @pytest.fixture
    def failing_hook(self, tmp_path: Path) -> Path:
        """Create a hook script that fails."""
        script = tmp_path / "pre-hook.sh"
        script.write_text("#!/bin/bash\necho 'Error output' >&2\nexit 1\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return script

    @pytest.fixture
    def slow_hook(self, tmp_path: Path) -> Path:
        """Create a hook script that takes too long."""
        script = tmp_path / "pre-hook.sh"
        script.write_text("#!/bin/bash\nsleep 10\necho 'done'\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return script

    @pytest.fixture
    def env_hook(self, tmp_path: Path) -> Path:
        """Create a hook script that echoes environment variables."""
        script = tmp_path / "pre-hook.sh"
        script.write_text(
            "#!/bin/bash\n"
            "echo \"RUN_ID=$ADW_RUN_ID\"\n"
            "echo \"PHASE=$ADW_PHASE\"\n"
            "echo \"FEATURE=$ADW_FEATURE\"\n"
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return script

    def test_successful_hook_execution(
        self, hook_config: HookConfig, run_context: RunContext, success_hook: Path
    ) -> None:
        """Test successful hook execution captures stdout."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(success_hook, run_context, "plan")

        assert result.is_success
        assert "Hello from hook" in result.stdout
        assert result.exit_code == 0
        assert result.hook_type == "pre"
        assert result.duration_ms >= 0

    def test_captures_both_stdout_and_stderr(
        self, hook_config: HookConfig, run_context: RunContext, stderr_hook: Path
    ) -> None:
        """Test that both stdout and stderr are captured."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(stderr_hook, run_context, "plan")

        assert result.is_success
        assert "stdout message" in result.stdout
        assert "stderr message" in result.stderr

    def test_failed_hook_raises_hook_error(
        self, hook_config: HookConfig, run_context: RunContext, failing_hook: Path
    ) -> None:
        """Test that non-zero exit code raises HookError."""
        runner = HookRunner(hook_config)

        with pytest.raises(HookError) as exc_info:
            runner.run_hook(failing_hook, run_context, "build")

        error = exc_info.value
        assert error.code == "HOOK_FAILED"
        assert error.exit_code == 1
        assert error.phase == "build"
        assert "Error output" in error.stderr
        assert error.suggestion is not None

    def test_timeout_raises_hook_error(
        self, run_context: RunContext, slow_hook: Path
    ) -> None:
        """Test that timeout raises HookError with HOOK_TIMEOUT code."""
        # Use very short timeout
        config = HookConfig(shell="/bin/bash", timeout_seconds=1)
        runner = HookRunner(config)

        with pytest.raises(HookError) as exc_info:
            runner.run_hook(slow_hook, run_context, "plan", timeout=1)

        error = exc_info.value
        assert error.code == "HOOK_TIMEOUT"
        assert "timed out" in error.message.lower()
        assert error.phase == "plan"

    def test_environment_variables_passed(
        self, hook_config: HookConfig, run_context: RunContext, env_hook: Path
    ) -> None:
        """Test that ADW environment variables are passed to hook."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(env_hook, run_context, "plan")

        assert result.is_success
        assert "RUN_ID=01KDSG2VDHNK0W4HSCZWJZXWSQ" in result.stdout
        assert "PHASE=plan" in result.stdout
        assert "FEATURE=Test feature" in result.stdout

    def test_hook_type_post(
        self, hook_config: HookConfig, run_context: RunContext, success_hook: Path
    ) -> None:
        """Test hook_type is correctly set for post hooks."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(
            success_hook, run_context, "plan", hook_type="post"
        )

        assert result.hook_type == "post"

    def test_timeout_override(
        self, run_context: RunContext, success_hook: Path
    ) -> None:
        """Test that timeout parameter overrides config timeout."""
        config = HookConfig(shell="/bin/bash", timeout_seconds=1)
        runner = HookRunner(config)

        # This should succeed because we override with longer timeout
        result = runner.run_hook(success_hook, run_context, "plan", timeout=60)
        assert result.is_success


class TestFindHook:
    """Tests for find_hook function."""

    def test_finds_hook_with_sh_extension(self, tmp_path: Path) -> None:
        """Test finding a hook with .sh extension."""
        hook = tmp_path / "pre-hook.sh"
        hook.write_text("#!/bin/bash\necho 'test'\n")

        result = find_hook(tmp_path, "pre")
        assert result == hook

    def test_finds_hook_without_extension(self, tmp_path: Path) -> None:
        """Test finding a hook without extension."""
        hook = tmp_path / "post-hook"
        hook.write_text("#!/bin/bash\necho 'test'\n")

        result = find_hook(tmp_path, "post")
        assert result == hook

    def test_prefers_sh_extension(self, tmp_path: Path) -> None:
        """Test that .sh extension is preferred over extensionless."""
        hook_sh = tmp_path / "pre-hook.sh"
        hook_sh.write_text("#!/bin/bash\necho 'sh'\n")

        hook_no_ext = tmp_path / "pre-hook"
        hook_no_ext.write_text("#!/bin/bash\necho 'no ext'\n")

        result = find_hook(tmp_path, "pre")
        assert result == hook_sh

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Test that None is returned when hook doesn't exist."""
        result = find_hook(tmp_path, "pre")
        assert result is None

    def test_returns_none_for_directory(self, tmp_path: Path) -> None:
        """Test that directories are not returned as hooks."""
        hook_dir = tmp_path / "pre-hook.sh"
        hook_dir.mkdir()

        result = find_hook(tmp_path, "pre")
        assert result is None

    def test_finds_pre_hook(self, tmp_path: Path) -> None:
        """Test finding pre-hook specifically."""
        pre = tmp_path / "pre-hook.sh"
        pre.write_text("#!/bin/bash\n")
        post = tmp_path / "post-hook.sh"
        post.write_text("#!/bin/bash\n")

        result = find_hook(tmp_path, "pre")
        assert result == pre
        assert result != post

    def test_finds_post_hook(self, tmp_path: Path) -> None:
        """Test finding post-hook specifically."""
        pre = tmp_path / "pre-hook.sh"
        pre.write_text("#!/bin/bash\n")
        post = tmp_path / "post-hook.sh"
        post.write_text("#!/bin/bash\n")

        result = find_hook(tmp_path, "post")
        assert result == post
