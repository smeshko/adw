"""Tests for wizard summary and file generation step.

Tests the summary panel generation, configuration confirmation,
file generation, and atomic write functionality.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from rich.console import Console
from rich.panel import Panel

from adw.cli.wizard.summary import (
    ConfigWriteError,
    SummaryStepHandler,
    atomic_write_config,
    generate_env_template,
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
            "git": {"git_enabled": False},
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
            "git": {
                "git_enabled": True,
                "git_branch_prefix": "feature/",
                "git_auto_create_pr": True,
            },
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": True, "type": "linear", "team_key": "RULE"},
            "phases": {
                "customized": True,
                "phases": {"plan": {"timeout_seconds": 600}},
            },
            "ship": {
                "enabled": True,
                "commands": {
                    "version_bump": "npm version patch",
                },
                "post_publish": ["git push --tags"],
                "pr": {
                    "merge_on_success": True,
                    "delete_branch_on_merge": True,
                    "merge_method": "squash",
                },
            },
            "llm_retry": {
                "retry_custom": True,
                "retry_max_retries": 5,
                "retry_base_delay": 2.0,
            },
            "security": {"security_allow_dangerous": False},
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
        assert "Ship:" in output
        assert "LLM Retry:" in output
        assert "Security:" in output
        assert "Webhooks:" in output

    def test_summary_panel_shows_disabled_features(self) -> None:
        """Test that disabled features show appropriate indicators."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "javascript", "platform": "web"},
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "phases": {"customized": False, "phases": {}},
            "ship": {
                "enabled": True,
                "commands": {},
                "post_publish": [],
                "pr": {
                    "merge_on_success": False,
                    "delete_branch_on_merge": True,
                    "merge_method": "squash",
                },
            },
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {},
            "task_manager": {},
            "phases": {
                "customized": True,
                "phases": {"plan": {"timeout": 600}, "build": {"pre_hook": "test"}},
            },
            "ship": {"enabled": True, "commands": {}, "post_publish": [], "pr": {}},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert config["name"] == "my-project"
        assert config["test_command"] == "pytest"
        assert config["build_command"] == "python -m build"

    def test_generate_project_yaml_with_git(self) -> None:
        """Test project.yaml includes git config when enabled."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {
                "git_enabled": True,
                "git_branch_prefix": "feat/",
                "git_auto_create_pr": True,
            },
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {
                "enabled": True,
                "type": "linear",
                "team_key": "RULE",
                "sync_comments": True,
            },
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 8000, "frontend_port_start": 8100},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        # ISS-032: Ports are now under worktree.port_range
        assert config["worktree"]["port_range"]["backend_start"] == 8000
        assert config["worktree"]["port_range"]["frontend_start"] == 8100

    def test_generate_project_yaml_omits_default_ports(self) -> None:
        """Test project.yaml omits ports when using defaults."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {
                "retry_custom": True,
                "retry_max_retries": 5,
                "retry_base_delay": 2.0,
                "retry_max_delay": 120.0,
                "retry_multiplier": 3.0,
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

    def test_generate_project_yaml_ship_moved_to_phase_config(self) -> None:
        """Test project.yaml no longer includes ship (ISS-031: moved to phase config).

        Ship configuration has been moved from project.yaml to the phase-specific
        config file at .adw/commands/ship/config.yaml. This test verifies that
        the ship section is no longer generated in project.yaml.
        """
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "ship": {
                "enabled": True,
                "commands": {
                    "version_bump": "npm version patch",
                    "publish": "npm publish",
                },
                "post_publish": ["git push --tags", "echo 'deployed'"],
                "pr": {
                    "merge_on_success": True,
                    "delete_branch_on_merge": True,
                    "merge_method": "squash",
                },
            },
            "llm_retry": {"retry_custom": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        # Ship config is now in .adw/commands/ship/config.yaml, not project.yaml
        assert "ship" not in config

    def test_generate_project_yaml_omits_ship_section(self) -> None:
        """Test project.yaml omits ship section entirely (ISS-031).

        After the refactoring, ship config is always in phase config,
        not in project.yaml.
        """
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "ship": {
                "enabled": True,
                "commands": {},
                "post_publish": [],
                "pr": {
                    "merge_on_success": False,
                    "delete_branch_on_merge": True,
                    "merge_method": "squash",
                },
            },
            "llm_retry": {"retry_custom": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)
        config = yaml.safe_load(yaml_content)

        assert "ship" not in config

    def test_generate_project_yaml_with_webhooks(self) -> None:
        """Test project.yaml includes webhooks when enabled."""
        state = WizardState()
        state.collected_config = {
            "basics": {"language": "python", "platform": "cli"},
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
            "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
            "task_manager": {"enabled": False, "type": "none"},
            "llm_retry": {"retry_custom": False},
            "security": {},
            "webhooks": {"enabled": False},
        }

        yaml_content = generate_project_yaml(state)

        # ISS-032: New format starts with title, then generation info
        assert "# ADW Project Configuration" in yaml_content
        assert "Generated by ADW Init Wizard" in yaml_content


class TestPhaseConfigGeneration:
    """Tests for phase-specific config generation."""

    def test_generate_phase_configs_all_phases_generated(self) -> None:
        """Test phase configs generated for ALL phases (ISS-032).

        The new behavior generates config files for all phases, not just
        customized ones, to provide full visibility into available options.
        """
        state = WizardState()
        state.collected_config = {
            "phases": {"customized": False, "phases": {}},
        }

        files = generate_phase_configs(state)

        # ISS-032: Now generates configs for ALL phases
        assert "commands/plan/config.yaml" in files
        assert "commands/build/config.yaml" in files
        assert "commands/validate/config.yaml" in files
        assert "commands/document/config.yaml" in files
        assert "commands/ship/config.yaml" in files

    def test_generate_phase_configs_for_customized_phases(self) -> None:
        """Test phase configs generated only for customized phases."""
        state = WizardState()
        state.collected_config = {
            "phases": {
                "customized": True,
                "phases": {
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
                "customized": True,
                "phases": {
                    "plan": {
                        "input_files": {"prd": "docs/prd.md", "arch": "docs/arch.md"}
                    },
                },
            },
        }

        files = generate_phase_configs(state)

        plan_config = yaml.safe_load(files["commands/plan/config.yaml"])
        assert plan_config["input_files"]["prd"] == "docs/prd.md"
        assert plan_config["input_files"]["arch"] == "docs/arch.md"

    def test_generate_phase_configs_includes_customized_values(self) -> None:
        """Test that customized phase values appear as active config (ISS-032).

        With the new YAML generator, customized values are output as active
        YAML while defaults appear as comments.
        """
        state = WizardState()
        state.collected_config = {
            "phases": {
                "customized": True,
                "phases": {
                    "validate": {
                        "timeout_seconds": 600,
                        "enabled": False,  # Custom: disabled
                    },
                },
            },
        }

        files = generate_phase_configs(state)

        assert "commands/validate/config.yaml" in files
        validate_content = files["commands/validate/config.yaml"]

        # ISS-032: Check that the content includes our custom values
        # Note: The new generator always outputs enabled and timeout_seconds
        # based on the config passed, with defaults as comments
        assert "enabled: false" in validate_content  # Our custom disabled value
        assert "timeout_seconds: 600" in validate_content  # Our custom timeout

        # Verify it's valid YAML
        validate_config = yaml.safe_load(validate_content)
        assert validate_config["enabled"] is False
        assert validate_config["timeout_seconds"] == 600


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
        """Test .gitignore excludes .env files (ISS-028)."""
        content = generate_gitignore()

        assert ".env" in content


class TestEnvTemplateGeneration:
    """Tests for .env.template generation (ISS-028)."""

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

            with (
                patch.object(Path, "write_text", failing_write_text),
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

            # Mock write_text to fail on the second file
            original_write_text = Path.write_text
            call_count = [0]

            def failing_write_text(self, content, *args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 2:  # Fail on second file write
                    raise OSError("Disk full")
                return original_write_text(self, content, *args, **kwargs)

            with (
                patch.object(Path, "write_text", failing_write_text),
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

    def test_run_summary_step_confirmed(self) -> None:
        """Test full flow when user confirms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            console = Console(force_terminal=True)
            state = WizardState()
            state.collected_config = {
                "basics": {"language": "python", "platform": "cli"},
                "git": {"git_enabled": False},
                "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
                "task_manager": {"enabled": False, "type": "none"},
                "phases": {"customized": False, "phases": {}},
                "llm_retry": {"retry_custom": False},
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
            "git": {"git_enabled": False},
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
            "git": {"git_enabled": False},
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
                "git": {"git_enabled": False},
                "ports": {"backend_port_start": 9100, "frontend_port_start": 9200},
                "task_manager": {"enabled": False, "type": "none"},
                "phases": {"customized": False, "phases": {}},
                "llm_retry": {"retry_custom": False},
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
