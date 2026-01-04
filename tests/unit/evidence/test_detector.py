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
