"""Tests for wizard summary and file generation step.

Tests the summary panel generation, configuration confirmation,
file generation, and atomic write functionality.
"""

from __future__ import annotations

import signal
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from rich.console import Console
from rich.panel import Panel

from adw import fs
from adw.cli.wizard.summary import (
    ConfigWriteError,
    atomic_write_config,
    generate_env_template,
    generate_gitignore,
    generate_phase_configs,
    generate_project_yaml,
    generate_summary_panel,
    run_summary_step,
)


class TestSummaryPanelGeneration:
    """Tests for summary panel generation."""

    def test_generate_summary_panel_returns_panel(self) -> None:
        """Test that generate_summary_panel returns a Rich Panel."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {},
            "phases": {},
        }

        panel = generate_summary_panel(cfg)

        assert isinstance(panel, Panel)
        assert panel.title == "Configuration Summary"

    def test_summary_panel_shows_all_sections(self) -> None:
        """Test that summary panel includes all configuration sections."""
        cfg = {
            "basics": {
                "language": "python",
                "platform": "api",
                "test_command": "pytest",
                "build_command": "python -m build",
            },
            "git": {
                "git_branch_prefix": "feature/",
            },
            "task_manager": {"enabled": True, "type": "linear", "team_key": "RULE"},
            "phases": {
                "customized": True,
                "phases": {"plan": {"enabled": True}},
            },
        }

        panel = generate_summary_panel(cfg)

        # Convert panel to string for content inspection
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Check all sections are present
        assert "Basics:" in output
        assert "python" in output
        assert "api" in output
        assert "pytest" in output
        assert "Git:" in output
        assert "Task Manager:" in output
        assert "Linear" in output.title() or "linear" in output.lower()
        assert "Phases:" in output
        assert "Security:" not in output
        assert "Webhooks:" not in output

    def test_summary_panel_shows_disabled_features(self) -> None:
        """Test that disabled features show appropriate indicators."""
        cfg = {
            "basics": {"language": "javascript", "platform": "web"},
            "git": {},
            "task_manager": {"enabled": False, "type": "none"},
            "phases": {"customized": False, "phases": {}},
        }

        panel = generate_summary_panel(cfg)

        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Check disabled features show appropriate state
        assert "Disabled" in output or "\u2717" in output

    def test_summary_panel_lists_files_to_create(self) -> None:
        """Test that summary panel lists files that will be created."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {},
            "phases": {
                "customized": True,
                "phases": {"plan": {"enabled": True}, "build": {"enabled": True}},
            },
        }

        panel = generate_summary_panel(cfg)

        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        assert "project.yaml" in output
        assert ".gitignore" in output
        # Check phase config files are listed
        assert "plan" in output
        assert "build" in output


class TestProjectYamlGeneration:
    """Tests for project.yaml generation."""

    def test_generate_project_yaml_basic(self) -> None:
        """Test project.yaml generation with minimal config."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {"enabled": False, "type": "none"},
        }

        yaml_content = generate_project_yaml(cfg)
        config = yaml.safe_load(yaml_content)

        assert config["name"] == "python"  # Falls back to language
        assert config["language"] == "python"
        assert config["platform"] == "cli"

    def test_generate_project_yaml_with_commands(self) -> None:
        """Test project.yaml includes test and build commands."""
        cfg = {
            "basics": {
                "project_name": "my-project",
                "language": "python",
                "platform": "api",
                "test_command": "pytest",
                "build_command": "python -m build",
            },
            "git": {},
            "task_manager": {"enabled": False, "type": "none"},
        }

        yaml_content = generate_project_yaml(cfg)
        config = yaml.safe_load(yaml_content)

        assert config["name"] == "my-project"
        assert config["test_command"] == "pytest"
        assert config["build_command"] == "python -m build"

    def test_generate_project_yaml_with_git(self) -> None:
        """Test project.yaml includes git config."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {
                "git_branch_prefix": "feat/",
            },
            "task_manager": {"enabled": False, "type": "none"},
        }

        yaml_content = generate_project_yaml(cfg)
        config = yaml.safe_load(yaml_content)

        assert config["git"]["branch_prefix"] == "feat/"

    def test_generate_project_yaml_always_has_git_section(self) -> None:
        """Test project.yaml always includes git section with defaults."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {"enabled": False, "type": "none"},
        }

        yaml_content = generate_project_yaml(cfg)
        config = yaml.safe_load(yaml_content)

        assert "git" in config
        assert config["git"]["branch_prefix"] == "feature/"

    def test_generate_project_yaml_with_task_manager(self) -> None:
        """Test project.yaml includes task manager when configured."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {
                "enabled": True,
                "type": "linear",
                "team_key": "RULE",
                "sync_comments": True,
            },
        }

        yaml_content = generate_project_yaml(cfg)
        config = yaml.safe_load(yaml_content)

        assert config["task_manager"]["type"] == "linear"
        assert config["task_manager"]["team_key"] == "RULE"
        assert config["task_manager"]["sync_comments"] is True

    def test_generate_project_yaml_omits_ship_section(self) -> None:
        """Test project.yaml omits ship section entirely.

        After the refactoring, ship config is always in phase config,
        not in project.yaml.
        """
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {"enabled": False, "type": "none"},
        }

        yaml_content = generate_project_yaml(cfg)
        config = yaml.safe_load(yaml_content)

        assert "ship" not in config

    def test_generate_project_yaml_includes_header_comment(self) -> None:
        """Test project.yaml includes header comment with date."""
        cfg = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {},
            "task_manager": {"enabled": False, "type": "none"},
        }

        yaml_content = generate_project_yaml(cfg)

        # The file starts with the title, then generation info
        assert "# ADW Project Configuration" in yaml_content
        assert "Generated by adw init" in yaml_content


class TestPhaseConfigGeneration:
    """Tests for phase-specific config generation."""

    def test_generate_phase_configs_all_phases_generated(self) -> None:
        """Test phase configs generated for ALL phases.

        The new behavior generates config files for all phases, not just
        customized ones, to provide full visibility into available options.
        """
        cfg = {
            "phases": {"customized": False, "phases": {}},
        }

        files = generate_phase_configs(cfg)

        # Configs are generated for ALL phases
        assert "commands/plan/config.yaml" in files
        assert "commands/build/config.yaml" in files
        assert "commands/validate/config.yaml" in files
        assert "commands/document/config.yaml" in files
        assert "commands/ship/config.yaml" in files

    def test_generate_phase_configs_for_customized_phases(self) -> None:
        """Test phase configs generated only for customized phases."""
        cfg = {
            "phases": {
                "customized": True,
                "phases": {
                    "plan": {"enabled": True},
                    "build": {"enabled": False},
                },
            },
        }

        files = generate_phase_configs(cfg)

        assert "commands/plan/config.yaml" in files
        assert "commands/build/config.yaml" in files

        plan_config = yaml.safe_load(files["commands/plan/config.yaml"])
        assert plan_config["enabled"] is True

        build_config = yaml.safe_load(files["commands/build/config.yaml"])
        assert build_config["enabled"] is False

    def test_generate_phase_configs_with_input_files(self) -> None:
        """Test phase config with input_files mapping."""
        cfg = {
            "phases": {
                "customized": True,
                "phases": {
                    "plan": {
                        "input_files": {"prd": "docs/prd.md", "arch": "docs/arch.md"}
                    },
                },
            },
        }

        files = generate_phase_configs(cfg)

        plan_config = yaml.safe_load(files["commands/plan/config.yaml"])
        assert plan_config["input_files"]["prd"] == "docs/prd.md"
        assert plan_config["input_files"]["arch"] == "docs/arch.md"

    def test_generate_phase_configs_includes_customized_values(self) -> None:
        """Test that customized phase values appear as active config.

        With the new YAML generator, customized values are output as active
        YAML while defaults appear as comments.
        """
        cfg = {
            "phases": {
                "customized": True,
                "phases": {
                    "validate": {
                        "enabled": False,  # Custom: disabled
                    },
                },
            },
        }

        files = generate_phase_configs(cfg)

        assert "commands/validate/config.yaml" in files
        validate_content = files["commands/validate/config.yaml"]

        # Check that the content includes our custom values
        assert "enabled: false" in validate_content  # Our custom disabled value

        # Verify it's valid YAML
        validate_config = yaml.safe_load(validate_content)
        assert validate_config["enabled"] is False

    def test_customized_ship_commands_reach_ship_config(self) -> None:
        """Ship commands set in the phases step land in the ship config file."""
        cfg = {
            "phases": {
                "customized": True,
                "phases": {
                    "ship": {
                        "enabled": True,
                        "commands": {
                            "version_bump": "npm version patch",
                            "publish": "npm publish",
                        },
                    },
                },
            },
        }

        files = generate_phase_configs(cfg)

        ship_config = yaml.safe_load(files["commands/ship/config.yaml"])
        assert ship_config["commands"] == {
            "version_bump": "npm version patch",
            "publish": "npm publish",
        }


class TestGitignoreGeneration:
    """Tests for .gitignore generation."""

    def test_generate_gitignore_content(self) -> None:
        """Test .gitignore contains expected entries."""
        content = generate_gitignore()

        assert "runs/" in content
        assert "logs/" in content
        assert "*.log" in content
        assert "state.json" in content

    def test_generate_gitignore_includes_env_file(self) -> None:
        """Test .gitignore excludes .env files."""
        content = generate_gitignore()

        assert ".env" in content


class TestEnvTemplateGeneration:
    """Tests for .env.template generation."""

    def test_generate_env_template_contains_linear_credentials(self) -> None:
        """Test .env.template includes Linear credential placeholders."""
        content = generate_env_template()

        assert "LINEAR_API_KEY=" in content
        assert "LINEAR_TEAM_ID=" in content

    def test_generate_env_template_contains_documentation(self) -> None:
        """Test .env.template includes helpful documentation."""
        content = generate_env_template()

        assert "Copy this file to .env" in content
        assert "gitignored" in content
        assert "Linear Settings" in content


def _fail_second_write() -> Callable[[Path, str | bytes], None]:
    """Wrap the real atomic_write so only its second call fails.

    Every other call, the rollback's restore included, really writes, so the
    backup-and-restore path runs.
    """
    calls = 0

    def write(path: Path, data: str | bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("Disk full")
        fs.atomic_write(path, data)

    return write


class TestAtomicWrite:
    """Tests for atomic file writing."""

    def test_atomic_write_creates_files(self) -> None:
        """Test atomic write creates all files successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adw_dir = Path(tmpdir) / ".adw"

            files = {
                "project.yaml": "name: test\n",
                ".gitignore": "runs/\n",
            }

            atomic_write_config(adw_dir, files)

            assert (adw_dir / "project.yaml").exists()
            assert (adw_dir / ".gitignore").exists()
            assert (adw_dir / "project.yaml").read_text() == "name: test\n"

    def test_atomic_write_creates_subdirectories(self) -> None:
        """Test atomic write creates nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adw_dir = Path(tmpdir) / ".adw"

            files = {
                "project.yaml": "name: test\n",
                "commands/plan/config.yaml": "timeout: 600\n",
            }

            atomic_write_config(adw_dir, files)

            assert (adw_dir / "commands" / "plan" / "config.yaml").exists()

    def test_atomic_write_rollback_on_failure(self) -> None:
        """Test atomic write rolls back on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adw_dir = Path(tmpdir) / ".adw"

            # Create first file successfully, then make second fail
            files = {
                "project.yaml": "name: test\n",
                "will_fail": "content",
            }

            with (
                patch("adw.cli.wizard.summary.atomic_write", _fail_second_write()),
                pytest.raises(ConfigWriteError) as exc_info,
            ):
                atomic_write_config(adw_dir, files)

            assert "Failed to write config" in str(exc_info.value)
            # Check that created file was rolled back
            assert not (adw_dir / "project.yaml").exists() or not adw_dir.exists()

    def test_atomic_write_preserves_existing_files_on_failure(self) -> None:
        """Test that pre-existing files are preserved when a later write fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adw_dir = Path(tmpdir) / ".adw"
            adw_dir.mkdir(parents=True)

            # Pre-create project.yaml with original content
            original_content = "name: original-project\nlanguage: python\n"
            (adw_dir / "project.yaml").write_text(original_content)

            # Try to write multiple files, with the second one failing
            files = {
                "project.yaml": "name: new-project\nlanguage: typescript\n",
                "new_file.yaml": "this will fail",
            }

            with (
                patch("adw.cli.wizard.summary.atomic_write", _fail_second_write()),
                pytest.raises(ConfigWriteError),
            ):
                atomic_write_config(adw_dir, files)

            # Verify original file content was restored
            assert (adw_dir / "project.yaml").exists()
            restored_content = (adw_dir / "project.yaml").read_text()
            assert restored_content == original_content

            # Verify new file was not created
            assert not (adw_dir / "new_file.yaml").exists()


class TestRunSummaryStep:
    """Tests for the main run_summary_step function."""

    CFG: dict[str, dict[str, Any]] = {  # noqa: RUF012
        "basics": {"language": "python", "platform": "cli"},
        "git": {},
        "task_manager": {"enabled": False, "type": "none"},
        "phases": {"customized": False, "phases": {}},
    }

    def test_confirm_writes_files_and_returns_true(self, tmp_path: Path) -> None:
        """Confirming writes the files and reports it."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.summary.Confirm.ask", return_value=True):
            written = run_summary_step(self.CFG, console, tmp_path)

        assert written is True
        assert (tmp_path / ".adw" / "project.yaml").exists()
        assert (tmp_path / ".adw" / ".gitignore").exists()

    def test_decline_writes_nothing_and_returns_false(self, tmp_path: Path) -> None:
        """Declining writes nothing and reports it."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.summary.Confirm.ask", return_value=False):
            written = run_summary_step(self.CFG, console, tmp_path)

        assert written is False
        assert not (tmp_path / ".adw").exists()

    def test_write_holds_off_ctrl_c(self, tmp_path: Path) -> None:
        """Ctrl+C is ignored while the files are written, registered and reported."""
        cfg = {
            **self.CFG,
            "global_registry": {
                "global_registry_enabled": True,
                "global_registry_name": "p",
            },
        }
        recorded: list[object] = []

        def record(*_: object, **__: object) -> None:
            recorded.append(signal.getsignal(signal.SIGINT))

        before = signal.getsignal(signal.SIGINT)
        with (
            patch("adw.cli.wizard.summary.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.summary.atomic_write_config", side_effect=record),
            patch(
                "adw.cli.wizard.summary._register_in_global_dashboard",
                side_effect=record,
            ),
            patch("adw.cli.wizard.summary._show_success_message", side_effect=record),
        ):
            run_summary_step(cfg, Console(force_terminal=True), tmp_path)

        assert recorded == [signal.SIG_IGN] * 3
        assert signal.getsignal(signal.SIGINT) == before
