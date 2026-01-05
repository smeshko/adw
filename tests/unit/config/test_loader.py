"""Unit tests for ConfigLoader class.

Tests for the three-tier configuration loading system:
- Project config (.adw/project.yaml)
- User config (~/.config/adw/config.yaml)
- Bundled defaults
"""

import pytest

from adw.config.loader import ConfigLoader
from adw.exceptions import ConfigError
from adw.models import ProjectConfig


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_init_with_default_project_root(self) -> None:
        """Test ConfigLoader uses current directory by default."""
        loader = ConfigLoader()
        assert loader.project_root.exists()

    def test_init_with_custom_project_root(self, tmp_path) -> None:
        """Test ConfigLoader accepts custom project root."""
        loader = ConfigLoader(project_root=tmp_path)
        assert loader.project_root == tmp_path

    def test_load_from_project_config(self, tmp_path) -> None:
        """Test loading config from .adw/project.yaml."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: my-test-project
language: python
test_command: pytest --cov
framework: fastapi
        """)

        loader = ConfigLoader(project_root=tmp_path)
        config = loader.load()

        assert isinstance(config, ProjectConfig)
        assert config.name == "my-test-project"
        assert config.language == "python"
        assert config.test_command == "pytest --cov"
        assert config.framework == "fastapi"

    def test_load_uses_defaults_when_no_project_config(self, tmp_path) -> None:
        """Test fallback to defaults when no .adw/project.yaml exists."""
        # Create pyproject.toml to trigger Python detection
        (tmp_path / "pyproject.toml").touch()

        loader = ConfigLoader(project_root=tmp_path)
        config = loader.load()

        assert isinstance(config, ProjectConfig)
        # Should use detected project type defaults
        assert config.language == "python"
        assert config.test_command == "pytest"

    def test_load_with_invalid_config_raises_error(self, tmp_path) -> None:
        """Test that invalid config file raises ConfigError."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
# Missing required fields
framework: fastapi
        """)

        loader = ConfigLoader(project_root=tmp_path)

        with pytest.raises(ConfigError) as exc_info:
            loader.load()

        assert exc_info.value.code == "INVALID_CONFIG"

    def test_load_with_malformed_yaml_raises_error(self, tmp_path) -> None:
        """Test that malformed YAML raises ConfigError."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: test
  bad indent: value
        """)

        loader = ConfigLoader(project_root=tmp_path)

        with pytest.raises(ConfigError) as exc_info:
            loader.load()

        assert exc_info.value.code in ("INVALID_CONFIG", "CONFIG_PARSE_ERROR")

    def test_project_config_path(self, tmp_path) -> None:
        """Test project_config_path property returns correct path."""
        loader = ConfigLoader(project_root=tmp_path)
        expected = tmp_path / ".adw" / "project.yaml"
        assert loader.project_config_path == expected

    def test_has_project_config_returns_true_when_exists(self, tmp_path) -> None:
        """Test has_project_config returns True when file exists."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "project.yaml").write_text("name: test\nlanguage: python")

        loader = ConfigLoader(project_root=tmp_path)
        assert loader.has_project_config is True

    def test_has_project_config_returns_false_when_missing(self, tmp_path) -> None:
        """Test has_project_config returns False when file missing."""
        loader = ConfigLoader(project_root=tmp_path)
        assert loader.has_project_config is False

    def test_load_returns_immutable_config(self, tmp_path) -> None:
        """Test that config modifications don't affect future loads."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: test-project
language: python
        """)

        loader = ConfigLoader(project_root=tmp_path)
        config1 = loader.load()
        config2 = loader.load()

        # Each load should return a fresh config
        assert config1 is not config2
        assert config1.name == config2.name
