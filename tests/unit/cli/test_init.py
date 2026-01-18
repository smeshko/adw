# REDUCTION: Consolidated 10 language detection tests into 1 parameterized test.
# Removed weak flag tests (test_init_language_short_flag, test_init_force_short_flag).
# Original: ~353 lines -> Reduced: ~180 lines
"""Unit tests for CLI init command.

Tests the init command functionality for initializing ADW projects,
including project detection, directory creation, and configuration generation.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestInitCommand:
    """Tests for the init CLI command."""

    def test_init_creates_adw_directory(self, tmp_path: Path) -> None:
        """Test that init creates .adw/ directory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            assert (Path.cwd() / ".adw").exists()
            assert (Path.cwd() / ".adw").is_dir()

    def test_init_creates_project_yaml(self, tmp_path: Path) -> None:
        """Test that init creates project.yaml configuration file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            project_yaml = Path.cwd() / ".adw" / "project.yaml"
            assert project_yaml.exists()

    def test_init_creates_runs_directory(self, tmp_path: Path) -> None:
        """Test that init creates runs/ subdirectory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            runs_dir = Path.cwd() / ".adw" / "runs"
            assert runs_dir.exists()
            assert runs_dir.is_dir()

    def test_init_creates_commands_directory(self, tmp_path: Path) -> None:
        """Test that init creates commands/ subdirectory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            commands_dir = Path.cwd() / ".adw" / "commands"
            assert commands_dir.exists()
            assert commands_dir.is_dir()

    def test_init_creates_gitignore(self, tmp_path: Path) -> None:
        """Test that init creates .gitignore in .adw/ directory."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            gitignore = Path.cwd() / ".adw" / ".gitignore"
            assert gitignore.exists()
            content = gitignore.read_text()
            assert "runs/" in content

    def test_init_shows_warning_if_already_initialized(self, tmp_path: Path) -> None:
        """Test that init shows warning if .adw/ already exists."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .adw/ directory
            (Path.cwd() / ".adw").mkdir()

            # Without --force, shows warning and prompts (we decline)
            result = runner.invoke(app, ["init", "--no-interactive"])

            # Should show warning about existing config
            assert "existing configuration" in result.output.lower()

    def test_init_force_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that init --force overwrites existing configuration."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .adw/ with old config
            adw_dir = Path.cwd() / ".adw"
            adw_dir.mkdir()
            old_config = adw_dir / "project.yaml"
            old_config.write_text("old: config\n")

            result = runner.invoke(app, ["init", "--force", "--no-interactive"])

            assert result.exit_code == 0
            new_config = old_config.read_text()
            assert "old: config" not in new_config
            assert "language:" in new_config

    def test_init_language_override(self, tmp_path: Path) -> None:
        """Test that init --language overrides auto-detection."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--language", "rust", "--no-interactive"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: rust" in config


class TestInitProjectDetection:
    """Tests for project type auto-detection during init."""

    @pytest.mark.parametrize(
        "marker_file,file_content,expected_language,expected_test_cmd",
        [
            ("pyproject.toml", "", "python", "pytest"),
            ("setup.py", "", "python", None),
            ("requirements.txt", "", "python", None),
            ("package.json", "{}", "javascript", "npm test"),
            ("go.mod", "", "go", "go test"),
            ("Cargo.toml", "", "rust", "cargo test"),
            ("build.gradle", "", "java", "gradle test"),
            ("pom.xml", "", "java", None),
            ("Gemfile", "", "ruby", "rspec"),
            ("composer.json", "{}", "php", "phpunit"),
        ],
    )
    def test_init_detects_language_from_marker_file(
        self,
        tmp_path: Path,
        marker_file: str,
        file_content: str,
        expected_language: str,
        expected_test_cmd: str | None,
    ) -> None:
        """Test that init detects project language from marker files."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            marker_path = Path.cwd() / marker_file
            if file_content:
                marker_path.write_text(file_content)
            else:
                marker_path.touch()

            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert f"language: {expected_language}" in config
            if expected_test_cmd:
                assert expected_test_cmd in config

    def test_init_defaults_to_generic_when_no_markers(self, tmp_path: Path) -> None:
        """Test that init defaults to generic when no project markers found."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: unknown" in config


class TestInitLanguageValidation:
    """Tests for language override validation."""

    def test_init_warns_on_invalid_language(self, tmp_path: Path) -> None:
        """Test that init warns when invalid language is specified."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--language", "garbage", "--no-interactive"])

            assert result.exit_code == 0
            assert "warning" in result.output.lower()
            assert "unknown language" in result.output.lower()

    def test_init_accepts_valid_language(self, tmp_path: Path) -> None:
        """Test that init accepts valid language without warning."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--language", "python", "--no-interactive"])

            assert result.exit_code == 0
            assert "warning" not in result.output.lower()
            config = (Path.cwd() / ".adw" / "project.yaml").read_text()
            assert "language: python" in config


class TestInitOutput:
    """Tests for init command output and display."""

    def test_init_shows_success_message(self, tmp_path: Path) -> None:
        """Test that init shows success message on completion."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            assert "initialized" in result.output.lower()

    def test_init_shows_detected_project_type(self, tmp_path: Path) -> None:
        """Test that init displays the detected project type."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "pyproject.toml").touch()

            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            assert "python" in result.output.lower()

    def test_init_shows_next_steps(self, tmp_path: Path) -> None:
        """Test that init displays next steps for the user."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            # Should mention how to proceed
            assert "adw" in result.output.lower()


class TestInitConfigContent:
    """Tests for generated configuration content."""

    def test_init_config_is_valid_yaml(self, tmp_path: Path) -> None:
        """Test that generated configuration is valid YAML."""
        import yaml

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

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
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            config_path = Path.cwd() / ".adw" / "project.yaml"
            data = yaml.safe_load(config_path.read_text())

            assert "language" in data

    def test_init_config_has_llm_section(self, tmp_path: Path) -> None:
        """Test that generated configuration includes LLM settings."""
        import yaml

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            config_path = Path.cwd() / ".adw" / "project.yaml"
            data = yaml.safe_load(config_path.read_text())

            assert "llm" in data
            assert "claude_code" in data["llm"]


class TestInitWizardFlags:
    """Tests for wizard and no-interactive flags."""

    def test_wizard_flag_forces_wizard_mode(self, tmp_path: Path) -> None:
        """Test that --wizard flag enters wizard mode."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Simulate user cancelling the wizard
            result = runner.invoke(app, ["init", "--wizard"], input="c\n")

            # Wizard was entered (may exit with 0 or non-zero depending on cancel handling)
            # Key is that wizard output appears
            assert "guided setup" in result.output.lower() or "wizard" in result.output.lower()

    def test_no_interactive_flag_skips_wizard(self, tmp_path: Path) -> None:
        """Test that --no-interactive flag uses minimal setup."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--no-interactive"])

            assert result.exit_code == 0
            # Should complete without prompting
            assert (Path.cwd() / ".adw" / "project.yaml").exists()

    def test_wizard_and_no_interactive_mutually_exclusive(self, tmp_path: Path) -> None:
        """Test that --wizard and --no-interactive cannot be used together."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(app, ["init", "--wizard", "--no-interactive"])

            assert result.exit_code != 0
            assert "mutually exclusive" in result.output.lower()

    def test_existing_config_shows_warning_panel(self, tmp_path: Path) -> None:
        """Test that existing config shows warning panel in interactive mode."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .adw/ directory
            (Path.cwd() / ".adw").mkdir()

            # Interactive mode should show warning and prompt (decline with 'n')
            result = runner.invoke(app, ["init"], input="n\n")

            # Should show warning about existing configuration
            assert "existing configuration" in result.output.lower()
            assert "warning" in result.output.lower()

    def test_no_interactive_with_existing_config_requires_force(
        self, tmp_path: Path
    ) -> None:
        """Test that --no-interactive requires --force when .adw/ exists."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .adw/ directory
            (Path.cwd() / ".adw").mkdir()

            result = runner.invoke(app, ["init", "--no-interactive"])

            # Should fail and require --force
            assert result.exit_code == 1
            assert "cannot overwrite" in result.output.lower()
            assert "--force" in result.output.lower()
