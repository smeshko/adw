"""Tests for platform detection.

This module tests the PlatformDetector class for detecting project platform
types from configuration and file markers.
"""

from pathlib import Path

from adw.evidence import detect_platform, get_evidence_strategy
from adw.evidence.detector import PlatformDetector
from adw.models.evidence import Confidence, EvidenceStrategy, PlatformType


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

    def test_detect_mobile_from_config(self, tmp_path: Path) -> None:
        """Test detecting MOBILE platform from explicit config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: my-ios-app
language: swift
platform: mobile
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
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
        content = "from fastapi import FastAPI\napp = FastAPI()"
        (tmp_path / "main.py").write_text(content)

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "main.py:fastapi" in result.markers

    def test_detect_flask_from_main_py(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from Flask in main.py."""
        content = "from flask import Flask\napp = Flask(__name__)"
        (tmp_path / "main.py").write_text(content)

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

    def test_detect_vapor_from_package_swift(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from Vapor in Package.swift."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text("""
// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "MyApp",
    dependencies: [
        .package(url: "https://github.com/vapor/vapor.git", from: "4.76.0"),
    ],
    targets: [
        .executableTarget(name: "App", dependencies: ["Vapor"])
    ]
)
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "Package.swift:vapor" in result.markers

    def test_detect_vapor_with_quoted_name(self, tmp_path: Path) -> None:
        """Test detecting BACKEND from Vapor with quoted dependency name."""
        package_swift = tmp_path / "Package.swift"
        package_swift.write_text("""
let package = Package(
    dependencies: [.package(name: "vapor", url: "...")]
)
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "Package.swift:vapor" in result.markers


class TestMobileMarkerDetection:
    """Tests for mobile project marker detection."""

    def test_detect_ios_from_xcodeproj(self, tmp_path: Path) -> None:
        """Test detecting MOBILE from .xcodeproj directory."""
        xcodeproj = tmp_path / "MyApp.xcodeproj"
        xcodeproj.mkdir()
        (xcodeproj / "project.pbxproj").write_text("// project file")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "MyApp.xcodeproj:ios" in result.markers

    def test_detect_ios_from_xcworkspace(self, tmp_path: Path) -> None:
        """Test detecting MOBILE from .xcworkspace directory."""
        xcworkspace = tmp_path / "MyApp.xcworkspace"
        xcworkspace.mkdir()

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "MyApp.xcworkspace:ios" in result.markers

    def test_detect_ios_from_info_plist_at_root(self, tmp_path: Path) -> None:
        """Test detecting MOBILE from Info.plist at project root."""
        info_plist = tmp_path / "Info.plist"
        info_plist.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.example.myapp</string>
</dict>
</plist>
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "Info.plist:ios" in result.markers

    def test_detect_ios_from_info_plist_in_subdirectory(self, tmp_path: Path) -> None:
        """Test detecting MOBILE from Info.plist in app subdirectory."""
        app_dir = tmp_path / "MyApp"
        app_dir.mkdir()
        info_plist = app_dir / "Info.plist"
        info_plist.write_text("<plist><dict></dict></plist>")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "Info.plist:ios" in result.markers

    def test_detect_android_from_manifest_and_gradle(self, tmp_path: Path) -> None:
        """Test detecting MOBILE from AndroidManifest.xml and build.gradle."""
        # Create Android project structure
        app_dir = tmp_path / "app" / "src" / "main"
        app_dir.mkdir(parents=True)
        (app_dir / "AndroidManifest.xml").write_text("<manifest />")
        (tmp_path / "build.gradle").write_text("plugins { id 'android' }")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "AndroidManifest.xml:android" in result.markers

    def test_detect_android_with_gradle_kts(self, tmp_path: Path) -> None:
        """Test detecting MOBILE with build.gradle.kts."""
        (tmp_path / "AndroidManifest.xml").write_text("<manifest />")
        (tmp_path / "build.gradle.kts").write_text("plugins { kotlin('android') }")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "AndroidManifest.xml:android" in result.markers

    def test_detect_flutter_from_pubspec(self, tmp_path: Path) -> None:
        """Test detecting MOBILE from pubspec.yaml with flutter SDK."""
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("""
name: my_flutter_app
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert "pubspec.yaml:flutter" in result.markers

    def test_pure_dart_pubspec_not_detected_as_mobile(self, tmp_path: Path) -> None:
        """Test that pubspec.yaml without flutter SDK is not detected as MOBILE."""
        pubspec = tmp_path / "pubspec.yaml"
        pubspec.write_text("""
name: my_dart_package
dependencies:
  http: ^0.13.0
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        # Should fall through to default CLI since no mobile markers
        assert result.platform == PlatformType.CLI
        assert result.source == "default"

    def test_android_requires_both_manifest_and_gradle(self, tmp_path: Path) -> None:
        """Test that AndroidManifest.xml alone is not enough for MOBILE detection."""
        (tmp_path / "AndroidManifest.xml").write_text("<manifest />")
        # No build.gradle

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        # Should fall through to default CLI
        assert result.platform == PlatformType.CLI


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


class TestConfidenceScoring:
    """Tests for confidence scoring (Task 4)."""

    def test_single_marker_medium_confidence(self, tmp_path: Path) -> None:
        """Test that single marker results in MEDIUM confidence."""
        (tmp_path / "index.html").write_text("<!DOCTYPE html>")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert result.confidence == Confidence.MEDIUM
        assert len(result.markers) == 1

    def test_multiple_markers_high_confidence(self, tmp_path: Path) -> None:
        """Test that multiple markers result in HIGH confidence."""
        (tmp_path / "package.json").write_text('{"dependencies": {"react": "^18"}}')
        (tmp_path / "next.config.js").write_text("module.exports = {}")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert result.confidence == Confidence.HIGH
        assert len(result.markers) >= 2

    def test_config_always_high_confidence(self, tmp_path: Path) -> None:
        """Test that config-based detection always has HIGH confidence."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("name: test\nlanguage: python\nplatform: backend")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert result.confidence == Confidence.HIGH
        assert result.source == "config"

    def test_default_low_confidence(self, tmp_path: Path) -> None:
        """Test that default CLI has LOW confidence."""
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.CLI
        assert result.confidence == Confidence.LOW
        assert result.source == "default"

    def test_markers_included_in_result(self, tmp_path: Path) -> None:
        """Test that all detected markers are included in result."""
        (tmp_path / "main.py").write_text("from fastapi import FastAPI")
        (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn")

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert "main.py:fastapi" in result.markers
        assert "requirements.txt:fastapi" in result.markers
        assert len(result.markers) == 2


class TestEvidenceStrategyFactory:
    """Tests for get_evidence_strategy factory function (Task 5)."""

    def test_cli_maps_to_terminal_output(self) -> None:
        """Test that CLI platform maps to TERMINAL_OUTPUT strategy."""
        strategy = get_evidence_strategy(PlatformType.CLI)
        assert strategy == EvidenceStrategy.TERMINAL_OUTPUT

    def test_web_maps_to_screenshot(self) -> None:
        """Test that WEB platform maps to SCREENSHOT strategy."""
        strategy = get_evidence_strategy(PlatformType.WEB)
        assert strategy == EvidenceStrategy.SCREENSHOT

    def test_backend_maps_to_api_capture(self) -> None:
        """Test that BACKEND platform maps to API_CAPTURE strategy."""
        strategy = get_evidence_strategy(PlatformType.BACKEND)
        assert strategy == EvidenceStrategy.API_CAPTURE

    def test_mobile_maps_to_screenshot(self) -> None:
        """Test that MOBILE platform maps to SCREENSHOT strategy."""
        strategy = get_evidence_strategy(PlatformType.MOBILE)
        assert strategy == EvidenceStrategy.SCREENSHOT

    def test_unknown_maps_to_terminal_output(self) -> None:
        """Test that UNKNOWN platform maps to TERMINAL_OUTPUT strategy."""
        strategy = get_evidence_strategy(PlatformType.UNKNOWN)
        assert strategy == EvidenceStrategy.TERMINAL_OUTPUT


class TestDetectPlatformConvenience:
    """Tests for detect_platform convenience function (Task 5)."""

    def test_detect_platform_returns_result(self, tmp_path: Path) -> None:
        """Test that detect_platform returns a valid result."""
        result = detect_platform(tmp_path)
        assert result.platform == PlatformType.CLI
        assert result.source == "default"

    def test_detect_platform_with_config(self, tmp_path: Path) -> None:
        """Test detect_platform with explicit config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("name: test\nlanguage: python\nplatform: web")

        result = detect_platform(tmp_path)
        assert result.platform == PlatformType.WEB
        assert result.source == "config"

    def test_detect_platform_with_markers(self, tmp_path: Path) -> None:
        """Test detect_platform with file markers."""
        (tmp_path / "package.json").write_text('{"dependencies": {"react": "^18"}}')

        result = detect_platform(tmp_path)
        assert result.platform == PlatformType.WEB
        assert result.source == "markers"


class TestWarningEmission:
    """Tests for warning emission on UNKNOWN platform (Task 5)."""

    def test_unknown_platform_emits_warning(self) -> None:
        """Test that UNKNOWN platform emits a warning when getting strategy."""
        from unittest.mock import MagicMock, patch

        # Mock the logger
        with patch("adw.evidence.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # Call get_evidence_strategy with UNKNOWN - re-import to use patched logger
            from adw.evidence import get_evidence_strategy as get_strategy
            from adw.models.evidence import PlatformType as PType

            strategy = get_strategy(PType.UNKNOWN)

            # Verify strategy is TERMINAL_OUTPUT
            assert strategy == EvidenceStrategy.TERMINAL_OUTPUT

            # Verify warning was logged
            mock_logger.warn.assert_called_once()
            call_args = mock_logger.warn.call_args
            # Check the message contains expected text
            assert "Platform could not be determined" in call_args[0][1]
