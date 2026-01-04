"""Tests for CLI evidence config loading.

Tests loading command configurations from project.yaml evidence section.
"""

from pathlib import Path

import pytest
import yaml

from adw.evidence.config_loader import load_evidence_commands
from adw.models.evidence import CommandConfig


class TestLoadEvidenceCommands:
    """Tests for load_evidence_commands function."""

    def test_load_commands_from_config(self, tmp_path: Path) -> None:
        """load_evidence_commands should parse commands from config."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump({
            "name": "test-project",
            "language": "python",
            "evidence": {
                "commands": [
                    {"name": "version", "cmd": "python --version", "timeout": 30},
                    {"name": "help", "cmd": "python --help", "timeout": 60},
                ]
            }
        }))

        commands = load_evidence_commands(tmp_path)

        assert len(commands) == 2
        assert isinstance(commands[0], CommandConfig)
        assert commands[0].name == "version"
        assert commands[0].cmd == "python --version"
        assert commands[0].timeout == 30
        assert commands[1].name == "help"
        assert commands[1].timeout == 60

    def test_load_commands_default_timeout(self, tmp_path: Path) -> None:
        """load_evidence_commands should use default timeout."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump({
            "name": "test-project",
            "language": "python",
            "evidence": {
                "commands": [
                    {"name": "quick", "cmd": "echo hi"}
                ]
            }
        }))

        commands = load_evidence_commands(tmp_path)

        assert len(commands) == 1
        assert commands[0].timeout == 30  # default

    def test_load_commands_missing_evidence_section(self, tmp_path: Path) -> None:
        """load_evidence_commands should return empty list if no evidence section."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump({
            "name": "test-project",
            "language": "python",
        }))

        commands = load_evidence_commands(tmp_path)

        assert commands == []

    def test_load_commands_missing_commands_key(self, tmp_path: Path) -> None:
        """load_evidence_commands should return empty if commands key missing."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump({
            "name": "test-project",
            "language": "python",
            "evidence": {
                "other_key": "value"
            }
        }))

        commands = load_evidence_commands(tmp_path)

        assert commands == []

    def test_load_commands_empty_commands_list(self, tmp_path: Path) -> None:
        """load_evidence_commands should return empty if commands list empty."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump({
            "name": "test-project",
            "language": "python",
            "evidence": {
                "commands": []
            }
        }))

        commands = load_evidence_commands(tmp_path)

        assert commands == []

    def test_load_commands_no_config_file(self, tmp_path: Path) -> None:
        """load_evidence_commands should return empty if no config file."""
        commands = load_evidence_commands(tmp_path)

        assert commands == []

    def test_load_commands_invalid_command_format(self, tmp_path: Path) -> None:
        """load_evidence_commands should skip invalid commands."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump({
            "name": "test-project",
            "language": "python",
            "evidence": {
                "commands": [
                    {"name": "valid", "cmd": "echo hi"},
                    {"invalid": "missing name and cmd"},  # invalid
                    {"name": "also-valid", "cmd": "echo ok"},
                ]
            }
        }))

        commands = load_evidence_commands(tmp_path)

        # Should only return valid commands
        assert len(commands) == 2
        assert commands[0].name == "valid"
        assert commands[1].name == "also-valid"

    def test_load_commands_yaml_format(self, tmp_path: Path) -> None:
        """load_evidence_commands should parse standard YAML format."""
        config_file = tmp_path / ".adw" / "project.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("""
name: test-project
language: python
evidence:
  commands:
    - name: "version"
      cmd: "adw --version"
      timeout: 30
    - name: "help"
      cmd: "adw --help"
      timeout: 30
""")

        commands = load_evidence_commands(tmp_path)

        assert len(commands) == 2
        assert commands[0].name == "version"
        assert commands[0].cmd == "adw --version"
