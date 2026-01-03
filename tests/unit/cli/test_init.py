"""Unit tests for CLI init command.

Tests the init command functionality for initializing ADW projects,
including project detection, directory creation, and configuration generation.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app


runner = CliRunner()


class TestInitCommand:
    """Tests for the init CLI command."""

    def test_init_creates_adw_directory(self, tmp_path: Path) -> None:
        """Test that init creates .adw/ directory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert (Path.cwd() / ".adw").exists()
            assert (Path.cwd() / ".adw").is_dir()

    def test_init_creates_project_yaml(self, tmp_path: Path) -> None:
        """Test that init creates project.yaml configuration file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            project_yaml = Path.cwd() / ".adw" / "project.yaml"
            assert project_yaml.exists()

    def test_init_creates_runs_directory(self, tmp_path: Path) -> None:
        """Test that init creates runs/ subdirectory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            runs_dir = Path.cwd() / ".adw" / "runs"
            assert runs_dir.exists()
            assert runs_dir.is_dir()

    def test_init_creates_commands_directory(self, tmp_path: Path) -> None:
        """Test that init creates commands/ subdirectory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            commands_dir = Path.cwd() / ".adw" / "commands"
            assert commands_dir.exists()
            assert commands_dir.is_dir()

    def test_init_creates_gitignore(self, tmp_path: Path) -> None:
        """Test that init creates .gitignore in .adw/ directory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            gitignore = Path.cwd() / ".adw" / ".gitignore"
            assert gitignore.exists()
            content = gitignore.read_text()
            assert "runs/" in content

    def test_init_fails_if_already_initialized(self, tmp_path: Path) -> None:
        """Test that init raises ConfigError if .adw/ already exists."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .adw/ directory
            (Path.cwd() / ".adw").mkdir()

            result = runner.invoke(app, ["init"])

            assert result.exit_code != 0
            # ConfigError is caught by Typer and displays the message
            assert "already initialized" in result.output.lower()
            assert "adw init --force" in result.output.lower()

    def test_init_force_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that init --force overwrites existing configuration."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .adw/ with old config
            adw_dir = Path.cwd() / ".adw"
            adw_dir.mkdir()
            old_config = adw_dir / "project.yaml"
            old_config.write_text("old: config\n")

            result = runner.invoke(app, ["init", "--force"])

            assert result.exit_code == 0
            new_config = old_config.read_text()
            assert "old: config" not in new_config
            assert "language:" in new_config

    def test_init_force_short_flag(self, tmp_path: Path) -> None:
        """Test that init -f works as short form of --force."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / ".adw").mkdir()

            result = runner.invoke(app, ["init", "-f"])

            assert result.exit_code == 0

    def test_init_language_override(self, tmp_path: Path) -> None:
        """Test that init --language overrides auto-detection."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--language", "rust"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: rust" in config

    def test_init_language_short_flag(self, tmp_path: Path) -> None:
        """Test that init -l works as short form of --language."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "-l", "go"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: go" in config


class TestInitProjectDetection:
    """Tests for project type auto-detection during init."""

    def test_init_detects_python_from_pyproject_toml(self, tmp_path: Path) -> None:
        """Test that init detects Python project from pyproject.toml."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "pyproject.toml").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: python" in config
            assert "test_command: pytest" in config

    def test_init_detects_python_from_setup_py(self, tmp_path: Path) -> None:
        """Test that init detects Python project from setup.py."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "setup.py").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: python" in config

    def test_init_detects_python_from_requirements_txt(self, tmp_path: Path) -> None:
        """Test that init detects Python project from requirements.txt."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "requirements.txt").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: python" in config

    def test_init_detects_nodejs_from_package_json(self, tmp_path: Path) -> None:
        """Test that init detects Node.js project from package.json."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "package.json").write_text("{}")

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: javascript" in config
            assert "test_command: npm test" in config

    def test_init_detects_go_from_go_mod(self, tmp_path: Path) -> None:
        """Test that init detects Go project from go.mod."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "go.mod").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: go" in config
            assert "go test" in config

    def test_init_detects_rust_from_cargo_toml(self, tmp_path: Path) -> None:
        """Test that init detects Rust project from Cargo.toml."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "Cargo.toml").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: rust" in config
            assert "cargo test" in config

    def test_init_detects_java_from_build_gradle(self, tmp_path: Path) -> None:
        """Test that init detects Java project from build.gradle."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "build.gradle").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: java" in config
            assert "gradle test" in config

    def test_init_detects_java_from_pom_xml(self, tmp_path: Path) -> None:
        """Test that init detects Java project from pom.xml."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "pom.xml").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: java" in config

    def test_init_detects_ruby_from_gemfile(self, tmp_path: Path) -> None:
        """Test that init detects Ruby project from Gemfile."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "Gemfile").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: ruby" in config
            assert "rspec" in config

    def test_init_detects_php_from_composer_json(self, tmp_path: Path) -> None:
        """Test that init detects PHP project from composer.json."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "composer.json").write_text("{}")

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: php" in config
            assert "phpunit" in config

    def test_init_defaults_to_generic_when_no_markers(self, tmp_path: Path) -> None:
        """Test that init defaults to generic when no project markers found."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: unknown" in config


class TestInitLanguageValidation:
    """Tests for language override validation."""

    def test_init_warns_on_invalid_language(self, tmp_path: Path) -> None:
        """Test that init warns when invalid language is specified."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--language", "garbage"])

            assert result.exit_code == 0
            assert "warning" in result.output.lower()
            assert "unknown language" in result.output.lower()

    def test_init_accepts_valid_language(self, tmp_path: Path) -> None:
        """Test that init accepts valid language without warning."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--language", "python"])

            assert result.exit_code == 0
            assert "warning" not in result.output.lower()
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: python" in config


class TestInitOutput:
    """Tests for init command output and display."""

    def test_init_shows_success_message(self, tmp_path: Path) -> None:
        """Test that init shows success message on completion."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert "initialized" in result.output.lower()

    def test_init_shows_detected_project_type(self, tmp_path: Path) -> None:
        """Test that init displays the detected project type."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "pyproject.toml").touch()

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert "python" in result.output.lower()

    def test_init_shows_next_steps(self, tmp_path: Path) -> None:
        """Test that init displays next steps for the user."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            # Should mention how to proceed
            assert "adw" in result.output.lower()


class TestInitConfigContent:
    """Tests for generated configuration content."""

    def test_init_config_is_valid_yaml(self, tmp_path: Path) -> None:
        """Test that generated configuration is valid YAML."""
        import yaml

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config_path = Path.cwd() / ".adw" / "project.yaml"
            config_content = config_path.read_text()

            # Should parse without error
            data = yaml.safe_load(config_content)
            assert isinstance(data, dict)

    def test_init_config_has_required_fields(self, tmp_path: Path) -> None:
        """Test that generated configuration has required fields."""
        import yaml

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config_path = Path.cwd() / ".adw" / "project.yaml"
            data = yaml.safe_load(config_path.read_text())

            assert "language" in data

    def test_init_config_has_llm_section(self, tmp_path: Path) -> None:
        """Test that generated configuration includes LLM settings."""
        import yaml

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            config_path = Path.cwd() / ".adw" / "project.yaml"
            data = yaml.safe_load(config_path.read_text())

            assert "llm" in data
            assert "claude_code" in data["llm"]
