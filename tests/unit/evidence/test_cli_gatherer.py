"""Tests for CLI evidence gatherer integration.

Tests the CLIEvidenceGatherer class that orchestrates CLI evidence gathering.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from adw.evidence.cli_gatherer import CLIEvidenceGatherer
from adw.models.evidence import (
    CLIEvidenceSummary,
    PlatformType,
)


class TestCLIEvidenceGatherer:
    """Tests for CLIEvidenceGatherer class."""

    def test_init(self, tmp_path: Path) -> None:
        """CLIEvidenceGatherer should initialize with paths."""
        evidence_dir = tmp_path / "evidence" / "cli"
        gatherer = CLIEvidenceGatherer(
            project_root=tmp_path,
            evidence_dir=evidence_dir,
        )
        assert gatherer.project_root == tmp_path
        assert gatherer.evidence_dir == evidence_dir


class TestGather:
    """Tests for gather method."""

    def test_gather_no_commands_configured(self, tmp_path: Path) -> None:
        """gather should return empty summary if no commands configured."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        evidence_dir = tmp_path / "evidence" / "cli"

        # Create config without evidence section
        config_dir = project_root / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "name": "test",
                    "language": "python",
                }
            )
        )

        gatherer = CLIEvidenceGatherer(
            project_root=project_root,
            evidence_dir=evidence_dir,
        )
        summary = gatherer.gather()

        assert isinstance(summary, CLIEvidenceSummary)
        assert summary.total_commands == 0
        assert summary.passed == 0
        assert summary.failed == 0

    @patch("subprocess.run")
    def test_gather_executes_commands(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """gather should execute configured commands."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        evidence_dir = tmp_path / "evidence" / "cli"

        # Create config with commands
        config_dir = project_root / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "name": "test",
                    "language": "python",
                    "evidence": {
                        "commands": [
                            {"name": "version", "cmd": "python --version"},
                            {"name": "help", "cmd": "python --help"},
                        ]
                    },
                }
            )
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        gatherer = CLIEvidenceGatherer(
            project_root=project_root,
            evidence_dir=evidence_dir,
        )
        summary = gatherer.gather()

        assert summary.total_commands == 2
        assert summary.passed == 2
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_gather_writes_evidence_files(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """gather should write evidence files for each command."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        evidence_dir = tmp_path / "evidence" / "cli"

        config_dir = project_root / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "name": "test",
                    "language": "python",
                    "evidence": {
                        "commands": [
                            {"name": "version", "cmd": "python --version"},
                        ]
                    },
                }
            )
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Python 3.11.0\n",
            stderr="",
        )

        gatherer = CLIEvidenceGatherer(
            project_root=project_root,
            evidence_dir=evidence_dir,
        )
        gatherer.gather()

        # Check evidence file was created
        evidence_file = evidence_dir / "version.txt"
        assert evidence_file.exists()
        content = evidence_file.read_text()
        assert "Python 3.11.0" in content

    @patch("subprocess.run")
    def test_gather_writes_summary_file(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """gather should write summary.json file."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        evidence_dir = tmp_path / "evidence" / "cli"

        config_dir = project_root / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "name": "test",
                    "language": "python",
                    "evidence": {
                        "commands": [
                            {"name": "test", "cmd": "echo ok"},
                        ]
                    },
                }
            )
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

        gatherer = CLIEvidenceGatherer(
            project_root=project_root,
            evidence_dir=evidence_dir,
        )
        gatherer.gather()

        summary_file = evidence_dir / "summary.json"
        assert summary_file.exists()

    @patch("subprocess.run")
    def test_gather_handles_failed_commands(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """gather should handle failed commands without stopping."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        evidence_dir = tmp_path / "evidence" / "cli"

        config_dir = project_root / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "name": "test",
                    "language": "python",
                    "evidence": {
                        "commands": [
                            {"name": "pass", "cmd": "echo ok"},
                            {"name": "fail", "cmd": "false"},
                            {"name": "also-pass", "cmd": "echo done"},
                        ]
                    },
                }
            )
        )

        # First and third succeed, second fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="ok", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="error"),
            MagicMock(returncode=0, stdout="done", stderr=""),
        ]

        gatherer = CLIEvidenceGatherer(
            project_root=project_root,
            evidence_dir=evidence_dir,
        )
        summary = gatherer.gather()

        # Should continue despite failure
        assert summary.total_commands == 3
        assert summary.passed == 2
        assert summary.failed == 1


class TestShouldGather:
    """Tests for should_gather method."""

    def test_should_gather_for_cli_platform(self, tmp_path: Path) -> None:
        """should_gather returns True for CLI platform."""
        gatherer = CLIEvidenceGatherer(
            project_root=tmp_path,
            evidence_dir=tmp_path / "evidence",
        )
        assert gatherer.should_gather(PlatformType.CLI) is True

    def test_should_gather_for_unknown_platform(self, tmp_path: Path) -> None:
        """should_gather returns True for UNKNOWN platform (defaults to CLI)."""
        gatherer = CLIEvidenceGatherer(
            project_root=tmp_path,
            evidence_dir=tmp_path / "evidence",
        )
        assert gatherer.should_gather(PlatformType.UNKNOWN) is True

    def test_should_not_gather_for_web_platform(self, tmp_path: Path) -> None:
        """should_gather returns False for WEB platform."""
        gatherer = CLIEvidenceGatherer(
            project_root=tmp_path,
            evidence_dir=tmp_path / "evidence",
        )
        assert gatherer.should_gather(PlatformType.WEB) is False

    def test_should_not_gather_for_mobile_platform(self, tmp_path: Path) -> None:
        """should_gather returns False for MOBILE platform."""
        gatherer = CLIEvidenceGatherer(
            project_root=tmp_path,
            evidence_dir=tmp_path / "evidence",
        )
        assert gatherer.should_gather(PlatformType.MOBILE) is False

    def test_should_not_gather_for_backend_platform(self, tmp_path: Path) -> None:
        """should_gather returns False for BACKEND platform."""
        gatherer = CLIEvidenceGatherer(
            project_root=tmp_path,
            evidence_dir=tmp_path / "evidence",
        )
        assert gatherer.should_gather(PlatformType.BACKEND) is False
