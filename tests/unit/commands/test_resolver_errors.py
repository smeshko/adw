"""Tests for CommandResolver error handling (Task 4).

Verifies proper error handling for command not found and invalid commands.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from adw.commands import CommandResolver
from adw.exceptions import ConfigError


class TestCommandResolverErrorHandling:
    """Test error handling in CommandResolver."""

    def test_command_not_found_raises_config_error(self, tmp_path: Path) -> None:
        """Should raise ConfigError with COMMAND_NOT_FOUND when command doesn't exist."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("nonexistent_command")

        assert exc_info.value.code == "COMMAND_NOT_FOUND"

    def test_command_not_found_includes_command_name(self, tmp_path: Path) -> None:
        """Error message should include the command name."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("my_missing_command")

        assert "my_missing_command" in exc_info.value.message

    def test_command_not_found_includes_suggestion(self, tmp_path: Path) -> None:
        """Error should include a helpful suggestion."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("unknown")

        assert exc_info.value.suggestion is not None
        assert len(exc_info.value.suggestion) > 0

    def test_command_not_found_is_not_recoverable(self, tmp_path: Path) -> None:
        """COMMAND_NOT_FOUND should not be recoverable."""
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("missing")

        assert exc_info.value.recoverable is False

    def test_directory_without_prompt_md_not_valid(self, tmp_path: Path) -> None:
        """A command directory without prompt.md should not be valid."""
        # Create directory without prompt.md
        project_cmd = tmp_path / ".adw" / "commands" / "incomplete"
        project_cmd.mkdir(parents=True)
        # No prompt.md created

        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("incomplete")

        assert exc_info.value.code == "COMMAND_NOT_FOUND"

    def test_file_instead_of_directory_not_valid(self, tmp_path: Path) -> None:
        """A file instead of directory should not be valid."""
        # Create file instead of directory - use non-bundled command name
        commands_dir = tmp_path / ".adw" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "custom_command").write_text("I'm a file, not a directory")

        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        with patch.object(Path, "home", return_value=mock_home):
            resolver = CommandResolver(project_root=tmp_path)

            with pytest.raises(ConfigError) as exc_info:
                resolver.resolve("custom_command")

        assert exc_info.value.code == "COMMAND_NOT_FOUND"
