"""Tests for wizard task manager configuration step.

Tests the team key validation, prompt flows, state mapping configuration,
and wizard state integration for the task manager step.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.wizard.task_manager import (
    DEFAULT_LABEL_PREFIX,
    DEFAULT_PR_TITLE_FORMAT,
    DEFAULT_STATE_MAPPINGS,
    TEAM_KEY_PATTERN,
    TaskManagerStepHandler,
    run_task_manager_step,
    validate_team_key,
)
from adw.models.wizard import WizardState


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
        state = WizardState()

        with patch("adw.cli.wizard.task_manager.Confirm.ask", return_value=False):
            result = run_task_manager_step(state, console)

        assert result["enabled"] is False
        assert result["type"] == "none"

    def test_disabled_returns_default_values(self) -> None:
        """Test that disabled task manager returns sensible defaults."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.task_manager.Confirm.ask", return_value=False):
            result = run_task_manager_step(state, console)

        assert result["team_key"] is None
        assert result["sync_comments"] is False
        assert result["comment_on_failure_only"] is False
        assert result["pr_title_format"] == DEFAULT_PR_TITLE_FORMAT
        assert result["labels_enabled"] is True
        assert result["label_prefix"] == DEFAULT_LABEL_PREFIX
        assert result["auto_close"] is False
        assert result["include_labels"] is True
        assert result["include_parent"] is True
        assert result["state_mapping"] is None


class TestEnabledFlow:
    """Tests for task manager enabled flow with all options."""

    def test_enabled_basic_flow(self) -> None:
        """Test enabled task manager collects basic configuration."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, auto_close,
            # include_labels, include_parent, configure_mapping
            mock_confirm.side_effect = [True, False, True, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["enabled"] is True
        assert result["type"] == "linear"
        assert result["team_key"] == "TEAM"

    def test_enabled_with_sync_comments(self) -> None:
        """Test enabled with sync comments and failure-only option."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, comment_failures_only, labels_enabled,
            # auto_close, include_labels, include_parent, configure_mapping
            mock_confirm.side_effect = [
                True,
                True,
                True,
                True,
                False,
                True,
                True,
                False,
            ]
            mock_prompt.side_effect = [
                "linear",
                "RULE",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["sync_comments"] is True
        assert result["comment_on_failure_only"] is True

    def test_enabled_comment_failures_only_skipped_when_no_sync(self) -> None:
        """Test comment_failures_only is False when sync_comments is disabled."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments (no), labels_enabled, auto_close,
            # include_labels, include_parent, configure_mapping
            mock_confirm.side_effect = [True, False, True, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["sync_comments"] is False
        assert result["comment_on_failure_only"] is False

    def test_enabled_with_custom_pr_title_format(self) -> None:
        """Test custom PR title format."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False, True, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                "[{task_id}] {description}",  # Custom format
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["pr_title_format"] == "[{task_id}] {description}"

    def test_enabled_with_labels_disabled(self) -> None:
        """Test labels can be disabled."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled (no), auto_close,
            # include_labels, include_parent, configure_mapping
            mock_confirm.side_effect = [True, False, False, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                # No label prefix prompt when labels disabled
            ]

            result = run_task_manager_step(state, console)

        assert result["labels_enabled"] is False
        assert result["label_prefix"] is None

    def test_enabled_with_auto_close(self) -> None:
        """Test auto_close option."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, auto_close (yes),
            # include_labels, include_parent, configure_mapping
            mock_confirm.side_effect = [True, False, True, True, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["auto_close"] is True


class TestContextOptions:
    """Tests for context inclusion options."""

    def test_context_options_disabled(self) -> None:
        """Test context options can be disabled."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, auto_close,
            # include_labels (no), include_parent (no), configure_mapping
            mock_confirm.side_effect = [True, False, True, False, False, False, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["include_labels"] is False
        assert result["include_parent"] is False

    def test_context_options_enabled(self) -> None:
        """Test context options enabled by default."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # enable, sync_comments, labels_enabled, auto_close,
            # include_labels (yes), include_parent (yes), configure_mapping
            mock_confirm.side_effect = [True, False, True, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["include_labels"] is True
        assert result["include_parent"] is True


class TestStateMappingConfiguration:
    """Tests for state mapping configuration."""

    def test_state_mapping_not_configured(self) -> None:
        """Test state mapping is None when not configured."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # configure_mapping is last and False
            mock_confirm.side_effect = [True, False, True, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]

            result = run_task_manager_step(state, console)

        assert result["state_mapping"] is None

    def test_state_mapping_with_custom_values(self) -> None:
        """Test state mapping with custom phase mappings."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            # configure_mapping is last and True
            mock_confirm.side_effect = [True, False, True, False, True, True, True]
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
                "Planning",  # plan
                "Building",  # build
                "Reviewing",  # validate
                "Documenting",  # document
                "Failed",  # failed
            ]

            result = run_task_manager_step(state, console)

        assert result["state_mapping"] is not None
        assert result["state_mapping"]["plan"] == "Planning"
        assert result["state_mapping"]["build"] == "Building"
        assert result["state_mapping"]["validate"] == "Reviewing"
        assert result["state_mapping"]["document"] == "Documenting"
        assert result["state_mapping"]["failed"] == "Failed"

    def test_state_mapping_accepts_defaults(self) -> None:
        """Test state mapping accepts default values when user just presses enter."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False, True, False, True, True, True]
            # Use defaults for all state mappings
            mock_prompt.side_effect = [
                "linear",
                "TEAM",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
                DEFAULT_STATE_MAPPINGS["plan"],
                DEFAULT_STATE_MAPPINGS["build"],
                DEFAULT_STATE_MAPPINGS["validate"],
                DEFAULT_STATE_MAPPINGS["document"],
                DEFAULT_STATE_MAPPINGS["failed"],
            ]

            result = run_task_manager_step(state, console)

        assert result["state_mapping"] is not None
        assert result["state_mapping"] == DEFAULT_STATE_MAPPINGS


class TestTaskManagerStepHandler:
    """Tests for TaskManagerStepHandler class."""

    def test_handler_execute_calls_run_task_manager_step(self) -> None:
        """Test handler execute method calls the correct function."""
        handler = TaskManagerStepHandler()
        state = WizardState()
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.task_manager.Confirm.ask", return_value=False):
            result = handler.execute(state, console)

        assert result["enabled"] is False
        assert result["type"] == "none"


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_config_stored_via_flow_controller_pattern(self) -> None:
        """Test that config can be stored using flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.task_manager.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.task_manager.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False, True, False, True, True, False]
            mock_prompt.side_effect = [
                "linear",
                "ADW",
                DEFAULT_PR_TITLE_FORMAT,
                DEFAULT_LABEL_PREFIX,
            ]
            config = run_task_manager_step(state, console)

            # Simulate what flow controller does
            state.update_config("task_manager", config)
            state.mark_completed("task_manager")

        # Verify storage
        stored = state.get_step_config("task_manager")
        assert stored["type"] == "linear"
        assert stored["team_key"] == "ADW"
        assert "task_manager" in state.completed_steps


class TestConstants:
    """Tests for module constants."""

    def test_default_state_mappings_covers_all_phases(self) -> None:
        """Test that default state mappings cover all ADW phases."""
        expected_phases = {"plan", "build", "validate", "document", "failed"}
        actual_phases = set(DEFAULT_STATE_MAPPINGS.keys())
        assert expected_phases == actual_phases

    def test_team_key_pattern_matches_expected(self) -> None:
        """Test team key pattern matches expected format."""
        assert TEAM_KEY_PATTERN.match("AB")  # Min length
        assert TEAM_KEY_PATTERN.match("ABCDEFGHIJ")  # Max length
        assert not TEAM_KEY_PATTERN.match("A")  # Too short
        assert not TEAM_KEY_PATTERN.match("ABCDEFGHIJK")  # Too long
        assert not TEAM_KEY_PATTERN.match("AB1")  # Contains number
