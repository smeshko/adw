"""Tests for wizard task manager configuration step.

Tests the team key validation, prompt flows, state mapping configuration,
and the generated config for the task manager step.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
import yaml
from rich.console import Console

from adw.cli.wizard.task_manager import (
    DEFAULT_LABEL_PREFIX,
    TEAM_KEY_PATTERN,
    run_task_manager_step,
    validate_team_key,
)
from adw.models.config import DEFAULT_STATE_MAPPING


class TestTeamKeyValidation:
    """Tests for validate_team_key function."""

    @pytest.mark.parametrize(
        "key,expected_valid,expected_result",
        [
            ("RULE", True, "RULE"),
            ("ENG", True, "ENG"),
            ("ADW", True, "ADW"),
            ("AB", True, "AB"),  # Minimum length
            ("ABCDEFGHIJ", True, "ABCDEFGHIJ"),  # Maximum length
        ],
    )
    def test_validate_team_key_valid_keys(
        self, key: str, expected_valid: bool, expected_result: str
    ) -> None:
        """Test validation accepts valid team keys."""
        is_valid, result = validate_team_key(key)
        assert is_valid == expected_valid
        assert result == expected_result

    def test_validate_team_key_auto_uppercase(self) -> None:
        """Test that lowercase keys are normalized to uppercase."""
        is_valid, result = validate_team_key("rule")
        assert is_valid is True
        assert result == "RULE"

    def test_validate_team_key_strips_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        is_valid, result = validate_team_key("  RULE  ")
        assert is_valid is True
        assert result == "RULE"

    @pytest.mark.parametrize(
        "key,error_substring",
        [
            ("R", "2-10 uppercase letters"),  # Too short
            ("ABCDEFGHIJK", "2-10 uppercase letters"),  # Too long (11 chars)
            ("RULE-123", "2-10 uppercase letters"),  # Invalid chars
            ("RULE123", "2-10 uppercase letters"),  # Contains numbers
            ("", "cannot be empty"),  # Empty
            ("   ", "cannot be empty"),  # Whitespace only
        ],
    )
    def test_validate_team_key_invalid_keys(
        self, key: str, error_substring: str
    ) -> None:
        """Test validation rejects invalid team keys with appropriate messages."""
        is_valid, error_message = validate_team_key(key)
        assert is_valid is False
        assert error_substring in error_message


class TestDisabledFlow:
    """Tests for task manager disabled flow."""

    def test_disabled_returns_none_type(self) -> None:
        """Test that disabled task manager returns type='none'."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.task_manager.Confirm.ask", return_value=False):
            result = run_task_manager_step(console)

        assert result["enabled"] is False
        assert result["type"] == "none"

    def test_disabled_returns_default_values(self) -> None:
        """Test that disabled task manager returns sensible defaults."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.task_manager.Confirm.ask", return_value=False):
            result = run_task_manager_step(console)

        assert result["team_key"] is None
        assert result["sync_comments"] is False
        assert result["labels_enabled"] is True
        assert result["label_prefix"] == DEFAULT_LABEL_PREFIX
        assert result["state_mapping"] is None


class TestEnabledFlow:
    """Tests for task manager enabled flow with all options."""

    def test_enabled_basic_flow(self) -> None:
        """Test enabled task manager collects basic configuration."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, configure_mapping
            mock_confirm.side_effect = [True, False, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(console)

        assert result["enabled"] is True
        assert result["type"] == "linear"
        assert result["team_key"] == "TEAM"

    def test_enabled_with_sync_comments(self) -> None:
        """Test enabled with sync comments."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, configure_mapping
            mock_confirm.side_effect = [True, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "RULE",
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(console)

        assert result["sync_comments"] is True

    def test_enabled_with_labels_disabled(self) -> None:
        """Test labels can be disabled."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled (no), configure_mapping
            mock_confirm.side_effect = [True, False, False, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                # No label prefix prompt when labels disabled
            ]

            result = run_task_manager_step(console)

        assert result["labels_enabled"] is False
        assert result["label_prefix"] is None


class TestStateMappingConfiguration:
    """Tests for state mapping configuration."""

    def test_state_mapping_not_configured(self) -> None:
        """Test state mapping is None when not configured."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, configure_mapping
            mock_confirm.side_effect = [True, False, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(console)

        assert result["state_mapping"] is None

    def test_state_mapping_with_custom_values(self) -> None:
        """Test state mapping with custom phase mappings."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, configure_mapping (yes)
            mock_confirm.side_effect = [True, False, True, True]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_LABEL_PREFIX,
                "Planning",  # plan
                "Building",  # build
                "Reviewing",  # validate
                "Documenting",  # document
                "Shipped",  # ship
                "Failed",  # failed
            ]

            result = run_task_manager_step(console)

        assert result["state_mapping"] is not None
        assert result["state_mapping"]["plan"] == "Planning"
        assert result["state_mapping"]["build"] == "Building"
        assert result["state_mapping"]["validate"] == "Reviewing"
        assert result["state_mapping"]["document"] == "Documenting"
        assert result["state_mapping"]["ship"] == "Shipped"
        assert result["state_mapping"]["failed"] == "Failed"

    def test_state_mapping_accepts_defaults(self) -> None:
        """Test state mapping accepts default values when user just presses enter."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, configure_mapping (yes)
            mock_confirm.side_effect = [True, False, True, True]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_LABEL_PREFIX,
                *DEFAULT_STATE_MAPPING.values(),
            ]

            result = run_task_manager_step(console)

        assert result["state_mapping"] is not None
        assert result["state_mapping"] == DEFAULT_STATE_MAPPING


class TestGeneratedConfig:
    """Tests that the step's answers produce a loadable project.yaml."""

    def test_accepted_defaults_yield_ship_mapping(self) -> None:
        """Accepting every default mapping prompt keeps ship -> Done (B17)."""
        from adw.cli.wizard.task_manager import _prompt_state_mapping
        from adw.config.registry import ConfigRegistry
        from adw.config.yaml_generator import YAMLWithComments
        from adw.models.config import ProjectConfig

        console = Console(file=io.StringIO())
        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask", return_value=True),
            patch(
                "adw.cli.wizard.task_manager.Prompt.ask",
                side_effect=lambda *a, **kw: kw["default"],
            ),
        ):
            state_mapping = _prompt_state_mapping(console)

        cfg = {
            "basics": {"project_name": "p", "language": "python"},
            "task_manager": {
                "enabled": True,
                "type": "linear",
                "state_mapping": state_mapping,
            },
        }
        content = YAMLWithComments(ConfigRegistry()).generate_project_yaml(cfg)
        config = ProjectConfig.model_validate(yaml.safe_load(content))

        assert config.task_manager.state_mapping["ship"] == "Done"


class TestConstants:
    """Tests for module constants."""

    def test_team_key_pattern_matches_expected(self) -> None:
        """Test team key pattern matches expected format."""
        assert TEAM_KEY_PATTERN.match("AB")  # Min length
        assert TEAM_KEY_PATTERN.match("ABCDEFGHIJ")  # Max length
        assert not TEAM_KEY_PATTERN.match("A")  # Too short
        assert not TEAM_KEY_PATTERN.match("ABCDEFGHIJK")  # Too long
        assert not TEAM_KEY_PATTERN.match("AB1")  # Contains number
