"""Platform detection for evidence gathering.

This module provides the PlatformDetector class that determines the
project platform type (CLI, WEB, BACKEND) from configuration or file markers.
"""

import json
import re
from pathlib import Path

import yaml

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

    def detect(self) -> PlatformDetectionResult:
        """Detect the platform type for the project.

        Attempts detection in priority order:
        1. Explicit config (returns immediately if found)
        2. File markers (analyzed for confidence scoring)
        3. Default to CLI with low confidence

        Returns:
            PlatformDetectionResult with detected platform and metadata
        """
        # Priority 1: Check explicit configuration
        config_result = self._detect_from_config()
        if config_result is not None:
            return config_result

        # Priority 2: Check file markers
        marker_result = self._detect_from_markers()
        if marker_result is not None:
            return marker_result

        # Priority 3: Default to CLI
        return self._get_default_result()

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

        Checks for:
        - Web markers: package.json with frameworks, next/nuxt config, index.html
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
