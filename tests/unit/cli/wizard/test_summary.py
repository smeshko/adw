"""Tests for wizard summary and file generation step.

Tests the summary panel generation, configuration confirmation,
file generation, and atomic write functionality.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from rich.console import Console
from rich.panel import Panel

from adw.cli.wizard.summary import (
    ConfigWriteError,
    SummaryStepHandler,
    atomic_write_config,
    generate_gitignore,
    generate_phase_configs,
    generate_project_yaml,
    generate_summary_panel,
    run_summary_step,
)
from adw.models.wizard import WizardState


class TestSummaryPanelGeneration:
    """Tests for summary panel generation."""

    def test_generate_summary_panel_returns_panel(self) -> None:
        """Test that generate_summary_panel returns a Rich Panel."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {},
            "task_manager": {},
            "phases": {},
            "llm_retry": {},
            "security": {},
            "webhooks": {},
        }

        panel = generate_summary_panel(state)

        assert isinstance(panel, Panel)
        assert panel.title == "Configuration Summary"

    def test_summary_panel_shows_all_sections(self) -> None:
        """Test that summary panel includes all configuration sections."""
        state = WizardState()
        state.collected_config = {
            "basics": {
                "language": "python",
                "platform": "api",
                "test_command": "pytest",
                "build_command": "python -m build",
            },
            "git": {"enabled": True, "branch_prefix": "feature/", "auto_create_pr": True},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "linear", "team_key": "RULE"},
            "phases": {"customized_phases": ["plan"]},
            "llm_retry": {"customized": True, "max_retries": 5, "base_delay": 2.0},
            "security": {"allow_dangerous": False},
            "webhooks": {"enabled": True, "providers": {"linear": {"enabled": True}}},
        }

        panel = generate_summary_panel(state)

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
        assert "Ports:" in output
        assert "Task Manager:" in output
        assert "Linear" in output.title() or "linear" in output.lower()
        assert "Phases:" in output
        assert "LLM Retry:" in output
        assert "Security:" in output
        assert "Webhooks:" in output

    def test_summary_panel_shows_disabled_features(self) -> None:
        """Test that disabled features show appropriate indicators."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "javascript", "platform": "web"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "phases": {"customized_phases": []},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        panel = generate_summary_panel(state)

        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(panel)
        output = capture.get()

        # Check disabled features show appropriate state
        assert "Disabled" in output or "\u2717" in output

    def test_summary_panel_lists_files_to_create(self) -> None:
        """Test that summary panel lists files that will be created."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {},
            "task_manager": {},
            "phases": {"customized_phases": ["plan", "build"]},
            "llm_retry": {},
            "security": {},
            "webhooks": {},
        }

        panel = generate_summary_panel(state)

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
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["name"] == "python"  # Falls back to language
        assert config["language"] == "python"
        assert config["platform"] == "cli"

    def test_generate_project_yaml_with_commands(self) -> None:
        """Test project.yaml includes test and build commands."""
        state = WizardState()
        state.collected_config = {
            "basics": {
                "project_name": "my-project",
                "language": "python",
                "platform": "api",
                "test_command": "pytest",
                "build_command": "python -m build",
            },
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["name"] == "my-project"
        assert config["commands"]["test"] == "pytest"
        assert config["commands"]["build"] == "python -m build"

    def test_generate_project_yaml_with_git(self) -> None:
        """Test project.yaml includes git config when enabled."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": True, "branch_prefix": "feat/", "auto_create_pr": True},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["git"]["enabled"] is True
        assert config["git"]["branch_prefix"] == "feat/"
        assert config["git"]["auto_create_pr"] is True

    def test_generate_project_yaml_omits_git_when_disabled(self) -> None:
        """Test project.yaml omits git section when disabled."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert "git" not in config

    def test_generate_project_yaml_with_task_manager(self) -> None:
        """Test project.yaml includes task manager when configured."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "linear", "team_key": "RULE", "sync_comments": True},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["task_manager"]["type"] == "linear"
        assert config["task_manager"]["team_key"] == "RULE"
        assert config["task_manager"]["sync_comments"] is True

    def test_generate_project_yaml_custom_ports(self) -> None:
        """Test project.yaml includes ports when non-default."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 8000, "frontend_start": 8100},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["ports"]["backend_start"] == 8000
        assert config["ports"]["frontend_start"] == 8100

    def test_generate_project_yaml_omits_default_ports(self) -> None:
        """Test project.yaml omits ports when using defaults."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert "ports" not in config

    def test_generate_project_yaml_with_llm_retry(self) -> None:
        """Test project.yaml includes LLM retry when customized."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {
                "customized": True,
                "max_retries": 5,
                "base_delay": 2.0,
                "max_delay": 120.0,
                "multiplier": 3.0,
            },
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["llm"]["retry"]["max_retries"] == 5
        assert config["llm"]["retry"]["base_delay"] == 2.0
        assert config["llm"]["retry"]["max_delay"] == 120.0
        assert config["llm"]["retry"]["multiplier"] == 3.0

    def test_generate_project_yaml_with_webhooks(self) -> None:
        """Test project.yaml includes webhooks when enabled."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {
                "enabled": True,
                "port": 9000,
                "host": "127.0.0.1",
                "providers": {
                    "linear": {
                        "enabled": True,
                        "secret_env": "LINEAR_SECRET",
                        "command_prefix": "/run",
                        "trigger_label": "ai",
                    }
                },
            },
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["webhook"]["port"] == 9000
        assert config["webhook"]["host"] == "127.0.0.1"
        assert config["webhook"]["providers"]["linear"]["enabled"] is True
        assert config["webhook"]["providers"]["linear"]["secret_env"] == "LINEAR_SECRET"

    def test_generate_project_yaml_includes_header_comment(self) -> None:
        """Test project.yaml includes header comment with date."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {"backend_start": 9100, "frontend_start": 9200},
            "task_manager": {"type": "none"},
            "llm_retry": {"customized": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)

        assert yaml_content.startswith("# Generated by ADW Init Wizard")
        assert "# Date:" in yaml_content


class TestPhaseConfigGeneration:
    """Tests for phase-specific config generation."""

    def test_generate_phase_configs_empty_when_no_customization(self) -> None:
        """Test no phase configs generated when nothing customized."""
        state = WizardState()
        state.collected_config = {
            "phases": {"customized_phases": []},
        }

        files = generate_phase_configs(state)

        assert files == {}

    def test_generate_phase_configs_for_customized_phases(self) -> None:
        """Test phase configs generated only for customized phases."""
        state = WizardState()
        state.collected_config = {
            "phases": {
                "customized_phases": ["plan", "build"],
                "phase_configs": {
                    "plan": {"timeout_seconds": 600, "pre_hook": "echo starting"},
                    "build": {"post_hook": "npm test"},
                },
            },
        }

        files = generate_phase_configs(state)

        assert "commands/plan/config.yaml" in files
        assert "commands/build/config.yaml" in files

        plan_config = yaml.safe_load(files["commands/plan/config.yaml"])
        assert plan_config["timeout_seconds"] == 600
        assert plan_config["pre_hook"] == "echo starting"

        build_config = yaml.safe_load(files["commands/build/config.yaml"])
        assert build_config["post_hook"] == "npm test"

    def test_generate_phase_configs_with_input_files(self) -> None:
        """Test phase config with input_files mapping."""
        state = WizardState()
        state.collected_config = {
            "phases": {
                "customized_phases": ["plan"],
                "phase_configs": {
                    "plan": {"input_files": {"prd": "docs/prd.md", "arch": "docs/arch.md"}},
                },
            },
        }

        files = generate_phase_configs(state)

        plan_config = yaml.safe_load(files["commands/plan/config.yaml"])
        assert plan_config["input_files"]["prd"] == "docs/prd.md"
        assert plan_config["input_files"]["arch"] == "docs/arch.md"


class TestGitignoreGeneration:
    """Tests for .gitignore generation."""

    def test_generate_gitignore_content(self) -> None:
        """Test .gitignore contains expected entries."""
        content = generate_gitignore()

        assert "runs/" in content
        assert "logs/" in content
        assert "*.log" in content
        assert "state.json" in content


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

            # Mock the second write to fail
            original_write_text = Path.write_text
            call_count = [0]

            def failing_write_text(self, content, *args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 2:  # Fail on second file
                    raise OSError("Disk full")
                return original_write_text(self, content, *args, **kwargs)

            with patch.object(Path, "write_text", failing_write_text):
                with pytest.raises(ConfigWriteError) as exc_info:
                    atomic_write_config(adw_dir, files)

            assert "Failed to write config" in str(exc_info.value)
            # Check that created file was rolled back
            assert not (adw_dir / "project.yaml").exists() or not adw_dir.exists()


class TestRunSummaryStep:
    """Tests for the main run_summary_step function."""

    def test_run_summary_step_confirmed(self) -> None:
        """Test full flow when user confirms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            console = Console(force_terminal=True)
            state = WizardState()
            state.collected_config = {
                "basics": {"language": "python", "platform": "cli"},
                "git": {"enabled": False},
                "ports": {"backend_start": 9100, "frontend_start": 9200},
                "task_manager": {"type": "none"},
                "phases": {"customized_phases": []},
                "llm_retry": {"customized": False},
                "security": {},
                "webhooks": {"enabled": False},
            }

            with patch("adw.cli.wizard.summary.Confirm.ask", return_value=True):
                result = run_summary_step(state, console, Path(tmpdir))

            assert result["confirmed"] is True
            assert result["action"] == "complete"
            assert len(result["files_created"]) > 0

            # Verify files were created
            adw_dir = Path(tmpdir) / ".adw"
            assert (adw_dir / "project.yaml").exists()
            assert (adw_dir / ".gitignore").exists()

    def test_run_summary_step_start_over(self) -> None:
        """Test flow when user declines and chooses start over."""
        console = Console(force_terminal=True)
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {},
            "task_manager": {},
            "phases": {},
            "llm_retry": {},
            "security": {},
            "webhooks": {},
        }

        with (
            patch("adw.cli.wizard.summary.Confirm.ask", return_value=False),
            patch("adw.cli.wizard.summary.Prompt.ask", return_value="s"),
        ):
            result = run_summary_step(state, console)

        assert result["confirmed"] is False
        assert result["action"] == "start_over"
        assert result["files_created"] == []

    def test_run_summary_step_cancel(self) -> None:
        """Test flow when user declines and chooses cancel."""
        console = Console(force_terminal=True)
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"enabled": False},
            "ports": {},
            "task_manager": {},
            "phases": {},
            "llm_retry": {},
            "security": {},
            "webhooks": {},
        }

        with (
            patch("adw.cli.wizard.summary.Confirm.ask", return_value=False),
            patch("adw.cli.wizard.summary.Prompt.ask", return_value="c"),
        ):
            result = run_summary_step(state, console)

        assert result["confirmed"] is False
        assert result["action"] == "cancel"
        assert result["files_created"] == []


class TestSummaryStepHandler:
    """Tests for SummaryStepHandler class."""

    def test_handler_uses_project_root(self) -> None:
        """Test that handler respects project_root parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SummaryStepHandler(project_root=Path(tmpdir))
            console = Console(force_terminal=True)
            state = WizardState()
            state.collected_config = {
                "basics": {"language": "python", "platform": "cli"},
                "git": {"enabled": False},
                "ports": {"backend_start": 9100, "frontend_start": 9200},
                "task_manager": {"type": "none"},
                "phases": {"customized_phases": []},
                "llm_retry": {"customized": False},
                "security": {},
                "webhooks": {"enabled": False},
            }

            with patch("adw.cli.wizard.summary.Confirm.ask", return_value=True):
                result = handler.execute(state, console)

            assert result["confirmed"] is True
            # Files should be in the specified project root
            adw_dir = Path(tmpdir) / ".adw"
            assert adw_dir.exists()

    def test_handler_defaults_to_cwd(self) -> None:
        """Test that handler defaults to current working directory."""
        handler = SummaryStepHandler()
        assert handler.project_root == Path.cwd()
