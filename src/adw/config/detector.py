"""Project type detection for ADW.

This module provides auto-detection of project types based on marker files
(e.g., pyproject.toml for Python, package.json for Node.js).
"""

from pathlib import Path


class ProjectTypeDetector:
    """Detect project type from file markers.

    Examines the project directory for known marker files and returns
    the detected project type with appropriate defaults.

    Example:
        >>> detector = ProjectTypeDetector()
        >>> project_type = detector.detect(Path("/path/to/project"))
        >>> defaults = detector.get_defaults(project_type)
    """

    # Marker files mapped to project types
    # Order matters - first match wins
    MARKERS: list[tuple[str, str]] = [
        ("pyproject.toml", "python"),
        ("setup.py", "python"),
        ("requirements.txt", "python"),
        ("package.json", "javascript"),
        ("go.mod", "go"),
        ("Cargo.toml", "rust"),
        ("build.gradle", "java"),
        ("pom.xml", "java"),
        ("Gemfile", "ruby"),
        ("composer.json", "php"),
    ]

    # Default configurations for each project type
    DEFAULTS: dict[str, dict[str, str | None]] = {
        "python": {
            "language": "python",
            "test_command": "pytest",
            "build_command": None,
        },
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
        "unknown": {
            "language": "unknown",
            "test_command": None,
            "build_command": None,
        },
        # Alias for backward compatibility with ConfigLoader
        "generic": {
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
            Detected project type (e.g., "python", "javascript").
            Returns "unknown" if no markers are found.
        """
        for marker, project_type in self.MARKERS:
            if (project_root / marker).exists():
                return project_type
        return "unknown"

    def get_defaults(self, project_type: str) -> dict[str, str | None]:
        """Get default configuration for a project type.

        Args:
            project_type: The project type (e.g., "python", "go").

        Returns:
            Dictionary with language, test_command, and build_command defaults.
        """
        return self.DEFAULTS.get(project_type, self.DEFAULTS["unknown"]).copy()
