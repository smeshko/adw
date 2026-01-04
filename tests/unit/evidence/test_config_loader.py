"""Tests for API and CLI evidence configuration loading.

This module tests loading endpoint and command configurations from project config files.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from adw.evidence.config_loader import (
    EvidenceConfig,
    load_evidence_commands,
    load_evidence_config,
)
from adw.models.evidence import AuthConfig, AuthType, CommandConfig, EndpointConfig


# =============================================================================
# API Evidence Config Tests
# =============================================================================


class TestLoadEvidenceConfig:
    """Tests for load_evidence_config function."""

    def test_load_config_from_project_yaml(self) -> None:
        """Test loading evidence config from .adw/project.yaml."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".adw"
            config_dir.mkdir()

            config_file = config_dir / "project.yaml"
            config_file.write_text("""
evidence:
  base_url: "http://localhost:8000"
  endpoints:
    - name: "health"
      path: "/health"
    - name: "users"
      method: "GET"
      path: "/api/users"
      expected_status: 200
""")

            config = load_evidence_config(project_root)

            assert config is not None
            assert config.base_url == "http://localhost:8000"
            assert len(config.endpoints) == 2
            assert config.endpoints[0].name == "health"
            assert config.endpoints[0].path == "/health"
            assert config.endpoints[1].name == "users"
            assert config.endpoints[1].expected_status == 200

    def test_load_config_with_auth(self) -> None:
        """Test loading config with authentication section."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".adw"
            config_dir.mkdir()

            config_file = config_dir / "project.yaml"
            config_file.write_text("""
evidence:
  base_url: "http://localhost:8000"
  auth:
    type: "bearer"
    token_env: "API_TOKEN"
  endpoints:
    - name: "protected"
      path: "/api/protected"
""")

            config = load_evidence_config(project_root)

            assert config.auth is not None
            assert config.auth.type == AuthType.BEARER
            assert config.auth.token_env == "API_TOKEN"

    def test_load_config_with_api_key_auth(self) -> None:
        """Test loading config with API key authentication."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".adw"
            config_dir.mkdir()

            config_file = config_dir / "project.yaml"
            config_file.write_text("""
evidence:
  base_url: "http://localhost:3000"
  auth:
    type: "api_key"
    header: "X-API-Key"
    key_env: "MY_API_KEY"
  endpoints:
    - name: "api"
      path: "/api"
""")

            config = load_evidence_config(project_root)

            assert config.auth is not None
            assert config.auth.type == AuthType.API_KEY
            assert config.auth.header == "X-API-Key"
            assert config.auth.key_env == "MY_API_KEY"

    def test_load_config_no_evidence_section_returns_none(self) -> None:
        """Test that missing evidence section returns None."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".adw"
            config_dir.mkdir()

            config_file = config_dir / "project.yaml"
            config_file.write_text("""
name: "my-project"
platform: "backend"
""")

            config = load_evidence_config(project_root)
            assert config is None

    def test_load_config_missing_file_returns_none(self) -> None:
        """Test that missing config file returns None."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = load_evidence_config(project_root)
            assert config is None

    def test_load_config_with_endpoint_body(self) -> None:
        """Test loading endpoint with request body."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".adw"
            config_dir.mkdir()

            config_file = config_dir / "project.yaml"
            config_file.write_text("""
evidence:
  base_url: "http://localhost:8000"
  endpoints:
    - name: "create_user"
      method: "POST"
      path: "/api/users"
      body:
        name: "test"
        email: "test@example.com"
      expected_status: 201
""")

            config = load_evidence_config(project_root)

            assert config.endpoints[0].method == "POST"
            assert config.endpoints[0].body == {
                "name": "test",
                "email": "test@example.com",
            }
            assert config.endpoints[0].expected_status == 201

    def test_load_config_with_custom_headers(self) -> None:
        """Test loading endpoint with custom headers."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config_dir = project_root / ".adw"
            config_dir.mkdir()

            config_file = config_dir / "project.yaml"
            config_file.write_text("""
evidence:
  base_url: "http://localhost:8000"
  endpoints:
    - name: "api"
      path: "/api"
      headers:
        Accept: "application/json"
        X-Custom: "value"
""")

            config = load_evidence_config(project_root)

            assert config.endpoints[0].headers == {
                "Accept": "application/json",
                "X-Custom": "value",
            }


class TestEvidenceConfig:
    """Tests for EvidenceConfig model."""

    def test_evidence_config_creation(self) -> None:
        """Test creating EvidenceConfig instance."""
        config = EvidenceConfig(
            base_url="http://localhost:8000",
            endpoints=[
                EndpointConfig(name="health", path="/health"),
            ],
        )
        assert config.base_url == "http://localhost:8000"
        assert len(config.endpoints) == 1

    def test_evidence_config_with_auth(self) -> None:
        """Test EvidenceConfig with auth."""
        config = EvidenceConfig(
            base_url="http://localhost:8000",
            auth=AuthConfig(type=AuthType.BEARER, token_env="TOKEN"),
            endpoints=[],
        )
        assert config.auth is not None
        assert config.auth.type == AuthType.BEARER


# =============================================================================
# CLI Evidence Commands Tests
# =============================================================================


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
