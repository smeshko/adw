"""Tests for the adw validate CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


@pytest.fixture()
def valid_project(tmp_path: Path) -> Path:
    """Create a valid project directory with project.yaml."""
    adw_dir = tmp_path / ".adw"
    adw_dir.mkdir()
    (adw_dir / "project.yaml").write_text(
        "name: test-project\nlanguage: python\n", encoding="utf-8"
    )
    return tmp_path


class TestValidateCommand:
    """Tests for adw validate command."""

    def test_validate_no_project_config(self, tmp_path: Path) -> None:
        """Should report error when no project.yaml exists."""
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            result = runner.invoke(app, ["validate"])
        assert result.exit_code == 1

    def test_validate_valid_project(self, valid_project: Path) -> None:
        """Should pass with valid project config."""
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = valid_project
            result = runner.invoke(app, ["validate"])
        assert result.exit_code == 0

    def test_validate_json_output(self, valid_project: Path) -> None:
        """Should output valid JSON with --json flag."""
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = valid_project
            result = runner.invoke(app, ["validate", "--json"])
        # Exit code 0 for valid config
        assert result.exit_code == 0
        # Output should be parseable JSON
        output = result.stdout.strip()
        data = json.loads(output)
        assert "valid" in data
        assert "error_count" in data
        assert "results" in data
        assert data["valid"] is True

    def test_validate_json_with_errors(self, tmp_path: Path) -> None:
        """JSON output should show errors for invalid config."""
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            result = runner.invoke(app, ["validate", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.stdout.strip())
        assert data["valid"] is False
        assert data["error_count"] >= 1

    def test_validate_strict_with_warnings(self, tmp_path: Path) -> None:
        """--strict should exit 1 when warnings exist."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        (adw_dir / "project.yaml").write_text(
            "name: test\nlanguage: python\ntest_command: nonexistent_xyz_abc\n",
            encoding="utf-8",
        )
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            result = runner.invoke(app, ["validate", "--strict"])
        assert result.exit_code == 1

    def test_validate_without_strict_warnings_ok(self, tmp_path: Path) -> None:
        """Without --strict, warnings should not cause exit 1."""
        adw_dir = tmp_path / ".adw"
        adw_dir.mkdir()
        (adw_dir / "project.yaml").write_text(
            "name: test\nlanguage: python\ntest_command: nonexistent_xyz_abc\n",
            encoding="utf-8",
        )
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            result = runner.invoke(app, ["validate"])
        assert result.exit_code == 0

    def test_validate_invalid_phase_option(self) -> None:
        """--phase with invalid value should fail."""
        result = runner.invoke(app, ["validate", "--phase", "nonexistent"])
        assert result.exit_code != 0

    def test_validate_specific_phase(self, valid_project: Path) -> None:
        """--phase should validate only that phase + project config."""
        with patch("adw.cli.validate_config.Path") as mock_path:
            mock_path.cwd.return_value = valid_project
            result = runner.invoke(app, ["validate", "--phase", "build"])
        assert result.exit_code == 0
