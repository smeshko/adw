"""Platform detection for evidence gathering.

This module provides the PlatformDetector class that determines the
project platform type (CLI, WEB, MOBILE, BACKEND) from configuration or
file markers.
"""

import json
import re
from pathlib import Path

import yaml

from adw.logging import LogCategory, get_logger
from adw.models.evidence import Confidence, PlatformDetectionResult, PlatformType

# Web framework markers in package.json
WEB_FRAMEWORKS = ["react", "vue", "@angular/core", "svelte", "solid-js", "preact"]

# Backend framework markers in Python files
BACKEND_FRAMEWORKS = ["fastapi", "flask", "django", "starlette", "aiohttp"]

# API route patterns
API_PATTERNS = [
    r"@app\.route\s*\(['\"].*api",
    r"@router\.",
    r"app\.get\s*\(",
    r"app\.post\s*\(",
]


class PlatformDetector:
    """Detects the platform type for a project.

    The detector uses a priority-based approach:
    1. Explicit configuration in .adw/project.yaml (highest priority)
    2. File markers (package.json, pyproject.toml, etc.)
    3. Default to CLI with warning (lowest priority)

    Attributes:
        project_root: Path to the project root directory

    Example:
        >>> detector = PlatformDetector(Path("/path/to/project"))
        >>> result = detector.detect()
        >>> result.platform
        <PlatformType.WEB: 'web'>
    """

    CONFIG_FILE = ".adw/project.yaml"

    def __init__(self, project_root: Path) -> None:
        """Initialize the platform detector.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self._logger = get_logger()

    def detect(self) -> PlatformDetectionResult:
        """Detect the platform type for the project.

        Attempts detection in priority order:
        1. Explicit config (returns immediately if found)
        2. File markers (analyzed for confidence scoring)
        3. Default to CLI with low confidence

        Returns:
            PlatformDetectionResult with detected platform and metadata
        """
        self._logger.debug(
            LogCategory.STATE,
            f"Starting platform detection for {self.project_root}",
        )

        # Priority 1: Check explicit configuration
        config_result = self._detect_from_config()
        if config_result is not None:
            self._log_detection_result(config_result)
            return config_result

        # Priority 2: Check file markers
        marker_result = self._detect_from_markers()
        if marker_result is not None:
            self._log_detection_result(marker_result)
            return marker_result

        # Priority 3: Default to CLI
        default_result = self._get_default_result()
        self._log_detection_result(default_result)
        return default_result

    def _log_detection_result(self, result: PlatformDetectionResult) -> None:
        """Log the detection result with all markers for debugging.

        Args:
            result: The platform detection result to log
        """
        markers_str = ", ".join(result.markers) if result.markers else "none"
        self._logger.info(
            LogCategory.STATE,
            f"Platform detected: {result.platform.value} "
            f"(confidence={result.confidence.value}, source={result.source}, "
            f"markers=[{markers_str}])",
        )

    def _detect_from_config(self) -> PlatformDetectionResult | None:
        """Attempt to detect platform from configuration file.

        Returns:
            PlatformDetectionResult if config specifies valid platform, None otherwise
        """
        config_path = self.project_root / self.CONFIG_FILE
        if not config_path.exists():
            return None

        try:
            content = config_path.read_text()
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                return None

            platform_value = data.get("platform")
            if platform_value is None:
                return None

            # Normalize to lowercase for case-insensitive matching
            platform_str = str(platform_value).lower()

            # Validate against PlatformType enum
            try:
                platform = PlatformType(platform_str)
            except ValueError:
                # Invalid platform value - fall through to marker detection
                return None

            return PlatformDetectionResult(
                platform=platform,
                confidence=Confidence.HIGH,
                source="config",
                markers=[],
            )
        except (yaml.YAMLError, OSError):
            # Config file exists but couldn't be parsed - fall through
            return None

    def _detect_from_markers(self) -> PlatformDetectionResult | None:
        """Attempt to detect platform from file markers.

        Checks for (in priority order):
        - Web markers: package.json with frameworks, next/nuxt config, index.html
        - Mobile markers: .xcodeproj/.xcworkspace, AndroidManifest.xml, pubspec.yaml
        - Backend markers: main.py/app.py with frameworks, requirements.txt, Dockerfile
        - CLI markers: pyproject.toml scripts, setup.py entry_points

        Returns:
            PlatformDetectionResult if markers found, None otherwise
        """
        markers: list[str] = []

        # Check for web markers
        web_markers = self._detect_web_markers()
        if web_markers:
            markers.extend(web_markers)
            return PlatformDetectionResult(
                platform=PlatformType.WEB,
                confidence=self._calculate_confidence(markers),
                source="markers",
                markers=markers,
            )

        # Check for mobile markers (iOS, Android, Flutter)
        mobile_markers = self._detect_mobile_markers()
        if mobile_markers:
            markers.extend(mobile_markers)
            return PlatformDetectionResult(
                platform=PlatformType.MOBILE,
                confidence=self._calculate_confidence(markers),
                source="markers",
                markers=markers,
            )

        # Check for backend markers
        backend_markers = self._detect_backend_markers()
        if backend_markers:
            markers.extend(backend_markers)
            return PlatformDetectionResult(
                platform=PlatformType.BACKEND,
                confidence=self._calculate_confidence(markers),
                source="markers",
                markers=markers,
            )

        # Check for CLI markers
        cli_markers = self._detect_cli_markers()
        if cli_markers:
            markers.extend(cli_markers)
            return PlatformDetectionResult(
                platform=PlatformType.CLI,
                confidence=self._calculate_confidence(markers),
                source="markers",
                markers=markers,
            )

        return None

    def _detect_web_markers(self) -> list[str]:
        """Detect web project markers.

        Checks for:
        - package.json with web frameworks (react, vue, angular, svelte)
        - next.config.js/ts
        - nuxt.config.ts/js
        - index.html at root

        Returns:
            List of detected marker strings
        """
        markers: list[str] = []

        # Check package.json for web frameworks
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text()
                data = json.loads(content)
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                for framework in WEB_FRAMEWORKS:
                    if framework in deps:
                        # Normalize framework name for marker
                        marker_name = framework.replace("@", "").split("/")[0]
                        if marker_name == "core":
                            marker_name = "angular"
                        markers.append(f"package.json:{marker_name}")
            except (json.JSONDecodeError, OSError):
                pass

        # Check for Next.js config
        next_config_js = self.project_root / "next.config.js"
        next_config_mjs = self.project_root / "next.config.mjs"
        next_config_ts = self.project_root / "next.config.ts"
        if next_config_js.exists():
            markers.append("next.config.js")
        elif next_config_mjs.exists():
            markers.append("next.config.mjs")
        elif next_config_ts.exists():
            markers.append("next.config.ts")

        # Check for Nuxt config
        nuxt_config_ts = self.project_root / "nuxt.config.ts"
        nuxt_config_js = self.project_root / "nuxt.config.js"
        if nuxt_config_ts.exists():
            markers.append("nuxt.config.ts")
        elif nuxt_config_js.exists():
            markers.append("nuxt.config.js")

        # Check for index.html at root
        index_html = self.project_root / "index.html"
        if index_html.exists():
            markers.append("index.html")

        return markers

    def _detect_backend_markers(self) -> list[str]:
        """Detect backend project markers.

        Checks for:
        - main.py with fastapi/flask/django imports
        - app.py with API patterns
        - requirements.txt with web frameworks
        - Dockerfile with EXPOSE
        - Package.swift with Vapor dependency (Swift backend)

        Returns:
            List of detected marker strings
        """
        markers: list[str] = []

        # Check main.py for backend frameworks
        main_py = self.project_root / "main.py"
        if main_py.exists():
            try:
                content = main_py.read_text().lower()
                for framework in BACKEND_FRAMEWORKS:
                    if framework in content:
                        markers.append(f"main.py:{framework}")
            except OSError:
                pass

        # Check app.py for API patterns
        app_py = self.project_root / "app.py"
        if app_py.exists():
            try:
                content = app_py.read_text()
                for pattern in API_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        markers.append("app.py:api-pattern")
                        break
            except OSError:
                pass

        # Check requirements.txt for backend frameworks
        requirements = self.project_root / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                for framework in BACKEND_FRAMEWORKS:
                    if framework in content:
                        markers.append(f"requirements.txt:{framework}")
            except OSError:
                pass

        # Check Dockerfile for EXPOSE
        dockerfile = self.project_root / "Dockerfile"
        if dockerfile.exists():
            try:
                content = dockerfile.read_text()
                if re.search(r"^\s*EXPOSE\s+\d+", content, re.MULTILINE):
                    markers.append("Dockerfile:EXPOSE")
            except OSError:
                pass

        # Check Package.swift for Swift Vapor backend
        package_swift = self.project_root / "Package.swift"
        if package_swift.exists():
            try:
                content = package_swift.read_text()
                # Check for Vapor dependency (vapor/vapor.git or just "vapor")
                if re.search(r'vapor/vapor\.git|"vapor"', content, re.IGNORECASE):
                    markers.append("Package.swift:vapor")
            except OSError:
                pass

        return markers

    def _detect_mobile_markers(self) -> list[str]:
        """Detect mobile project markers.

        Checks for:
        - iOS native: .xcodeproj or .xcworkspace directories, Info.plist
        - Android native: AndroidManifest.xml with build.gradle
        - Flutter: pubspec.yaml with flutter SDK dependency

        Returns:
            List of detected marker strings
        """
        markers: list[str] = []

        # Check for iOS native project (.xcodeproj or .xcworkspace)
        for item in self.project_root.iterdir():
            if item.is_dir() and item.suffix in (".xcodeproj", ".xcworkspace"):
                markers.append(f"{item.name}:ios")
                break

        # Check for iOS Info.plist in common locations
        info_plist_paths = [
            self.project_root / "Info.plist",
            # Check subdirectories that might contain Info.plist
            *self.project_root.glob("*/Info.plist"),
        ]
        for plist_path in info_plist_paths:
            if plist_path.exists() and plist_path.is_file():
                markers.append("Info.plist:ios")
                break

        # Check for Android native project
        # Look for AndroidManifest.xml in common locations
        android_manifest_paths = [
            self.project_root / "app" / "src" / "main" / "AndroidManifest.xml",
            self.project_root / "AndroidManifest.xml",
        ]
        build_gradle_paths = [
            self.project_root / "build.gradle",
            self.project_root / "build.gradle.kts",
            self.project_root / "app" / "build.gradle",
            self.project_root / "app" / "build.gradle.kts",
        ]

        has_manifest = any(p.exists() for p in android_manifest_paths)
        has_gradle = any(p.exists() for p in build_gradle_paths)

        if has_manifest and has_gradle:
            markers.append("AndroidManifest.xml:android")

        # Check for Flutter project (pubspec.yaml with flutter SDK)
        pubspec = self.project_root / "pubspec.yaml"
        if pubspec.exists():
            try:
                content = pubspec.read_text()
                # Check for flutter SDK dependency
                if "flutter:" in content and "sdk: flutter" in content:
                    markers.append("pubspec.yaml:flutter")
            except OSError:
                pass

        return markers

    def _detect_cli_markers(self) -> list[str]:
        """Detect CLI project markers.

        Checks for:
        - pyproject.toml with [project.scripts] section
        - setup.py with entry_points

        Returns:
            List of detected marker strings
        """
        markers: list[str] = []

        # Check pyproject.toml for scripts
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "[project.scripts]" in content:
                    markers.append("pyproject.toml:scripts")
            except OSError:
                pass

        # Check setup.py for entry_points
        setup_py = self.project_root / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                if "entry_points" in content:
                    markers.append("setup.py:entry_points")
            except OSError:
                pass

        return markers

    def _calculate_confidence(self, markers: list[str]) -> Confidence:
        """Calculate confidence level based on markers found.

        Args:
            markers: List of detected markers

        Returns:
            Confidence level (HIGH for 2+, MEDIUM for 1, LOW for 0)
        """
        if len(markers) >= 2:
            return Confidence.HIGH
        elif len(markers) == 1:
            return Confidence.MEDIUM
        return Confidence.LOW

    def _get_default_result(self) -> PlatformDetectionResult:
        """Get the default platform detection result.

        Defaults to CLI platform with low confidence when no other
        detection method succeeds.

        Returns:
            PlatformDetectionResult with CLI platform and low confidence
        """
        return PlatformDetectionResult(
            platform=PlatformType.CLI,
            confidence=Confidence.LOW,
            source="default",
            markers=[],
        )
