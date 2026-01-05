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

    def test_includes_port_variables_when_allocation_provided(
        self, run_context: RunContext
    ) -> None:
        """Test that port variables are included when port_allocation is provided."""
        from adw.models.worktree import PortAllocation

        allocation = PortAllocation(
            slot=3,
            backend_port=9103,
            frontend_port=9203,
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        )
        env = build_hook_environment(run_context, "plan", port_allocation=allocation)
        assert env["ADW_BACKEND_PORT"] == "9103"
        assert env["ADW_FRONTEND_PORT"] == "9203"
        assert env["ADW_SLOT"] == "3"

    def test_no_port_variables_without_allocation(
        self, run_context: RunContext
    ) -> None:
        """Test that port variables are not set when no allocation is provided."""
        env = build_hook_environment(run_context, "plan")
        assert "ADW_BACKEND_PORT" not in env
        assert "ADW_FRONTEND_PORT" not in env
        assert "ADW_SLOT" not in env

    def test_port_variables_are_strings(self, run_context: RunContext) -> None:
        """Test that port values are converted to strings."""
        from adw.models.worktree import PortAllocation

        allocation = PortAllocation(
            slot=0,
            backend_port=9100,
            frontend_port=9200,
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        )
        env = build_hook_environment(run_context, "plan", port_allocation=allocation)
        # Environment variables must be strings
        assert isinstance(env["ADW_BACKEND_PORT"], str)
        assert isinstance(env["ADW_FRONTEND_PORT"], str)
        assert isinstance(env["ADW_SLOT"], str)


class TestWorktreePathEnvironment:
    """Tests for ADW_WORKTREE_PATH environment variable (Story 10.5)."""

    @pytest.fixture
    def run_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature description",
            current_phase="plan",
            started_at=datetime.now(),
        )

    def test_includes_worktree_path_when_set(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_WORKTREE_PATH is set from context.worktree_path."""
        run_context = run_context.model_copy(
            update={"worktree_path": tmp_path / "worktree"}
        )
        env = build_hook_environment(run_context, "plan")
        assert env["ADW_WORKTREE_PATH"] == str(tmp_path / "worktree")

    def test_worktree_path_fallback_to_project_root(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_WORKTREE_PATH falls back to project_root when worktree not set."""
        # worktree_path is None by default in run_context
        assert run_context.worktree_path is None
        env = build_hook_environment(
            run_context, "plan", project_root=tmp_path / "project"
        )
        assert env["ADW_WORKTREE_PATH"] == str(tmp_path / "project")

    def test_worktree_path_is_absolute(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_WORKTREE_PATH is an absolute path."""
        run_context = run_context.model_copy(
            update={"worktree_path": tmp_path / "worktree"}
        )
        env = build_hook_environment(run_context, "plan")
        assert Path(env["ADW_WORKTREE_PATH"]).is_absolute()

    def test_worktree_path_uses_context_over_project_root(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that worktree_path from context is preferred over project_root."""
        run_context = run_context.model_copy(
            update={"worktree_path": tmp_path / "worktree"}
        )
        env = build_hook_environment(
            run_context, "plan", project_root=tmp_path / "project"
        )
        # Should use context.worktree_path, not project_root
        assert env["ADW_WORKTREE_PATH"] == str(tmp_path / "worktree")

    def test_worktree_path_and_project_root_both_none(
        self, run_context: RunContext
    ) -> None:
        """Test behavior when both worktree_path and project_root are None."""
        assert run_context.worktree_path is None
        # Should not include ADW_WORKTREE_PATH if no path available
        env = build_hook_environment(run_context, "plan", project_root=None)
        # Either not present or present as empty - depends on implementation
        # For backward compatibility with hooks that may check for it
        assert "ADW_WORKTREE_PATH" not in env or env.get("ADW_WORKTREE_PATH") == ""


class TestPortsEnvAutoSourcing:
    """Tests for auto-sourcing .ports.env file (Story 10.5 Task 6)."""

    @pytest.fixture
    def run_context(self) -> RunContext:
        """Create a sample RunContext for testing."""
        return RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature description",
            current_phase="plan",
            started_at=datetime.now(),
        )

    def test_ports_file_adds_adw_ports_file_env(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_PORTS_FILE is set when ports_file is provided."""
        ports_file = tmp_path / ".ports.env"
        ports_file.write_text("BACKEND_PORT=9100\n")

        env = build_hook_environment(run_context, "plan", ports_file=ports_file)

        assert env["ADW_PORTS_FILE"] == str(ports_file)

    def test_ports_file_auto_sources_variables(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that .ports.env variables are auto-sourced into environment."""
        ports_file = tmp_path / ".ports.env"
        ports_file.write_text(
            "BACKEND_PORT=9100\nFRONTEND_PORT=9200\nADW_SLOT=0\n"
        )

        env = build_hook_environment(run_context, "plan", ports_file=ports_file)

        assert env["BACKEND_PORT"] == "9100"
        assert env["FRONTEND_PORT"] == "9200"
        assert env["ADW_SLOT"] == "0"

    def test_ports_file_ignores_comments(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that comments in .ports.env are ignored."""
        ports_file = tmp_path / ".ports.env"
        ports_file.write_text(
            "# This is a comment\n"
            "BACKEND_PORT=9100\n"
            "# Another comment\n"
            "FRONTEND_PORT=9200\n"
        )

        env = build_hook_environment(run_context, "plan", ports_file=ports_file)

        assert env["BACKEND_PORT"] == "9100"
        assert env["FRONTEND_PORT"] == "9200"
        assert "This is a comment" not in str(env)

    def test_ports_file_auto_detected_from_worktree(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that .ports.env is auto-detected from worktree_path."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        ports_file = worktree_path / ".ports.env"
        ports_file.write_text("BACKEND_PORT=9101\n")

        run_context = run_context.model_copy(update={"worktree_path": worktree_path})
        env = build_hook_environment(run_context, "plan")

        assert env["ADW_PORTS_FILE"] == str(ports_file)
        assert env["BACKEND_PORT"] == "9101"

    def test_ports_file_not_added_when_missing(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that ADW_PORTS_FILE is not set when file doesn't exist."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        # .ports.env does NOT exist

        run_context = run_context.model_copy(update={"worktree_path": worktree_path})
        env = build_hook_environment(run_context, "plan")

        assert "ADW_PORTS_FILE" not in env

    def test_explicit_ports_file_takes_precedence(
        self, run_context: RunContext, tmp_path: Path
    ) -> None:
        """Test that explicit ports_file takes precedence over auto-detected."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        # Auto-detected file
        auto_ports_file = worktree_path / ".ports.env"
        auto_ports_file.write_text("BACKEND_PORT=9101\n")

        # Explicit file
        explicit_ports_file = tmp_path / "explicit.ports.env"
        explicit_ports_file.write_text("BACKEND_PORT=9200\n")

        run_context = run_context.model_copy(update={"worktree_path": worktree_path})
        env = build_hook_environment(
            run_context, "plan", ports_file=explicit_ports_file
        )

        # Should use explicit file's values
        assert env["ADW_PORTS_FILE"] == str(explicit_ports_file)
        assert env["BACKEND_PORT"] == "9200"
