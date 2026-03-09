"""Tests for CommandResolver three-tier resolution (Task 3).

Verifies the three-tier command resolution logic: project > user > bundled.
"""

from pathlib import Path
from unittest.mock import patch

from adw.commands import CommandResolver


class TestCommandResolverThreeTierResolution:
    """Test the three-tier resolution priority."""

    def test_project_tier_takes_precedence(self, tmp_path: Path) -> None:
        """Project-level commands should take precedence over user and bundled."""
        # Setup project-level command
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Project Plan")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.tier == "project"
        assert result.path == project_cmd
        assert result.name == "plan"

    def test_user_tier_fallback(self, tmp_path: Path) -> None:
        """User-level commands should be used when project-level doesn't exist."""
        # Setup user-level command (mock home directory)
        mock_home = tmp_path / "mock_home"
        user_cmd = mock_home / ".adw" / "commands" / "plan"
        user_cmd.mkdir(parents=True)
        (user_cmd / "prompt.md").write_text("# User Plan")

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("plan")

        assert result.tier == "user"
        assert result.path == user_cmd
        assert result.name == "plan"

    def test_bundled_tier_fallback(self, tmp_path: Path) -> None:
        """Bundled commands should be used when project and user don't exist.

        Note: This test requires bundled defaults to exist (see Task 6).
        For now, we test that the resolver correctly tries bundled tier
        by checking it raises ConfigError when no commands exist anywhere.
        The full bundled tier test is in test_resolver_bundled.py after Task 6.
        """
        # Create a temporary bundled command by manually setting up the structure
        # This simulates what Task 6 will create
        bundled_dir = tmp_path / "bundled_commands" / "plan"
        bundled_dir.mkdir(parents=True)
        (bundled_dir / "prompt.md").write_text("# Bundled Plan")

        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        # Mock the _get_bundled_command_path to return our test bundled directory
        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            # Patch _get_bundled_command_path to simulate bundled commands
            with patch.object(
                resolver, "_get_bundled_command_path", return_value=bundled_dir
            ):
                result = resolver.resolve("plan")

        assert result.tier == "bundled"
        assert result.name == "plan"

    def test_project_overrides_user_and_bundled(self, tmp_path: Path) -> None:
        """Project command should override both user and bundled."""
        # Setup project-level command
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Project Plan")

        # Setup user-level command
        mock_home = tmp_path / "mock_home"
        user_cmd = mock_home / ".adw" / "commands" / "plan"
        user_cmd.mkdir(parents=True)
        (user_cmd / "prompt.md").write_text("# User Plan")

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("plan")

        # Should use project, not user
        assert result.tier == "project"
        assert result.path == project_cmd

    def test_user_overrides_bundled(self, tmp_path: Path) -> None:
        """User command should override bundled when project doesn't exist."""
        # Setup user-level command only
        mock_home = tmp_path / "mock_home"
        user_cmd = mock_home / ".adw" / "commands" / "plan"
        user_cmd.mkdir(parents=True)
        (user_cmd / "prompt.md").write_text("# User Plan")

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)
            result = resolver.resolve("plan")

        assert result.tier == "user"
        assert result.path == user_cmd


class TestCommandResolverOptionalFileDetection:
    """Test detection of optional files in command directories."""

    def test_detects_schema_json(self, tmp_path: Path) -> None:
        """Should detect schema.json in command directory."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "schema.json").write_text("{}")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_schema is True

    def test_detects_pre_hook_sh(self, tmp_path: Path) -> None:
        """Should detect pre.sh in command directory."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "pre.sh").write_text("#!/bin/bash")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_pre_hook is True

    def test_detects_pre_hook_alternate_name(self, tmp_path: Path) -> None:
        """Should detect pre-hook.sh as alternate pre-hook name."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "pre-hook.sh").write_text("#!/bin/bash")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_pre_hook is True

    def test_detects_post_hook_sh(self, tmp_path: Path) -> None:
        """Should detect post.sh in command directory."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "post.sh").write_text("#!/bin/bash")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_post_hook is True

    def test_detects_post_hook_alternate_name(self, tmp_path: Path) -> None:
        """Should detect post-hook.sh as alternate post-hook name."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "post-hook.sh").write_text("#!/bin/bash")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_post_hook is True

    def test_no_optional_files_detected_as_false(self, tmp_path: Path) -> None:
        """Should report False for missing optional files."""
        # Use a custom command name with no bundled equivalent to avoid
        # hook chaining picking up bundled hooks
        project_cmd = tmp_path / ".adw" / "commands" / "custom-test-cmd"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Custom")
        # No schema, hooks, or config

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("custom-test-cmd")

        assert result.has_schema is False
        assert result.has_pre_hook is False
        assert result.has_post_hook is False
        assert result.has_config is False

    def test_detects_config_yaml(self, tmp_path: Path) -> None:
        """Should detect config.yaml in command directory."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "config.yaml").write_text("enabled: true")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_config is True
