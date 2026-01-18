"""Integration tests for CLI init command.

Tests the full init flow including directory creation, configuration
generation, and subsequent run command integration.
"""

import subprocess
import sys
from pathlib import Path

import yaml


class TestInitFullFlow:
    """Integration tests for complete init workflow."""

    def test_full_init_flow_python_project(self, tmp_path: Path) -> None:
        """Test complete init flow for Python project."""
        # Create Python project marker
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        # Run init command with --no-interactive to skip prompts
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "initialized" in result.stdout.lower()
        assert "python" in result.stdout.lower()

        # Verify directory structure
        adw_dir = tmp_path / ".adw"
        assert adw_dir.exists()
        assert (adw_dir / "project.yaml").exists()
        assert (adw_dir / "runs").exists()
        assert (adw_dir / "commands").exists()
        assert (adw_dir / ".gitignore").exists()

        # Verify config content
        config = yaml.safe_load((adw_dir / "project.yaml").read_text())
        assert config["language"] == "python"
        assert config["test_command"] == "pytest"
        assert "llm" in config
        assert "claude_code" in config["llm"]

    def test_full_init_flow_nodejs_project(self, tmp_path: Path) -> None:
        """Test complete init flow for Node.js project."""
        # Create Node.js project marker
        (tmp_path / "package.json").write_text('{"name": "test-project"}')

        # Run init command with --no-interactive
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Verify config
        config = yaml.safe_load((tmp_path / ".adw" / "project.yaml").read_text())
        assert config["language"] == "javascript"
        assert config["test_command"] == "npm test"

    def test_full_init_flow_generic_project(self, tmp_path: Path) -> None:
        """Test complete init flow for generic project (no markers)."""
        # Run init command in empty directory with --no-interactive
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Verify config defaults to unknown
        config = yaml.safe_load((tmp_path / ".adw" / "project.yaml").read_text())
        assert config["language"] == "unknown"


class TestInitReinitialize:
    """Integration tests for reinitializing existing projects."""

    def test_init_shows_warning_on_existing_project(self, tmp_path: Path) -> None:
        """Test that init shows warning when .adw/ already exists."""
        # Create existing .adw directory
        (tmp_path / ".adw").mkdir()

        # Run init command with --no-interactive (will show warning but not proceed)
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        # Should show warning about existing config
        assert "existing configuration" in result.stdout.lower()

    def test_init_force_reinitializes(self, tmp_path: Path) -> None:
        """Test that init --force reinitializes existing project."""
        # Create existing .adw with old config
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        (adw_dir / "project.yaml").write_text("old: config\n")

        # Create Python marker
        (tmp_path / "pyproject.toml").touch()

        # Run init with force and --no-interactive
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--force", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Verify new config
        config = yaml.safe_load((adw_dir / "project.yaml").read_text())
        assert config["language"] == "python"
        assert "old" not in config

    def test_init_force_creates_backup(self, tmp_path: Path) -> None:
        """Test that init --force creates backup of existing config."""
        # Create existing .adw with config
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        (adw_dir / "project.yaml").write_text("old: config\n")

        # Run init with force and --no-interactive
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--force", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Verify backup was created
        backup_dirs = list(tmp_path.glob(".adw.backup.*"))
        assert len(backup_dirs) == 1
        assert (backup_dirs[0] / "project.yaml").exists()


class TestInitDirectoryStructure:
    """Integration tests for directory structure verification."""

    def test_runs_directory_is_gitignored(self, tmp_path: Path) -> None:
        """Test that runs/ directory is properly gitignored."""
        # Run init with --no-interactive
        subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        # Verify .gitignore content
        gitignore_path = tmp_path / ".adw" / ".gitignore"
        gitignore_content = gitignore_path.read_text()

        assert "runs/" in gitignore_content

    def test_commands_directory_is_empty(self, tmp_path: Path) -> None:
        """Test that commands/ directory is created empty."""
        # Run init with --no-interactive
        subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        # Verify commands directory is empty
        commands_dir = tmp_path / ".adw" / "commands"
        assert commands_dir.is_dir()
        assert list(commands_dir.iterdir()) == []

    def test_runs_directory_is_empty(self, tmp_path: Path) -> None:
        """Test that runs/ directory is created empty."""
        # Run init with --no-interactive
        subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        # Verify runs directory is empty
        runs_dir = tmp_path / ".adw" / "runs"
        assert runs_dir.is_dir()
        assert list(runs_dir.iterdir()) == []


class TestInitLanguageOverride:
    """Integration tests for language override functionality."""

    def test_language_override_ignores_detection(self, tmp_path: Path) -> None:
        """Test that --language overrides auto-detection."""
        # Create Python marker
        (tmp_path / "pyproject.toml").touch()

        # Run init with different language and --no-interactive
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--language", "rust", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Verify override applied
        config = yaml.safe_load((tmp_path / ".adw" / "project.yaml").read_text())
        assert config["language"] == "rust"
        assert "cargo test" in config["test_command"]

    def test_language_short_flag(self, tmp_path: Path) -> None:
        """Test that -l short flag works."""
        result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "-l", "go", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        config = yaml.safe_load((tmp_path / ".adw" / "project.yaml").read_text())
        assert config["language"] == "go"


class TestInitConfigValidation:
    """Integration tests for configuration validation."""

    def test_generated_config_is_valid_yaml(self, tmp_path: Path) -> None:
        """Test that generated configuration is valid YAML."""
        subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        # Should parse without error
        config_path = tmp_path / ".adw" / "project.yaml"
        config = yaml.safe_load(config_path.read_text())
        assert isinstance(config, dict)

    def test_generated_config_has_llm_timeout(self, tmp_path: Path) -> None:
        """Test that generated config includes LLM timeout setting."""
        subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        config = yaml.safe_load((tmp_path / ".adw" / "project.yaml").read_text())
        assert config["llm"]["claude_code"]["timeout_seconds"] == 300


class TestInitRunIntegration:
    """Integration tests verifying run command works after init."""

    def test_run_command_loads_config_after_init(self, tmp_path: Path) -> None:
        """Test that run command can load configuration after init.

        This verifies that init creates a valid project structure that
        the run command recognizes. The run may fail for other reasons
        (missing claude CLI) but should not fail due to missing config.
        """
        # Initialize project with --no-interactive
        init_result = subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert init_result.returncode == 0

        # Run command - expect it to get past config loading
        # With ADW_MOCK_EXECUTOR set, this uses MockExecutor and exits quickly
        # Timeout ensures we don't hang if something goes wrong
        run_result = subprocess.run(
            [sys.executable, "-m", "adw", "run", "test feature"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,  # Should complete quickly with mock executor
        )

        # Should not complain about missing config or initialization
        combined_output = (run_result.stdout + run_result.stderr).lower()
        assert "not initialized" not in combined_output
        # Check for config-related errors (missing/invalid project.yaml)
        assert "missing project.yaml" not in combined_output
        assert "cannot find project.yaml" not in combined_output
        assert "invalid project.yaml" not in combined_output

    def test_run_help_works_after_init(self, tmp_path: Path) -> None:
        """Test that run --help works in initialized project."""
        # Initialize project with --no-interactive
        subprocess.run(
            [sys.executable, "-m", "adw", "init", "--no-interactive"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        # Run help command
        result = subprocess.run(
            [sys.executable, "-m", "adw", "run", "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "feature" in result.stdout.lower()
