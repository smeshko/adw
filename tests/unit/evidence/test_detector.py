"""Tests for platform detection.

# TEST REDUCTION: Consolidated 31 individual tests into 3 parameterized tests.
# Removed: test_config_platform_is_case_insensitive (trivial Pydantic behavior)
# Consolidated: 7 web framework tests -> 1 parameterized test
# Consolidated: 8 backend framework tests -> 1 parameterized test
# Consolidated: 9 mobile platform tests -> 1 parameterized test
# Net reduction: ~23 tests

This module tests the PlatformDetector class for detecting project platform
types from configuration and file markers.
"""

from pathlib import Path
from typing import Any

import pytest

from adw.evidence import detect_platform, get_evidence_strategy
from adw.evidence.detector import PlatformDetector
from adw.models.evidence import Confidence, EvidenceStrategy, PlatformType


class TestConfigurationBasedDetection:
    """Tests for configuration-based platform detection (Task 2)."""

    @pytest.mark.parametrize(
        "platform,expected_type",
        [
            ("cli", PlatformType.CLI),
            ("web", PlatformType.WEB),
            ("backend", PlatformType.BACKEND),
            ("mobile", PlatformType.MOBILE),
        ],
    )
    def test_detect_platform_from_config(
        self, tmp_path: Path, platform: str, expected_type: PlatformType
    ) -> None:
        """Test detecting platform types from explicit config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(f"""
name: my-app
language: python
platform: {platform}
""")
        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == expected_type
        assert result.confidence == Confidence.HIGH
        assert result.source == "config"

    def test_invalid_platform_in_config_falls_through(self, tmp_path: Path) -> None:
        """Test that invalid platform value falls through to marker detection."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
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
        config_file.parent.mkdir(parents=True, exist_ok=True)
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
        config_file.parent.mkdir(parents=True, exist_ok=True)
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

    @pytest.mark.parametrize(
        "setup,expected_marker",
        [
            pytest.param(
                {"file": "package.json", "content": '{"dependencies": {"react": "^18.0.0"}}'},
                "package.json:react",
                id="react",
            ),
            pytest.param(
                {"file": "package.json", "content": '{"dependencies": {"vue": "^3.0.0"}}'},
                "package.json:vue",
                id="vue",
            ),
            pytest.param(
                {"file": "package.json", "content": '{"dependencies": {"@angular/core": "^17.0.0"}}'},
                "package.json:angular",
                id="angular",
            ),
            pytest.param(
                {"file": "package.json", "content": '{"dependencies": {"svelte": "^4.0.0"}}'},
                "package.json:svelte",
                id="svelte",
            ),
            pytest.param(
                {"file": "next.config.js", "content": "module.exports = {}"},
                "next.config.js",
                id="next-config",
            ),
            pytest.param(
                {"file": "nuxt.config.ts", "content": "export default {}"},
                "nuxt.config.ts",
                id="nuxt-config",
            ),
            pytest.param(
                {"file": "index.html", "content": "<!DOCTYPE html>"},
                "index.html",
                id="index-html",
            ),
        ],
    )
    def test_detect_web_from_markers(
        self, tmp_path: Path, setup: dict[str, Any], expected_marker: str
    ) -> None:
        """Test detecting WEB platform from various file markers."""
        (tmp_path / setup["file"]).write_text(setup["content"])

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.WEB
        assert result.source == "markers"
        assert expected_marker in result.markers


class TestBackendMarkerDetection:
    """Tests for backend project marker detection (Task 3)."""

    @pytest.mark.parametrize(
        "setup,expected_marker",
        [
            pytest.param(
                {"file": "main.py", "content": "from fastapi import FastAPI\napp = FastAPI()"},
                "main.py:fastapi",
                id="fastapi-main",
            ),
            pytest.param(
                {"file": "main.py", "content": "from flask import Flask\napp = Flask(__name__)"},
                "main.py:flask",
                id="flask-main",
            ),
            pytest.param(
                {"file": "main.py", "content": "import django\ndjango.setup()"},
                "main.py:django",
                id="django-main",
            ),
            pytest.param(
                {"file": "app.py", "content": '@app.route("/api")\ndef get_data(): pass'},
                "app.py:api-pattern",
                id="api-pattern",
            ),
            pytest.param(
                {"file": "requirements.txt", "content": "fastapi==0.100.0\nuvicorn"},
                "requirements.txt:fastapi",
                id="fastapi-requirements",
            ),
            pytest.param(
                {"file": "Dockerfile", "content": "FROM python:3.11\nEXPOSE 8000"},
                "Dockerfile:EXPOSE",
                id="dockerfile-expose",
            ),
            pytest.param(
                {
                    "file": "Package.swift",
                    "content": """
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
""",
                },
                "Package.swift:vapor",
                id="vapor-package-swift",
            ),
            pytest.param(
                {
                    "file": "Package.swift",
                    "content": 'let package = Package(\n    dependencies: [.package(name: "vapor", url: "...")]\n)',
                },
                "Package.swift:vapor",
                id="vapor-quoted-name",
            ),
        ],
    )
    def test_detect_backend_from_markers(
        self, tmp_path: Path, setup: dict[str, Any], expected_marker: str
    ) -> None:
        """Test detecting BACKEND platform from various file markers."""
        (tmp_path / setup["file"]).write_text(setup["content"])

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.BACKEND
        assert result.source == "markers"
        assert expected_marker in result.markers


class TestMobileMarkerDetection:
    """Tests for mobile project marker detection."""

    @pytest.mark.parametrize(
        "setup_fn,expected_marker",
        [
            pytest.param(
                lambda p: (p / "MyApp.xcodeproj").mkdir() or (p / "MyApp.xcodeproj" / "project.pbxproj").write_text("// project file"),
                "MyApp.xcodeproj:ios",
                id="ios-xcodeproj",
            ),
            pytest.param(
                lambda p: (p / "MyApp.xcworkspace").mkdir(),
                "MyApp.xcworkspace:ios",
                id="ios-xcworkspace",
            ),
            pytest.param(
                lambda p: (p / "Info.plist").write_text(
                    '<?xml version="1.0"?>\n<plist><dict><key>CFBundleIdentifier</key><string>com.example</string></dict></plist>'
                ),
                "Info.plist:ios",
                id="ios-info-plist-root",
            ),
            pytest.param(
                lambda p: (p / "MyApp").mkdir() or (p / "MyApp" / "Info.plist").write_text("<plist><dict></dict></plist>"),
                "Info.plist:ios",
                id="ios-info-plist-subdir",
            ),
            pytest.param(
                lambda p: (
                    (p / "app" / "src" / "main").mkdir(parents=True),
                    (p / "app" / "src" / "main" / "AndroidManifest.xml").write_text("<manifest />"),
                    (p / "build.gradle").write_text("plugins { id 'android' }"),
                ),
                "AndroidManifest.xml:android",
                id="android-manifest-gradle",
            ),
            pytest.param(
                lambda p: (
                    (p / "AndroidManifest.xml").write_text("<manifest />"),
                    (p / "build.gradle.kts").write_text("plugins { kotlin('android') }"),
                ),
                "AndroidManifest.xml:android",
                id="android-gradle-kts",
            ),
            pytest.param(
                lambda p: (p / "pubspec.yaml").write_text(
                    "name: my_flutter_app\ndependencies:\n  flutter:\n    sdk: flutter\n"
                ),
                "pubspec.yaml:flutter",
                id="flutter-pubspec",
            ),
        ],
    )
    def test_detect_mobile_from_markers(
        self, tmp_path: Path, setup_fn: Any, expected_marker: str
    ) -> None:
        """Test detecting MOBILE platform from various file markers."""
        setup_fn(tmp_path)

        detector = PlatformDetector(tmp_path)
        result = detector.detect()

        assert result.platform == PlatformType.MOBILE
        assert result.source == "markers"
        assert expected_marker in result.markers

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
        config_file.parent.mkdir(parents=True, exist_ok=True)
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

    @pytest.mark.parametrize(
        "platform,expected_strategy",
        [
            (PlatformType.CLI, EvidenceStrategy.TERMINAL_OUTPUT),
            (PlatformType.WEB, EvidenceStrategy.SCREENSHOT),
            (PlatformType.BACKEND, EvidenceStrategy.API_CAPTURE),
            (PlatformType.MOBILE, EvidenceStrategy.SCREENSHOT),
            (PlatformType.UNKNOWN, EvidenceStrategy.TERMINAL_OUTPUT),
        ],
    )
    def test_platform_maps_to_strategy(
        self, platform: PlatformType, expected_strategy: EvidenceStrategy
    ) -> None:
        """Test that each platform maps to correct evidence strategy."""
        strategy = get_evidence_strategy(platform)
        assert strategy == expected_strategy


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
        config_file.parent.mkdir(parents=True, exist_ok=True)
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
