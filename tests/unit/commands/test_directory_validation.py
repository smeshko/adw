"""Tests for command directory validation (Task 5).

Verifies validation of command directories including required and optional files.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from adw.commands import CommandResolver
from adw.exceptions import ConfigError


class TestCommandDirectoryValidation:
    """Test command directory validation."""

    def test_valid_directory_has_prompt_md(self, tmp_path: Path) -> None:
        """A valid command directory must have prompt.md."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan Phase")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.name == "plan"
        assert result.path == project_cmd

    def test_directory_without_prompt_md_invalid(self, tmp_path: Path) -> None:
        """Directory without prompt.md is not valid and should not be resolved."""
        # Use a non-bundled command name to avoid fallback to bundled
        project_cmd = tmp_path / ".adw" / "commands" / "custom_cmd"
        project_cmd.mkdir(parents=True)
        # No prompt.md

        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("custom_cmd")

        # Should raise COMMAND_NOT_FOUND since the directory isn't valid
        assert exc_info.value.code == "COMMAND_NOT_FOUND"

    def test_detects_schema_json_presence(self, tmp_path: Path) -> None:
        """Should correctly detect schema.json."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "schema.json").write_text('{"type": "object"}')

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_schema is True

    def test_detects_schema_json_absence(self, tmp_path: Path) -> None:
        """Should correctly detect missing schema.json."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_schema is False

    def test_detects_pre_sh_presence(self, tmp_path: Path) -> None:
        """Should correctly detect pre.sh."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "pre.sh").write_text("#!/bin/bash\necho pre")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_pre_hook is True

    def test_detects_pre_hook_sh_presence(self, tmp_path: Path) -> None:
        """Should correctly detect pre-hook.sh (alternate name)."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "pre-hook.sh").write_text("#!/bin/bash\necho pre")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_pre_hook is True

    def test_detects_post_sh_presence(self, tmp_path: Path) -> None:
        """Should correctly detect post.sh."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "post.sh").write_text("#!/bin/bash\necho post")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_post_hook is True

    def test_detects_post_hook_sh_presence(self, tmp_path: Path) -> None:
        """Should correctly detect post-hook.sh (alternate name)."""
        project_cmd = tmp_path / ".adw" / "commands" / "plan"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Plan")
        (project_cmd / "post-hook.sh").write_text("#!/bin/bash\necho post")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("plan")

        assert result.has_post_hook is True

    def test_detects_hooks_absence(self, tmp_path: Path) -> None:
        """Should correctly detect missing hooks."""
        # Use a custom command name with no bundled equivalent to avoid
        # hook chaining picking up bundled hooks
        project_cmd = tmp_path / ".adw" / "commands" / "custom-no-hooks"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Custom")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("custom-no-hooks")

        assert result.has_pre_hook is False
        assert result.has_post_hook is False

    def test_full_command_directory_structure(self, tmp_path: Path) -> None:
        """Should detect all files in a fully-equipped command directory."""
        project_cmd = tmp_path / ".adw" / "commands" / "build"
        project_cmd.mkdir(parents=True)
        (project_cmd / "prompt.md").write_text("# Build Phase")
        (project_cmd / "schema.json").write_text("{}")
        (project_cmd / "pre.sh").write_text("#!/bin/bash")
        (project_cmd / "post.sh").write_text("#!/bin/bash")

        resolver = CommandResolver(project_root=tmp_path)
        result = resolver.resolve("build")

        assert result.name == "build"
        assert result.has_schema is True
        assert result.has_pre_hook is True
        assert result.has_post_hook is True
