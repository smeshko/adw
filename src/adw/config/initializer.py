"""Project initialization for ADW.

This module provides the ProjectInitializer class that creates the .adw/
directory structure and generates project configuration.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from adw.config.detector import ProjectTypeDetector
from adw.config.registry import ConfigRegistry
from adw.config.yaml_generator import YAMLWithComments
from adw.models.wizard import WizardState


def generate_gitignore() -> str:
    """Generate .gitignore content for the .adw directory.

    Returns:
        Gitignore file content.
    """
    return """# ADW runtime artifacts
runs/
logs/
*.log
state.json

# Environment files with secrets
.env
"""


def generate_env_template() -> str:
    """Generate .env.template content for credential setup.

    Returns:
        Environment template file content with placeholder credentials.
    """
    return """\
# ADW Credentials
# Copy this file to .env and fill in your values
# The .env file is gitignored and will NOT be committed

# Linear Task Manager (required if using linear task manager)
# Get your API key from: Linear Settings > API > Personal API keys
LINEAR_API_KEY=

# Linear Team ID (UUID format)
# Find via: Linear Settings > Workspace > Copy team ID
LINEAR_TEAM_ID=
"""


class ProjectInitializer:
    """Initialize ADW project structure.

    Creates the .adw/ directory with configuration files and subdirectories
    based on auto-detected or specified project type.

    Attributes:
        project_root: Path to the project root directory.
        adw_dir: Path to the .adw/ directory.

    Example:
        >>> initializer = ProjectInitializer(Path("/path/to/project"))
        >>> config = initializer.initialize(project_type="python")
    """

    def __init__(self, project_root: Path) -> None:
        """Initialize the ProjectInitializer.

        Args:
            project_root: Path to the project root directory.
        """
        self.project_root = project_root
        self.adw_dir = project_root / ".adw"

    def initialize(
        self,
        project_type: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Initialize ADW project.

        Creates the .adw/ directory structure and generates configuration
        based on the specified project type.

        Args:
            project_type: Detected or specified project type.
            force: If True, overwrite existing configuration.

        Returns:
            Generated configuration dictionary with language, test_command, etc.
        """
        # Backup existing if force
        if self.adw_dir.exists() and force:
            self._backup_existing()

        # Create directory structure
        self._create_directories()

        # Generate config
        config = self._generate_config(project_type)

        # Write files
        self._write_config(config)
        self._write_gitignore()
        self._write_env_template()

        return config

    def _create_directories(self) -> None:
        """Create .adw/ directory structure."""
        self.adw_dir.mkdir(exist_ok=True)
        (self.adw_dir / "runs").mkdir(exist_ok=True)
        (self.adw_dir / "commands").mkdir(exist_ok=True)

    def _generate_config(self, project_type: str) -> dict[str, Any]:
        """Generate configuration based on project type.

        Args:
            project_type: The project type (e.g., "python", "javascript").

        Returns:
            Configuration dictionary with language, test_command, build_command.
        """
        detector = ProjectTypeDetector()
        defaults = detector.get_defaults(project_type)

        return {
            "language": defaults.get("language", "unknown"),
            "test_command": defaults.get("test_command"),
            "build_command": defaults.get("build_command"),
        }

    def _write_config(self, config: dict[str, Any]) -> None:
        """Write project.yaml configuration file.

        Args:
            config: Configuration dictionary to write.
        """
        state = WizardState()
        state.update_config(
            "basics", {"project_name": self.project_root.name, **config}
        )
        config_content = YAMLWithComments(ConfigRegistry()).generate_project_yaml(state)

        config_path = self.adw_dir / "project.yaml"
        config_path.write_text(config_content)

    def _write_gitignore(self) -> None:
        """Write .gitignore for .adw/ directory."""
        gitignore_path = self.adw_dir / ".gitignore"
        gitignore_path.write_text(generate_gitignore())

    def _write_env_template(self) -> None:
        """Write .env.template for credential setup guidance."""
        env_template_path = self.adw_dir / ".env.template"
        env_template_path.write_text(generate_env_template())

    def _backup_existing(self) -> None:
        """Backup existing .adw/ configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / f".adw.backup.{timestamp}"

        # Handle collision if backup dir already exists (multiple --force)
        counter = 1
        while backup_dir.exists():
            backup_dir = self.project_root / f".adw.backup.{timestamp}.{counter}"
            counter += 1

        shutil.move(str(self.adw_dir), str(backup_dir))
