"""Tests for platform detection.

This module tests the PlatformDetector class for detecting project platform
types from configuration and file markers.
"""

from pathlib import Path

from adw.evidence.detector import PlatformDetector
from adw.models.evidence import Confidence, PlatformType


class TestConfigurationBasedDetection:
    """Tests for configuration-based platform detection (Task 2)."""

    def test_detect_cli_from_config(self, tmp_path: Path) -> None:
        """Test detecting CLI platform from explicit config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-cli-app
language: python
platform: cli
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.CLI
        assert result.confidence == Confidence.HIGH
        assert result.source == "config"

    def test_detect_web_from_config(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from explicit config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-web-app
language: typescript
platform: web
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert result.confidence == Confidence.HIGH
        assert result.source == "config"

    def test_detect_backend_from_config(self, tmp_path: Path) -> None:
        """Test detecting BACKEND platform from explicit config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-api
language: python
platform: backend
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert result.confidence == Confidence.HIGH
        assert result.source == "config"

    def test_config_platform_is_case_insensitive(self, tmp_path: Path) -> None:
        """Test that platform value in config is case insensitive."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-app
language: python
platform: WEB
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB

    def test_invalid_platform_in_config_falls_through(self, tmp_path: Path) -> None:
        """Test that invalid platform value falls through to marker detection."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-app
language: python
platform: invalid-platform
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        # Should fall through to markers or default
        assert result.source != "config"

    def test_no_config_file_falls_through(self, tmp_path: Path) -> None:
        """Test that missing config file falls through to marker detection."""
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        # Should fall through to markers or default
        assert result.source != "config"

    def test_config_without_platform_falls_through(self, tmp_path: Path) -> None:
        """Test that config without platform key falls through."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-app
language: python
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        # Should fall through to markers or default
        assert result.source != "config"

    def test_config_detection_returns_early(self, tmp_path: Path) -> None:
        """Test that explicit config returns immediately without checking markers."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-cli-app
language: python
platform: cli
""")
        # Add web markers that would normally be detected
        (tmp_path / "package.json").write_text('{"dependencies": {"react": "^18.0.0"}}')

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        # Config takes precedence
        assert result.platform == PlatformType.CLI
        assert result.source == "config"
        assert result.markers == []  # No marker detection performed


class TestWebMarkerDetection:
    """Tests for web project marker detection (Task 3)."""

    def test_detect_react_from_package_json(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from React in package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"dependencies": {"react": "^18.0.0"}}')

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert result.source == "markers"
        assert "package.json:react" in result.markers

    def test_detect_vue_from_package_json(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from Vue in package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"dependencies": {"vue": "^3.0.0"}}')

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert "package.json:vue" in result.markers

    def test_detect_angular_from_package_json(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from Angular in package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"dependencies": {"@angular/core": "^17.0.0"}}')

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert "package.json:angular" in result.markers

    def test_detect_svelte_from_package_json(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from Svelte in package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"dependencies": {"svelte": "^4.0.0"}}')

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert "package.json:svelte" in result.markers

    def test_detect_next_config(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from next.config.js."""
        (tmp_path / "next.config.js").write_text("module.exports = {}")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert "next.config.js" in result.markers

    def test_detect_nuxt_config(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from nuxt.config.ts."""
        (tmp_path / "nuxt.config.ts").write_text("export default {}")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert "nuxt.config.ts" in result.markers

    def test_detect_index_html(self, tmp_path: Path) -> None:
        """Test detecting WEB platform from index.html at root."""
        (tmp_path / "index.html").write_text("<!DOCTYPE html>")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert "index.html" in result.markers


class TestBackendMarkerDetection:
    """Tests for backend project marker detection (Task 3)."""

    def test_detect_fastapi_from_main_py(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from FastAPI in main.py."""
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "main.py:fastapi" in result.markers

    def test_detect_flask_from_main_py(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from Flask in main.py."""
        (tmp_path / "main.py").write_text("from flask import Flask\napp = Flask(__name__)")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "main.py:flask" in result.markers

    def test_detect_django_from_main_py(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from Django in main.py."""
        (tmp_path / "main.py").write_text("import django\ndjango.setup()")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "main.py:django" in result.markers

    def test_detect_api_from_app_py(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from API patterns in app.py."""
        (tmp_path / "app.py").write_text('@app.route("/api")\ndef get_data(): pass')

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "app.py:api-pattern" in result.markers

    def test_detect_fastapi_from_requirements(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from FastAPI in requirements.txt."""
        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "requirements.txt:fastapi" in result.markers

    def test_detect_expose_from_dockerfile(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from EXPOSE in Dockerfile."""
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\nEXPOSE 8000")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "Dockerfile:EXPOSE" in result.markers


class TestCliMarkerDetection:
    """Tests for CLI project marker detection (Task 3)."""

    def test_detect_cli_from_pyproject_scripts(self, tmp_path: Path) -> None:
        """Test detecting CLI from [project.scripts] in pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "my-cli"

[project.scripts]
mycli = "mypackage.cli:main"
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.CLI
        assert "pyproject.toml:scripts" in result.markers

    def test_detect_cli_from_setup_py_entry_points(self, tmp_path: Path) -> None:
        """Test detecting CLI from entry_points in setup.py."""
        setup_py = tmp_path / "setup.py"
        setup_py.write_text("""
from setuptools import setup
setup(
    name="my-cli",
    entry_points={
        "console_scripts": ["mycli=mypackage.cli:main"],
    },
)
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.CLI
        assert "setup.py:entry_points" in result.markers

    def test_default_to_cli_when_no_markers(self, tmp_path: Path) -> None:
        """Test defaulting to CLI when no markers found."""
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.CLI
        assert result.source == "default"
        assert result.confidence == Confidence.LOW
