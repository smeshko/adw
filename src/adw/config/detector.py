"""Project type detection for ADW.

This module provides the ProjectTypeDetector class that detects
project type from filesystem markers and provides sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

__all__ = ["ProjectTypeDetector", "ProjectType"]

ProjectType = Literal["python", "nodejs", "go", "generic"]


class ProjectTypeDetector:
    """Detect project type from filesystem markers.

    Examines the project directory for common files that indicate
    the project type (e.g., pyproject.toml for Python, package.json
    for Node.js).

    Attributes:
        MARKERS: Mapping of project types to their marker files.
        DEFAULTS: Default configuration values for each project type.

    Example:
        >>> from pathlib import Path
        >>> detector = ProjectTypeDetector()
        >>> project_type = detector.detect(Path("/my/python/project"))
        >>> print(project_type)
        'python'
        >>> defaults = detector.get_defaults(project_type)
        >>> print(defaults)
        {'language': 'python', 'test_command': 'pytest'}
    """

    MARKERS: dict[str, list[str]] = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt"],
        "nodejs": ["package.json"],
        "go": ["go.mod"],
    }

    DEFAULTS: dict[str, dict[str, str | None]] = {
        "python": {"language": "python", "test_command": "pytest"},
        "nodejs": {"language": "javascript", "test_command": "npm test"},
        "go": {"language": "go", "test_command": "go test ./..."},
        "generic": {"language": "unknown", "test_command": None},
    }

    def detect(self, project_root: Path) -> ProjectType:
        """Detect project type from directory.

        Checks for marker files in order of MARKERS dict.
        Returns "generic" if no known project type detected.

        Args:
            project_root: Path to project root directory.

        Returns:
            Detected project type.
        """
        for project_type, markers in self.MARKERS.items():
            for marker in markers:
                if (project_root / marker).exists():
                    return project_type  # type: ignore[return-value]
        return "generic"

    def get_defaults(self, project_type: ProjectType) -> dict[str, str | None]:
        """Get default config values for project type.

        Args:
            project_type: The detected project type.

        Returns:
            Dictionary of default configuration values.
        """
        return self.DEFAULTS.get(project_type, self.DEFAULTS["generic"])
