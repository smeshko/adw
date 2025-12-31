"""Unit tests for CommandLoader class.

Tests cover:
- Basic class instantiation and configuration
- Integration with CommandResolver
- Prompt loading from resolved directories
- Template variable substitution
- Artifact inclusion via context
- Pre-hook output inclusion
- Strict mode error handling
- Schema loading
"""

from datetime import datetime
from pathlib import Path

import pytest

from adw.commands import CommandLoader, CommandResolver
from adw.exceptions import ConfigError
from adw.models import RunContext


@pytest.fixture
def run_context() -> RunContext:
    """Create a minimal RunContext for testing."""
    return RunContext(
        run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        feature_description="Add user authentication",
        current_phase="plan",
        started_at=datetime.now(),
    )


@pytest.fixture
def command_dir(tmp_path: Path) -> Path:
    """Create a command directory with prompt.md."""
    cmd_dir = tmp_path / ".adw" / "commands" / "plan"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "prompt.md").write_text("This is the plan prompt.", encoding="utf-8")
    return cmd_dir


class TestCommandLoaderInstantiation:
    """Tests for CommandLoader instantiation and configuration."""

    def test_command_loader_can_be_instantiated(self) -> None:
        """CommandLoader can be instantiated without arguments."""
        loader = CommandLoader()
        assert loader is not None

    def test_command_loader_accepts_project_root(self, tmp_path: Path) -> None:
        """CommandLoader accepts an optional project_root parameter."""
        loader = CommandLoader(project_root=tmp_path)
        assert loader.project_root == tmp_path

    def test_command_loader_defaults_to_cwd(self) -> None:
        """CommandLoader defaults project_root to current working directory."""
        loader = CommandLoader()
        assert loader.project_root == Path.cwd()


class TestCommandLoaderResolverIntegration:
    """Tests for CommandLoader integration with CommandResolver."""

    def test_command_loader_has_resolver(self, tmp_path: Path) -> None:
        """CommandLoader creates its own CommandResolver if not provided."""
        loader = CommandLoader(project_root=tmp_path)
        assert loader.resolver is not None
        assert isinstance(loader.resolver, CommandResolver)

    def test_command_loader_accepts_custom_resolver(self, tmp_path: Path) -> None:
        """CommandLoader accepts a custom CommandResolver instance."""
        resolver = CommandResolver(project_root=tmp_path)
        loader = CommandLoader(project_root=tmp_path, resolver=resolver)
        assert loader.resolver is resolver

    def test_command_loader_resolver_uses_same_project_root(
        self, tmp_path: Path
    ) -> None:
        """CommandLoader's resolver uses the same project_root."""
        loader = CommandLoader(project_root=tmp_path)
        assert loader.resolver.project_root == tmp_path


class TestPromptLoading:
    """Tests for loading prompts from resolved command directories."""

    def test_load_prompt_returns_prompt_content(
        self, tmp_path: Path, command_dir: Path, run_context: RunContext
    ) -> None:
        """load_prompt returns the raw prompt content from prompt.md."""
        loader = CommandLoader(project_root=tmp_path)
        result = loader.load_prompt("plan", run_context)
        assert "This is the plan prompt." in result

    def test_load_prompt_resolves_command_using_resolver(
        self, tmp_path: Path, command_dir: Path, run_context: RunContext
    ) -> None:
        """load_prompt uses CommandResolver to find the command directory."""
        loader = CommandLoader(project_root=tmp_path)
        # If resolution fails, it would raise ConfigError
        result = loader.load_prompt("plan", run_context)
        assert result is not None

    def test_load_prompt_reads_with_utf8_encoding(
        self, tmp_path: Path, run_context: RunContext
    ) -> None:
        """load_prompt reads prompt.md with UTF-8 encoding."""
        # Create command with unicode characters
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text(
            "Hello 世界! Ñoño émoji 🎉", encoding="utf-8"
        )

        loader = CommandLoader(project_root=tmp_path)
        result = loader.load_prompt("plan", run_context)
        assert "世界" in result
        assert "🎉" in result

    def test_load_prompt_raises_error_for_missing_command(
        self, tmp_path: Path, run_context: RunContext
    ) -> None:
        """load_prompt raises ConfigError for non-existent command."""
        loader = CommandLoader(project_root=tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load_prompt("nonexistent", run_context)
        assert exc_info.value.code == "COMMAND_NOT_FOUND"
