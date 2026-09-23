"""Unit tests for the HookRunner class."""

import os
import stat
import time
from datetime import datetime
from pathlib import Path

import pytest

from adw.exceptions import HookError
from adw.hooks.runner import HookRunner
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
        script.write_text(
            "#!/bin/bash\necho 'stdout message'\necho 'stderr message' >&2\n"
        )
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
            'echo "RUN_ID=$ADW_RUN_ID"\n'
            'echo "PHASE=$ADW_PHASE"\n'
            'echo "FEATURE=$ADW_FEATURE"\n'
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return script

    def test_successful_hook_execution(
        self, hook_config: HookConfig, run_context: RunContext, success_hook: Path
    ) -> None:
        """Test successful hook execution captures stdout."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(success_hook, run_context, "plan")

        assert result.exit_code == 0
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

        assert result.exit_code == 0
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

    def test_timeout_kills_hook_children(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that timeout kills the children the hook started, not just the hook."""
        pid_file = tmp_path / "child.pid"
        script = tmp_path / "pre-hook.sh"
        script.write_text(f"#!/bin/bash\nsleep 30 &\necho $! > {pid_file}\nwait\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        runner = HookRunner(HookConfig(shell="/bin/bash", timeout_seconds=1))

        start = time.monotonic()
        with pytest.raises(HookError) as exc_info:
            runner.run_hook(script, run_context, "plan", timeout=1)
        elapsed = time.monotonic() - start

        assert exc_info.value.code == "HOOK_TIMEOUT"
        assert elapsed < 3

        # Poll so a killed child that is not reaped yet (Linux CI) is tolerated.
        child_pid = int(pid_file.read_text().strip())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
        pytest.fail(f"hook child {child_pid} survived the timeout")

    def test_environment_variables_passed(
        self, hook_config: HookConfig, run_context: RunContext, env_hook: Path
    ) -> None:
        """Test that ADW environment variables are passed to hook."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(env_hook, run_context, "plan")

        assert result.exit_code == 0
        assert "RUN_ID=01KDSG2VDHNK0W4HSCZWJZXWSQ" in result.stdout
        assert "PHASE=plan" in result.stdout
        assert "FEATURE=Test feature" in result.stdout

    def test_hook_type_post(
        self, hook_config: HookConfig, run_context: RunContext, success_hook: Path
    ) -> None:
        """Test hook_type is correctly set for post hooks."""
        runner = HookRunner(hook_config)
        result = runner.run_hook(success_hook, run_context, "plan", hook_type="post")

        assert result.hook_type == "post"

    def test_timeout_override(
        self, run_context: RunContext, success_hook: Path
    ) -> None:
        """Test that timeout parameter overrides config timeout."""
        config = HookConfig(shell="/bin/bash", timeout_seconds=1)
        runner = HookRunner(config)

        # This should succeed because we override with longer timeout
        result = runner.run_hook(success_hook, run_context, "plan", timeout=60)
        assert result.exit_code == 0
