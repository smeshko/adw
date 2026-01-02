"""Configuration loader for ADW.

This module provides the ConfigLoader class that implements three-tier
configuration resolution: project → user → bundled defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import ValidationError as PydanticValidationError

from adw.exceptions import ConfigError
from adw.models import ProjectConfig

if TYPE_CHECKING:
    pass

__all__ = ["ConfigLoader"]


class ConfigLoader:
    """Load and validate ADW project configuration.

    Implements three-tier configuration resolution:
    1. Project config: .adw/project.yaml in project root
    2. User config: ~/.config/adw/config.yaml (future)
    3. Bundled defaults based on detected project type

    Attributes:
        project_root: Path to the project root directory.

    Example:
        >>> from pathlib import Path
        >>> loader = ConfigLoader(project_root=Path("/my/project"))
        >>> config = loader.load()
        >>> print(config.language)
        'python'
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the ConfigLoader.

        Args:
            project_root: Path to project root. Uses cwd if not specified.
        """
        self.project_root = project_root or Path.cwd()

    @property
    def project_config_path(self) -> Path:
        """Get the path to the project config file.

        Returns:
            Path to .adw/project.yaml
        """
        return self.project_root / ".adw" / "project.yaml"

    @property
    def has_project_config(self) -> bool:
        """Check if project config file exists.

        Returns:
            True if .adw/project.yaml exists, False otherwise.
        """
        return self.project_config_path.exists()

    def load(self) -> ProjectConfig:
        """Load configuration using three-tier resolution.

        Resolution order (highest priority first):
        1. Project config (.adw/project.yaml)
        2. User config (~/.config/adw/config.yaml) [future]
        3. Bundled defaults based on detected project type

        Returns:
            Validated ProjectConfig instance.

        Raises:
            ConfigError: If config file exists but is invalid.
        """
        if self.has_project_config:
            return self._load_project_config()

        # Fall back to defaults based on detected project type
        return self._create_default_config()

    def _load_project_config(self) -> ProjectConfig:
        """Load configuration from project config file.

        Returns:
            ProjectConfig loaded from .adw/project.yaml

        Raises:
            ConfigError: If file cannot be parsed or validated.
        """
        try:
            content = self.project_config_path.read_text()
            data = yaml.safe_load(content)

            if data is None:
                raise ConfigError(
                    code="INVALID_CONFIG",
                    message="Configuration file is empty",
                    suggestion="Add required fields: name, language",
                )

            return ProjectConfig.model_validate(data)

        except yaml.YAMLError as e:
            raise ConfigError(
                code="CONFIG_PARSE_ERROR",
                message=f"Failed to parse YAML: {e}",
                suggestion="Check YAML syntax in .adw/project.yaml",
            ) from e

        except PydanticValidationError as e:
            # Extract first error message for user-friendly output
            error_msg = str(e.errors()[0]["msg"]) if e.errors() else str(e)
            raise ConfigError(
                code="INVALID_CONFIG",
                message=f"Configuration validation failed: {error_msg}",
                suggestion="Check required fields: name, language",
            ) from e

    def _create_default_config(self) -> ProjectConfig:
        """Create default configuration based on detected project type.

        Detects project type from filesystem markers and returns
        appropriate default configuration.

        Returns:
            ProjectConfig with sensible defaults.
        """
        # Import here to avoid circular imports
        from adw.config.detector import ProjectTypeDetector

        detector = ProjectTypeDetector()
        project_type = detector.detect(self.project_root)
        defaults = detector.get_defaults(project_type)

        # Create config with detected defaults
        return ProjectConfig(
            name=self.project_root.name,
            language=defaults.get("language", "unknown"),
            test_command=defaults.get("test_command"),
        )
