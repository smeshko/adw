"""Project type detection for ADW.

This module provides auto-detection of project types based on marker files
(e.g., pyproject.toml for Python, package.json for Node.js).
"""

from pathlib import Path
from typing import Literal

# Type alias for project types
ProjectType = Literal[
    "python",
    "nodejs",
    "javascript",
    "go",
    "rust",
    "java",
    "ruby",
    "php",
    "unknown",
    "generic",
]


class ProjectTypeDetector:
    """Detect project type from file markers.

    Examines the project directory for known marker files and returns
    the detected project type with appropriate defaults.

    Example:
        >>> detector = ProjectTypeDetector()
        >>> project_type = detector.detect(Path("/path/to/project"))
        >>> defaults = detector.get_defaults(project_type)
    """

    # Marker files mapped to project types (dict format for compatibility)
    MARKERS: dict[str, list[str]] = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt"],
        "nodejs": ["package.json"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
        "java": ["build.gradle", "pom.xml"],
        "ruby": ["Gemfile"],
        "php": ["composer.json"],
    }

    # Default configurations for each project type
    DEFAULTS: dict[str, dict[str, str | None]] = {
        "python": {
            "language": "python",
            "test_command": "pytest",
            "build_command": None,
        },
        "nodejs": {
            "language": "javascript",
            "test_command": "npm test",
            "build_command": "npm run build",
        },
        # Alias for tests that use "javascript" directly
        "javascript": {
            "language": "javascript",
            "test_command": "npm test",
            "build_command": "npm run build",
        },
        "go": {
            "language": "go",
            "test_command": "go test ./...",
            "build_command": "go build",
        },
        "rust": {
            "language": "rust",
            "test_command": "cargo test",
            "build_command": "cargo build",
        },
        "java": {
            "language": "java",
            "test_command": "gradle test",
            "build_command": "gradle build",
        },
        "ruby": {
            "language": "ruby",
            "test_command": "bundle exec rspec",
            "build_command": None,
        },
        "php": {
            "language": "php",
            "test_command": "vendor/bin/phpunit",
            "build_command": None,
        },
        "generic": {
            "language": "unknown",
            "test_command": None,
            "build_command": None,
        },
        # Alias for backward compatibility
        "unknown": {
            "language": "unknown",
            "test_command": None,
            "build_command": None,
        },
    }

    def detect(self, project_root: Path) -> str:
        """Detect project type from marker files.

        Args:
            project_root: Path to the project root directory.

        Returns:
            Detected project type (e.g., "python", "nodejs").
            Returns "generic" if no markers are found.
        """
        for project_type, markers in self.MARKERS.items():
            for marker in markers:
                if (project_root / marker).exists():
                    return project_type
        return "generic"

    def get_defaults(self, project_type: str) -> dict[str, str | None]:
        """Get default configuration for a project type.

        Args:
            project_type: The project type (e.g., "python", "go").

        Returns:
            Dictionary with language, test_command, and build_command defaults.
        """
        return self.DEFAULTS.get(project_type, self.DEFAULTS["generic"]).copy()
