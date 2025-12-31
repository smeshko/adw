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
from adw.models import ResolvedCommand, RunContext
from adw.models.command import LoadedCommand


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


class TestContextBuilding:
    """Tests for building template context from RunContext."""

    def test_build_context_includes_run_id(self, run_context: RunContext) -> None:
        """_build_context includes run_id from RunContext."""
        loader = CommandLoader()
        context = loader._build_context(run_context)
        assert context["run_id"] == "01KDSG2VDHNK0W4HSCZWJZXWSQ"

    def test_build_context_includes_feature_description(
        self, run_context: RunContext
    ) -> None:
        """_build_context includes feature_description as feature_request."""
        loader = CommandLoader()
        context = loader._build_context(run_context)
        assert context["feature_request"] == "Add user authentication"

    def test_build_context_includes_current_phase(
        self, run_context: RunContext
    ) -> None:
        """_build_context includes current_phase."""
        loader = CommandLoader()
        context = loader._build_context(run_context)
        assert context["current_phase"] == "plan"

    def test_build_context_includes_artifacts_namespace(self) -> None:
        """_build_context includes artifacts namespace for previous phases."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="build",
            started_at=datetime.now(),
            artifacts={"plan": ["plan.md", "requirements.txt"]},
        )
        loader = CommandLoader()
        built = loader._build_context(context)
        assert "artifacts" in built
        assert built["artifacts"]["plan"] == ["plan.md", "requirements.txt"]

    def test_build_context_includes_empty_pre_hook_output_by_default(
        self, run_context: RunContext
    ) -> None:
        """_build_context includes empty pre_hook_output when not available."""
        loader = CommandLoader()
        context = loader._build_context(run_context)
        assert context["pre_hook_output"] == ""

    def test_build_context_includes_pre_hook_output_when_provided(
        self, run_context: RunContext
    ) -> None:
        """_build_context includes pre_hook_output when provided."""
        loader = CommandLoader()
        context = loader._build_context(run_context, pre_hook_output="hook result")
        assert context["pre_hook_output"] == "hook result"


class TestPromptRendering:
    """Tests for template rendering in prompts."""

    def test_load_prompt_renders_template_variables(
        self, tmp_path: Path, run_context: RunContext
    ) -> None:
        """load_prompt renders {{variable}} patterns from context."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text(
            "Run ID: {{run_id}}\nPhase: {{current_phase}}", encoding="utf-8"
        )

        loader = CommandLoader(project_root=tmp_path)
        result = loader.load_prompt("plan", run_context)
        assert "Run ID: 01KDSG2VDHNK0W4HSCZWJZXWSQ" in result
        assert "Phase: plan" in result

    def test_load_prompt_renders_feature_request(
        self, tmp_path: Path, run_context: RunContext
    ) -> None:
        """load_prompt renders feature_request variable."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text(
            "Feature: {{feature_request}}", encoding="utf-8"
        )

        loader = CommandLoader(project_root=tmp_path)
        result = loader.load_prompt("plan", run_context)
        assert "Feature: Add user authentication" in result

    def test_load_prompt_uses_strict_mode_by_default(
        self, tmp_path: Path, run_context: RunContext
    ) -> None:
        """load_prompt raises error for unknown variables in strict mode."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text(
            "Unknown: {{unknown_variable}}", encoding="utf-8"
        )

        loader = CommandLoader(project_root=tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load_prompt("plan", run_context)
        assert exc_info.value.code == "UNKNOWN_VARIABLE"

    def test_load_prompt_accepts_pre_hook_output(
        self, tmp_path: Path, run_context: RunContext
    ) -> None:
        """load_prompt can include pre_hook_output in rendering."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text(
            "Hook output: {{pre_hook_output}}", encoding="utf-8"
        )

        loader = CommandLoader(project_root=tmp_path)
        result = loader.load_prompt("plan", run_context, pre_hook_output="hook data")
        assert "Hook output: hook data" in result

    def test_load_prompt_renders_artifacts_namespace(
        self, tmp_path: Path
    ) -> None:
        """load_prompt can access artifacts via artifacts.phase namespace."""
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="build",
            started_at=datetime.now(),
            artifacts={"plan": ["plan.md"]},
        )
        cmd_dir = tmp_path / ".adw" / "commands" / "build"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text(
            "Artifacts: {{artifacts.plan}}", encoding="utf-8"
        )

        loader = CommandLoader(project_root=tmp_path)
        result = loader.load_prompt("build", context)
        assert "plan.md" in result


class TestLoadedCommandModel:
    """Tests for LoadedCommand Pydantic model."""

    def test_loaded_command_has_required_fields(self, tmp_path: Path) -> None:
        """LoadedCommand model has all required fields."""
        resolved = ResolvedCommand(
            name="plan",
            path=tmp_path,
            tier="project",
            has_schema=True,
            has_pre_hook=True,
            has_post_hook=False,
        )
        loaded = LoadedCommand(
            name="plan",
            resolved=resolved,
            prompt_content="This is the prompt",
            output_schema={"type": "object"},
            has_pre_hook=True,
            has_post_hook=False,
        )
        assert loaded.name == "plan"
        assert loaded.resolved == resolved
        assert loaded.prompt_content == "This is the prompt"
        assert loaded.output_schema == {"type": "object"}
        assert loaded.has_pre_hook is True
        assert loaded.has_post_hook is False

    def test_loaded_command_schema_is_optional(self, tmp_path: Path) -> None:
        """LoadedCommand output_schema field defaults to None."""
        resolved = ResolvedCommand(
            name="plan",
            path=tmp_path,
            tier="bundled",
        )
        loaded = LoadedCommand(
            name="plan",
            resolved=resolved,
            prompt_content="Prompt",
        )
        assert loaded.output_schema is None

    def test_loaded_command_hooks_default_to_false(self, tmp_path: Path) -> None:
        """LoadedCommand hook fields default to False."""
        resolved = ResolvedCommand(
            name="plan",
            path=tmp_path,
            tier="bundled",
        )
        loaded = LoadedCommand(
            name="plan",
            resolved=resolved,
            prompt_content="Prompt",
        )
        assert loaded.has_pre_hook is False
        assert loaded.has_post_hook is False


class TestSchemaLoading:
    """Tests for optional schema.json loading."""

    def test_load_schema_returns_parsed_json(self, tmp_path: Path) -> None:
        """_load_schema returns parsed JSON when schema.json exists."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text("Prompt", encoding="utf-8")
        (cmd_dir / "schema.json").write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}',
            encoding="utf-8",
        )

        loader = CommandLoader(project_root=tmp_path)
        resolved = loader.resolver.resolve("plan")
        schema = loader._load_schema(resolved)

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_load_schema_returns_none_when_missing(self, tmp_path: Path) -> None:
        """_load_schema returns None when schema.json doesn't exist."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text("Prompt", encoding="utf-8")

        loader = CommandLoader(project_root=tmp_path)
        resolved = loader.resolver.resolve("plan")
        schema = loader._load_schema(resolved)

        assert schema is None

    def test_load_schema_raises_on_invalid_json(self, tmp_path: Path) -> None:
        """_load_schema raises ConfigError for invalid JSON."""
        cmd_dir = tmp_path / ".adw" / "commands" / "plan"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "prompt.md").write_text("Prompt", encoding="utf-8")
        (cmd_dir / "schema.json").write_text("not valid json {", encoding="utf-8")

        loader = CommandLoader(project_root=tmp_path)
        resolved = loader.resolver.resolve("plan")

        with pytest.raises(ConfigError) as exc_info:
            loader._load_schema(resolved)
        assert exc_info.value.code == "INVALID_SCHEMA"
