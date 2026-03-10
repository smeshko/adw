"""Configuration checker for validating ADW config files.

This module provides the ConfigChecker class that validates project.yaml
and phase config.yaml files through four validation layers:
existence, syntax, schema, and semantics.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from adw.commands.loader import get_config_class
from adw.commands.resolver import CommandResolver
from adw.core.constants import PHASE_SEQUENCE
from adw.models.command import ShipCommandConfig, ValidateCommandConfig
from adw.models.config import ProjectConfig

__all__ = ["CheckReport", "CheckResult", "ConfigChecker", "Severity"]


class Severity(Enum):
    """Severity level for a check result."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class CheckResult:
    """A single validation finding.

    Attributes:
        severity: Whether this is an error or warning.
        file_path: Relative path to the config file checked.
        message: Human-readable description of the issue.
        field: Dotted field path, if applicable.
        suggestion: Suggested fix, if available.
    """

    severity: Severity
    file_path: str
    message: str
    field: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "severity": self.severity.value,
            "file_path": self.file_path,
            "message": self.message,
            "field": self.field,
            "suggestion": self.suggestion,
        }


@dataclass
class CheckReport:
    """Aggregated validation report.

    Attributes:
        results: List of individual check results.
    """

    results: list[CheckResult] = field(default_factory=list)

    @property
    def errors(self) -> list[CheckResult]:
        """All error-severity results."""
        return [r for r in self.results if r.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[CheckResult]:
        """All warning-severity results."""
        return [r for r in self.results if r.severity == Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        """True if no errors were found (warnings are OK)."""
        return len(self.errors) == 0

    def add(self, result: CheckResult) -> None:
        """Add a single check result."""
        self.results.append(result)

    def merge(self, other: CheckReport) -> None:
        """Merge another report's results into this one."""
        self.results.extend(other.results)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "results": [r.to_dict() for r in self.results],
        }


class ConfigChecker:
    """Validates ADW configuration files.

    Checks project.yaml and phase config.yaml files through four layers:
    1. Existence — does the file exist?
    2. Syntax — is it valid YAML?
    3. Schema — does it conform to the Pydantic model?
    4. Semantic — do cross-references resolve?

    Layers short-circuit: if existence fails, syntax/schema/semantic
    checks are skipped for that file.

    Example:
        >>> checker = ConfigChecker(project_root=Path("."))
        >>> report = checker.check_all()
        >>> print(report.is_valid)
        True
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the ConfigChecker.

        Args:
            project_root: Project root directory. Uses cwd if not specified.
        """
        self.project_root = project_root or Path.cwd()
        self._resolver = CommandResolver(project_root=self.project_root)

    def check_all(self) -> CheckReport:
        """Run all checks on project config and all phase configs.

        Returns:
            Aggregated CheckReport with all findings.
        """
        report = self.check_project_config()
        for phase in PHASE_SEQUENCE:
            report.merge(self.check_phase_config(phase))
        return report

    def check_project_config(self) -> CheckReport:
        """Check project.yaml through all validation layers.

        Returns:
            CheckReport for the project config file.
        """
        report = CheckReport()
        config_path = self.project_root / ".adw" / "project.yaml"
        rel_path = ".adw/project.yaml"

        # Layer 1: Existence
        if not config_path.exists():
            report.add(
                CheckResult(
                    severity=Severity.ERROR,
                    file_path=rel_path,
                    message="Project config file not found",
                    suggestion="Run 'adw init' to create project configuration",
                )
            )
            return report

        # Layer 2: Syntax
        try:
            content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            report.add(
                CheckResult(
                    severity=Severity.ERROR,
                    file_path=rel_path,
                    message=f"Invalid YAML syntax: {e}",
                    suggestion="Fix YAML syntax errors in project.yaml",
                )
            )
            return report

        if data is None:
            report.add(
                CheckResult(
                    severity=Severity.ERROR,
                    file_path=rel_path,
                    message="Configuration file is empty",
                    suggestion="Add required fields: name, language",
                )
            )
            return report

        # Layer 3: Schema
        try:
            config = ProjectConfig.model_validate(data)
        except PydanticValidationError as e:
            for err in e.errors():
                field_path = ".".join(str(loc) for loc in err["loc"])
                report.add(
                    CheckResult(
                        severity=Severity.ERROR,
                        file_path=rel_path,
                        message=err["msg"],
                        field=field_path,
                    )
                )
            return report

        # Layer 4: Semantics
        self._check_project_semantics(config, rel_path, report)

        return report

    def check_phase_config(self, phase: str) -> CheckReport:
        """Check a phase's config.yaml through all validation layers.

        Checks config.yaml from the resolved command directory AND from the
        project-tier override directory (.adw/commands/{phase}/config.yaml),
        since project overrides may exist without a prompt.md (config-only override).

        Args:
            phase: Phase name (e.g., "plan", "build").

        Returns:
            CheckReport for the phase config file.
        """
        report = CheckReport()

        # Resolve the command to find its config.yaml
        try:
            resolved = self._resolver.resolve(phase)
        except Exception:
            # Phase command not found — not necessarily an error
            # (could be a custom setup without all phases)
            return report

        # Collect config paths to check:
        # 1. The resolved command's config.yaml (could be bundled/user/project)
        # 2. The project-tier override config.yaml (if different from resolved)
        config_paths: list[Path] = []

        resolved_config = resolved.path / "config.yaml"
        if resolved_config.exists():
            config_paths.append(resolved_config)

        # Also check project-tier config override even when command resolves
        # to bundled/user tier. Projects can have .adw/commands/{phase}/config.yaml
        # without a prompt.md (config-only override).
        project_config = self.project_root / ".adw" / "commands" / phase / "config.yaml"
        if project_config.exists() and project_config != resolved_config:
            config_paths.append(project_config)

        # Layer 1: Existence — config.yaml is optional for phases
        if not config_paths:
            return report

        for config_path in config_paths:
            report.merge(self._check_single_phase_config(config_path, phase))

        return report

    def _check_single_phase_config(
        self, config_path: Path, phase: str
    ) -> CheckReport:
        """Check a single phase config.yaml file.

        Args:
            config_path: Path to the config.yaml file.
            phase: Phase name for selecting the config class.

        Returns:
            CheckReport for this config file.
        """
        report = CheckReport()
        rel_path = str(config_path.relative_to(self.project_root)) if _is_relative_to(
            config_path, self.project_root
        ) else str(config_path)

        # Layer 2: Syntax
        try:
            content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            report.add(
                CheckResult(
                    severity=Severity.ERROR,
                    file_path=rel_path,
                    message=f"Invalid YAML syntax: {e}",
                    suggestion=f"Fix YAML syntax in {phase} config.yaml",
                )
            )
            return report

        if data is None:
            # Empty config.yaml is valid (uses defaults)
            data = {}

        # Layer 3: Schema
        config_class = get_config_class(phase)
        try:
            config = config_class.model_validate(data)
        except PydanticValidationError as e:
            for err in e.errors():
                field_path = ".".join(str(loc) for loc in err["loc"])
                report.add(
                    CheckResult(
                        severity=Severity.ERROR,
                        file_path=rel_path,
                        message=err["msg"],
                        field=field_path,
                    )
                )
            return report

        # Layer 4: Semantics
        self._check_phase_semantics(config, rel_path, report)

        return report

    def _check_project_semantics(
        self, config: ProjectConfig, rel_path: str, report: CheckReport
    ) -> None:
        """Run semantic checks on project config.

        Checks:
        - test_command executable exists on PATH
        - build_command executable exists on PATH
        - llm.path executable exists on PATH (if not "claude")
        """
        if config.test_command:
            exe = _extract_executable(config.test_command)
            if exe and not shutil.which(exe):
                report.add(
                    CheckResult(
                        severity=Severity.WARNING,
                        file_path=rel_path,
                        message=f"'{exe}' not found on PATH",
                        field="test_command",
                        suggestion=f"Install {exe} or update test_command",
                    )
                )

        if config.build_command:
            exe = _extract_executable(config.build_command)
            if exe and not shutil.which(exe):
                report.add(
                    CheckResult(
                        severity=Severity.WARNING,
                        file_path=rel_path,
                        message=f"'{exe}' not found on PATH",
                        field="build_command",
                        suggestion=f"Install {exe} or update build_command",
                    )
                )

        if config.llm.path != "claude":
            exe = _extract_executable(config.llm.path)
            if exe and not shutil.which(exe):
                report.add(
                    CheckResult(
                        severity=Severity.WARNING,
                        file_path=rel_path,
                        message=f"LLM executable '{exe}' not found on PATH",
                        field="llm.path",
                        suggestion=f"Install {exe} or set llm.path to 'claude'",
                    )
                )

    def _check_phase_semantics(
        self, config: Any, rel_path: str, report: CheckReport
    ) -> None:
        """Run semantic checks on a phase config.

        Checks:
        - input_files values exist relative to project root
        - lint_command executable (validate phase)
        - ship commands executables (ship phase)
        """
        # Check input_files exist
        if hasattr(config, "input_files") and config.input_files:
            for name, file_path in config.input_files.items():
                full_path = self.project_root / file_path
                if not full_path.exists():
                    report.add(
                        CheckResult(
                            severity=Severity.ERROR,
                            file_path=rel_path,
                            message=f"Input file '{file_path}' does not exist",
                            field=f"input_files.{name}",
                            suggestion=f"Create the file or update the path",
                        )
                    )

        # Validate phase: check lint_command
        if isinstance(config, ValidateCommandConfig) and config.lint_command:
            exe = _extract_executable(config.lint_command)
            if exe and not shutil.which(exe):
                report.add(
                    CheckResult(
                        severity=Severity.WARNING,
                        file_path=rel_path,
                        message=f"'{exe}' not found on PATH",
                        field="lint_command",
                        suggestion=f"Install {exe} or update lint_command",
                    )
                )

        # Ship phase: check commands
        if isinstance(config, ShipCommandConfig):
            if config.commands.version_bump:
                exe = _extract_executable(config.commands.version_bump)
                if exe and not shutil.which(exe):
                    report.add(
                        CheckResult(
                            severity=Severity.WARNING,
                            file_path=rel_path,
                            message=f"'{exe}' not found on PATH",
                            field="commands.version_bump",
                            suggestion=f"Install {exe} or update version_bump command",
                        )
                    )
            if config.commands.publish:
                exe = _extract_executable(config.commands.publish)
                if exe and not shutil.which(exe):
                    report.add(
                        CheckResult(
                            severity=Severity.WARNING,
                            file_path=rel_path,
                            message=f"'{exe}' not found on PATH",
                            field="commands.publish",
                            suggestion=f"Install {exe} or update publish command",
                        )
                    )


def _extract_executable(command: str) -> str | None:
    """Extract the executable name from a shell command string.

    Handles common patterns like 'pytest tests/', 'npm run test',
    and 'python -m pytest'.

    Args:
        command: Shell command string.

    Returns:
        The executable name, or None if empty.
    """
    parts = command.strip().split()
    return parts[0] if parts else None


def _is_relative_to(path: Path, base: Path) -> bool:
    """Check if path is relative to base (Python 3.9+ compatible)."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False
