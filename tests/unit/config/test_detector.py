"""Unit tests for ProjectTypeDetector class.

Tests for project type detection based on filesystem markers.
"""

import pytest

from adw.config.detector import ProjectType, ProjectTypeDetector


class TestProjectTypeDetector:
    """Tests for ProjectTypeDetector class."""

    def test_detect_python_via_pyproject_toml(self, tmp_path) -> None:
        """Test Python detection via pyproject.toml."""
        (tmp_path / "pyproject.toml").touch()

        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        assert result == "python"

    def test_detect_python_via_setup_py(self, tmp_path) -> None:
        """Test Python detection via setup.py."""
        (tmp_path / "setup.py").touch()

        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        assert result == "python"

    def test_detect_python_via_requirements_txt(self, tmp_path) -> None:
        """Test Python detection via requirements.txt."""
        (tmp_path / "requirements.txt").touch()

        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        assert result == "python"

    def test_detect_nodejs_via_package_json(self, tmp_path) -> None:
        """Test Node.js detection via package.json."""
        (tmp_path / "package.json").touch()

        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        assert result == "nodejs"

    def test_detect_go_via_go_mod(self, tmp_path) -> None:
        """Test Go detection via go.mod."""
        (tmp_path / "go.mod").touch()

        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        assert result == "go"

    def test_detect_generic_when_no_markers(self, tmp_path) -> None:
        """Test generic detection when no markers found."""
        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        assert result == "generic"

    def test_python_priority_over_nodejs(self, tmp_path) -> None:
        """Test that Python is detected first when both markers exist."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()

        detector = ProjectTypeDetector()
        result = detector.detect(tmp_path)

        # Python markers are checked first
        assert result == "python"

    def test_get_defaults_python(self) -> None:
        """Test default values for Python projects."""
        detector = ProjectTypeDetector()
        defaults = detector.get_defaults("python")

        assert defaults["language"] == "python"
        assert defaults["test_command"] == "pytest"

    def test_get_defaults_nodejs(self) -> None:
        """Test default values for Node.js projects."""
        detector = ProjectTypeDetector()
        defaults = detector.get_defaults("nodejs")

        assert defaults["language"] == "javascript"
        assert defaults["test_command"] == "npm test"

    def test_get_defaults_go(self) -> None:
        """Test default values for Go projects."""
        detector = ProjectTypeDetector()
        defaults = detector.get_defaults("go")

        assert defaults["language"] == "go"
        assert defaults["test_command"] == "go test ./..."

    def test_get_defaults_generic(self) -> None:
        """Test default values for generic projects."""
        detector = ProjectTypeDetector()
        defaults = detector.get_defaults("generic")

        assert defaults["language"] == "unknown"
        assert defaults["test_command"] is None

    def test_markers_class_attribute(self) -> None:
        """Test that MARKERS includes expected project types."""
        assert "python" in ProjectTypeDetector.MARKERS
        assert "nodejs" in ProjectTypeDetector.MARKERS
        assert "go" in ProjectTypeDetector.MARKERS

    def test_defaults_class_attribute(self) -> None:
        """Test that DEFAULTS includes all project types."""
        assert "python" in ProjectTypeDetector.DEFAULTS
        assert "nodejs" in ProjectTypeDetector.DEFAULTS
        assert "go" in ProjectTypeDetector.DEFAULTS
        assert "generic" in ProjectTypeDetector.DEFAULTS
