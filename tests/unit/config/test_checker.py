"""Tests for ConfigChecker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from adw.config.checker import (
    CheckReport,
    CheckResult,
    ConfigChecker,
    Severity,
    _extract_executable,
)


class TestSeverity:
    """Tests for Severity enum."""

    def test_error_value(self) -> None:
        assert Severity.ERROR.value == "error"

    def test_warning_value(self) -> None:
        assert Severity.WARNING.value == "warning"


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_basic_creation(self) -> None:
        result = CheckResult(
            severity=Severity.ERROR,
            file_path=".adw/project.yaml",
            message="File not found",
        )
        assert result.severity == Severity.ERROR
        assert result.file_path == ".adw/project.yaml"
        assert result.message == "File not found"
        assert result.field is None
        assert result.suggestion is None

    def test_with_field_and_suggestion(self) -> None:
        result = CheckResult(
            severity=Severity.WARNING,
            file_path=".adw/project.yaml",
            message="'ruff' not found",
            field="lint_command",
            suggestion="Install ruff",
        )
        assert result.field == "lint_command"
        assert result.suggestion == "Install ruff"

    def test_to_dict(self) -> None:
        result = CheckResult(
            severity=Severity.ERROR,
            file_path="test.yaml",
            message="error msg",
            field="name",
            suggestion="fix it",
        )
        d = result.to_dict()
        assert d == {
            "severity": "error",
            "file_path": "test.yaml",
            "message": "error msg",
            "field": "name",
            "suggestion": "fix it",
        }


class TestCheckReport:
    """Tests for CheckReport dataclass."""

    def test_empty_report(self) -> None:
        report = CheckReport()
        assert report.is_valid is True
        assert report.errors == []
        assert report.warnings == []

    def test_add_error(self) -> None:
        report = CheckReport()
        report.add(
            CheckResult(
                severity=Severity.ERROR,
                file_path="test.yaml",
                message="bad",
            )
        )
        assert report.is_valid is False
        assert len(report.errors) == 1
        assert len(report.warnings) == 0

    def test_add_warning(self) -> None:
        report = CheckReport()
        report.add(
            CheckResult(
                severity=Severity.WARNING,
                file_path="test.yaml",
                message="warn",
            )
        )
        assert report.is_valid is True
        assert len(report.warnings) == 1

    def test_merge(self) -> None:
        r1 = CheckReport()
        r1.add(CheckResult(severity=Severity.ERROR, file_path="a", message="e1"))
        r2 = CheckReport()
        r2.add(CheckResult(severity=Severity.WARNING, file_path="b", message="w1"))
        r1.merge(r2)
        assert len(r1.results) == 2
        assert len(r1.errors) == 1
        assert len(r1.warnings) == 1

    def test_to_dict(self) -> None:
        report = CheckReport()
        report.add(CheckResult(severity=Severity.ERROR, file_path="a", message="e"))
        report.add(CheckResult(severity=Severity.WARNING, file_path="b", message="w"))
        d = report.to_dict()
        assert d["valid"] is False
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert len(d["results"]) == 2


class TestExtractExecutable:
    """Tests for _extract_executable helper."""

    def test_simple_command(self) -> None:
        assert _extract_executable("pytest") == "pytest"

    def test_command_with_args(self) -> None:
        assert _extract_executable("pytest tests/ -v") == "pytest"

    def test_empty_string(self) -> None:
        assert _extract_executable("") is None

    def test_whitespace(self) -> None:
        assert _extract_executable("  npm  run test") == "npm"


class TestConfigCheckerProjectConfig:
    """Tests for ConfigChecker.check_project_config()."""

    def test_missing_project_config(self, tmp_path: Path) -> None:
        """Missing .adw/project.yaml should produce an error."""
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert not report.is_valid
        assert len(report.errors) == 1
        assert "not found" in report.errors[0].message

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Invalid YAML should produce a syntax error."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text("name: [unclosed bracket", encoding="utf-8")
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert not report.is_valid
        assert "YAML syntax" in report.errors[0].message

    def test_empty_config_file(self, tmp_path: Path) -> None:
        """Empty YAML file should produce an error."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text("", encoding="utf-8")
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert not report.is_valid
        assert "empty" in report.errors[0].message.lower()

    def test_schema_violation(self, tmp_path: Path) -> None:
        """Missing required fields should produce schema errors."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        # Missing required 'name' and 'language'
        config_file.write_text("platform: cli\n", encoding="utf-8")
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert not report.is_valid
        assert len(report.errors) >= 1

    def test_valid_config(self, tmp_path: Path) -> None:
        """Valid config should pass all checks."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text(
            "name: test-project\nlanguage: python\n", encoding="utf-8"
        )
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert report.is_valid

    def test_semantic_warning_test_command_not_found(self, tmp_path: Path) -> None:
        """test_command with nonexistent executable should warn."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text(
            "name: test\nlanguage: python\ntest_command: nonexistent_tool_xyz123\n",
            encoding="utf-8",
        )
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        # Should be valid (warnings don't make it invalid)
        assert report.is_valid
        assert len(report.warnings) == 1
        assert "nonexistent_tool_xyz123" in report.warnings[0].message
        assert report.warnings[0].field == "test_command"

    def test_semantic_warning_build_command_not_found(self, tmp_path: Path) -> None:
        """build_command with nonexistent executable should warn."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text(
            "name: test\nlanguage: python\nbuild_command: nonexistent_build_xyz\n",
            encoding="utf-8",
        )
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert report.is_valid
        assert len(report.warnings) == 1
        assert report.warnings[0].field == "build_command"

    def test_semantic_warning_llm_path_not_found(self, tmp_path: Path) -> None:
        """llm.path with nonexistent executable should warn (if not 'claude')."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text(
            "name: test\nlanguage: python\nllm:\n  path: nonexistent_llm_xyz\n",
            encoding="utf-8",
        )
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_project_config()
        assert report.is_valid
        assert len(report.warnings) == 1
        assert report.warnings[0].field == "llm.path"

    def test_no_warning_for_claude_llm_path(self, tmp_path: Path) -> None:
        """llm.path='claude' should not warn even if not on PATH."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text(
            "name: test\nlanguage: python\nllm:\n  path: claude\n",
            encoding="utf-8",
        )
        checker = ConfigChecker(project_root=tmp_path)
        with patch("adw.config.checker.shutil.which", return_value=None):
            report = checker.check_project_config()
        # No warning for 'claude' — it's the default and skipped
        llm_warnings = [w for w in report.warnings if w.field == "llm.path"]
        assert len(llm_warnings) == 0

    def test_semantic_no_warning_when_executable_found(self, tmp_path: Path) -> None:
        """No warning when executable is found on PATH."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        config_file = adw_dir / "project.yaml"
        config_file.write_text(
            "name: test\nlanguage: python\ntest_command: pytest\n",
            encoding="utf-8",
        )
        checker = ConfigChecker(project_root=tmp_path)
        with patch("adw.config.checker.shutil.which", return_value="/usr/bin/pytest"):
            report = checker.check_project_config()
        assert len(report.warnings) == 0


class TestConfigCheckerPhaseConfig:
    """Tests for ConfigChecker.check_phase_config()."""

    def test_phase_without_config_yaml(self, tmp_path: Path) -> None:
        """Phase with no config.yaml should pass (it's optional)."""
        # Set up a minimal phase command directory
        phase_dir = tmp_path / ".adw" / "commands" / "plan"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Plan prompt", encoding="utf-8")

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("plan")
        assert report.is_valid
        assert len(report.results) == 0

    def test_project_config_override_without_prompt(self, tmp_path: Path) -> None:
        """Project config.yaml override without prompt.md should still be checked.

        This is the common case: user creates .adw/commands/plan/config.yaml
        to override settings, but prompt.md resolves to bundled. The checker
        must still validate the project-tier config.yaml.
        """
        # Project-tier: config.yaml only, no prompt.md
        phase_dir = tmp_path / ".adw" / "commands" / "plan"
        phase_dir.mkdir(parents=True)
        (phase_dir / "config.yaml").write_text(
            "enabled: true\ntimeout_seconds: 300\n", encoding="utf-8"
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("plan")
        # timeout_seconds is not a valid field — should be rejected
        assert not report.is_valid
        assert any(
            "timeout_seconds" in r.message or "timeout_seconds" in (r.field or "")
            for r in report.errors
        )

    def test_phase_with_valid_config(self, tmp_path: Path) -> None:
        """Phase with valid config.yaml should pass."""
        phase_dir = tmp_path / ".adw" / "commands" / "build"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Build prompt", encoding="utf-8")
        (phase_dir / "config.yaml").write_text("enabled: true\n", encoding="utf-8")

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("build")
        assert report.is_valid

    def test_phase_with_invalid_yaml(self, tmp_path: Path) -> None:
        """Phase config with invalid YAML should error."""
        phase_dir = tmp_path / ".adw" / "commands" / "build"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Build prompt", encoding="utf-8")
        (phase_dir / "config.yaml").write_text("enabled: [bad", encoding="utf-8")

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("build")
        assert not report.is_valid
        assert "YAML syntax" in report.errors[0].message

    def test_phase_with_schema_violation(self, tmp_path: Path) -> None:
        """Phase config with unknown field should error (extra='forbid')."""
        phase_dir = tmp_path / ".adw" / "commands" / "build"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Build prompt", encoding="utf-8")
        (phase_dir / "config.yaml").write_text(
            "enabled: true\nunknown_field: bad\n", encoding="utf-8"
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("build")
        assert not report.is_valid

    def test_phase_input_files_missing(self, tmp_path: Path) -> None:
        """Input file that doesn't exist should produce an error."""
        phase_dir = tmp_path / ".adw" / "commands" / "plan"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Plan prompt", encoding="utf-8")
        (phase_dir / "config.yaml").write_text(
            "input_files:\n  prd: docs/prd.md\n", encoding="utf-8"
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("plan")
        assert not report.is_valid
        assert "does not exist" in report.errors[0].message
        assert report.errors[0].field == "input_files.prd"

    def test_phase_input_files_exist(self, tmp_path: Path) -> None:
        """Input file that exists should not produce errors."""
        phase_dir = tmp_path / ".adw" / "commands" / "plan"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Plan prompt", encoding="utf-8")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "prd.md").write_text("PRD content", encoding="utf-8")
        (phase_dir / "config.yaml").write_text(
            "input_files:\n  prd: docs/prd.md\n", encoding="utf-8"
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("plan")
        assert report.is_valid

    def test_validate_phase_lint_command_warning(self, tmp_path: Path) -> None:
        """Validate phase with nonexistent lint_command should warn."""
        phase_dir = tmp_path / ".adw" / "commands" / "validate"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Validate prompt", encoding="utf-8")
        (phase_dir / "config.yaml").write_text(
            "lint_command: nonexistent_linter_xyz\n", encoding="utf-8"
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("validate")
        assert report.is_valid  # Warning, not error
        assert len(report.warnings) == 1
        assert report.warnings[0].field == "lint_command"

    def test_ship_phase_command_warnings(self, tmp_path: Path) -> None:
        """Ship phase with nonexistent commands should warn."""
        phase_dir = tmp_path / ".adw" / "commands" / "ship"
        phase_dir.mkdir(parents=True)
        (phase_dir / "prompt.md").write_text("Ship prompt", encoding="utf-8")
        (phase_dir / "config.yaml").write_text(
            "commands:\n  version_bump: nonexistent_bump_xyz\n  publish: nonexistent_pub_xyz\n",
            encoding="utf-8",
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_phase_config("ship")
        assert report.is_valid  # Warnings, not errors
        assert len(report.warnings) == 2


class TestConfigCheckerCheckAll:
    """Tests for ConfigChecker.check_all()."""

    def test_check_all_missing_project(self, tmp_path: Path) -> None:
        """check_all with no project config should report error."""
        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_all()
        assert not report.is_valid
        assert len(report.errors) >= 1

    def test_check_all_valid_project_no_phases(self, tmp_path: Path) -> None:
        """check_all with valid project but no phase configs should pass."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        (adw_dir / "project.yaml").write_text(
            "name: test\nlanguage: python\n", encoding="utf-8"
        )

        checker = ConfigChecker(project_root=tmp_path)
        report = checker.check_all()
        assert report.is_valid
