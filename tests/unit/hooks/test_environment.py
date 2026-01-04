"""Unit tests for the hook environment builder."""

import os
from datetime import datetime
from pathlib import Path

import pytest

from adw.hooks.environment import build_hook_environment
from adw.models import RunContext


class TestBuildHookEnvironment:
    """Tests for build_hook_environment function."""

    @pytest.fixture
    def run_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature description",
            current_phase="plan",
            started_at=datetime.now(),
        )

    def test_includes_adw_run_id(self, run_context: RunContext) -> None:
        """Test that ADW_RUN_ID is set from context."""
        env = build_hook_environment(run_context, "plan")
        assert env["ADW_RUN_ID"] == "01KDSG2VDHNK0W4HSCZWJZXWSQ"

    def test_includes_adw_phase(self, run_context: RunContext) -> None:
        """Test that ADW_PHASE is set from the phase argument."""
        env = build_hook_environment(run_context, "build")
        assert env["ADW_PHASE"] == "build"

    def test_includes_adw_artifacts_dir(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_ARTIFACTS_DIR is set when provided."""
        env = build_hook_environment(
            run_context, "plan", artifacts_dir=tmp_path / "artifacts"
        )
        assert env["ADW_ARTIFACTS_DIR"] == str(tmp_path / "artifacts")

    def test_includes_adw_context_file(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_CONTEXT_FILE is set when provided."""
        env = build_hook_environment(
            run_context, "plan", context_file=tmp_path / "context.json"
        )
        assert env["ADW_CONTEXT_FILE"] == str(tmp_path / "context.json")

    def test_includes_adw_feature(self, run_context: RunContext) -> None:
        """Test that ADW_FEATURE is set from context feature_description."""
        env = build_hook_environment(run_context, "plan")
        assert env["ADW_FEATURE"] == "Test feature description"

    def test_merges_with_os_environ(self, run_context: RunContext) -> None:
        """Test that environment merges with current os.environ."""
        env = build_hook_environment(run_context, "plan")
        # PATH should be inherited from os.environ
        assert "PATH" in env
        assert env["PATH"] == os.environ.get("PATH", "")

    def test_adw_vars_override_existing(self, run_context: RunContext) -> None:
        """Test that ADW_ variables override any existing ones."""
        # Even if ADW_RUN_ID existed in os.environ, our value should override
        env = build_hook_environment(run_context, "plan")
        assert env["ADW_RUN_ID"] == run_context.run_id

    def test_handles_none_artifacts_dir(self, run_context: RunContext) -> None:
        """Test handling when artifacts_dir is None."""
        env = build_hook_environment(run_context, "plan", artifacts_dir=None)
        assert env.get("ADW_ARTIFACTS_DIR", "") == ""

    def test_handles_none_context_file(self, run_context: RunContext) -> None:
        """Test handling when context_file is None."""
        env = build_hook_environment(run_context, "plan", context_file=None)
        assert env.get("ADW_CONTEXT_FILE", "") == ""

    def test_all_values_are_strings(self, run_context: RunContext) -> None:
        """Test that all environment variable values are strings."""
        env = build_hook_environment(run_context, "plan")
        for key, value in env.items():
            assert isinstance(key, str), f"Key {key} is not a string"
            assert isinstance(value, str), f"Value for {key} is not a string"
