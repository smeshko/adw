"""Tests for the WizardState model.

This module tests the WizardState Pydantic model that tracks
wizard progress, configuration, and navigation history.
"""

from __future__ import annotations

import pytest

from adw.models.wizard import WizardState


class TestWizardStateFields:
    """Tests for WizardState field initialization."""

    def test_default_current_step(self) -> None:
        """Default current step is 'basics'."""
        state = WizardState()
        assert state.current_step == "basics"

    def test_default_completed_steps(self) -> None:
        """Default completed steps is empty list."""
        state = WizardState()
        assert state.completed_steps == []

    def test_default_collected_config(self) -> None:
        """Default collected config is empty dict."""
        state = WizardState()
        assert state.collected_config == {}

    def test_default_navigation_history(self) -> None:
        """Default navigation history contains 'basics'."""
        state = WizardState()
        assert state.navigation_history == ["basics"]

    def test_default_history_position(self) -> None:
        """Default history position is 0."""
        state = WizardState()
        assert state.history_position == 0

    def test_custom_initialization(self) -> None:
        """WizardState accepts custom values."""
        state = WizardState(
            current_step="git",
            completed_steps=["basics"],
            collected_config={"basics": {"language": "python"}},
            navigation_history=["basics", "git"],
            history_position=1,
        )
        assert state.current_step == "git"
        assert state.completed_steps == ["basics"]
        assert state.collected_config == {"basics": {"language": "python"}}
        assert state.navigation_history == ["basics", "git"]
        assert state.history_position == 1


class TestMarkCompleted:
    """Tests for mark_completed method."""

    def test_mark_step_completed(self) -> None:
        """Marking a step adds it to completed_steps."""
        state = WizardState()
        state.mark_completed("basics")
        assert "basics" in state.completed_steps

    def test_mark_completed_no_duplicates(self) -> None:
        """Marking same step twice does not create duplicates."""
        state = WizardState()
        state.mark_completed("basics")
        state.mark_completed("basics")
        assert state.completed_steps.count("basics") == 1

    def test_mark_multiple_steps(self) -> None:
        """Multiple steps can be marked completed."""
        state = WizardState()
        state.mark_completed("basics")
        state.mark_completed("git")
        state.mark_completed("ports")
        assert state.completed_steps == ["basics", "git", "ports"]


class TestNavigationHistory:
    """Tests for navigation history methods."""

    def test_can_go_back_at_start(self) -> None:
        """Cannot go back when at position 0."""
        state = WizardState()
        assert state.can_go_back() is False

    def test_can_go_back_after_navigation(self) -> None:
        """Can go back after navigating forward."""
        state = WizardState()
        state.navigate_to("git")
        assert state.can_go_back() is True

    def test_can_go_forward_at_end(self) -> None:
        """Cannot go forward when at end of history."""
        state = WizardState()
        assert state.can_go_forward() is False

    def test_can_go_forward_after_back(self) -> None:
        """Can go forward after going back."""
        state = WizardState()
        state.navigate_to("git")
        state.go_back_in_history()
        assert state.can_go_forward() is True

    def test_navigate_to_adds_to_history(self) -> None:
        """Navigating to new step adds it to history."""
        state = WizardState()
        state.navigate_to("git")
        assert state.navigation_history == ["basics", "git"]
        assert state.current_step == "git"
        assert state.history_position == 1

    def test_navigate_to_truncates_forward_history(self) -> None:
        """Navigating to new step after going back truncates forward history."""
        state = WizardState()
        state.navigate_to("git")
        state.navigate_to("ports")
        state.go_back_in_history()  # Now at git
        state.navigate_to("task_manager")  # Should replace ports

        assert state.navigation_history == ["basics", "git", "task_manager"]
        assert state.current_step == "task_manager"

    def test_navigate_to_same_step_no_duplicate(self) -> None:
        """Navigating to current step does not duplicate in history."""
        state = WizardState()
        state.navigate_to("basics")
        assert state.navigation_history == ["basics"]

    def test_go_back_in_history(self) -> None:
        """Going back moves to previous step in history."""
        state = WizardState()
        state.navigate_to("git")
        state.navigate_to("ports")

        result = state.go_back_in_history()

        assert result == "git"
        assert state.current_step == "git"
        assert state.history_position == 1

    def test_go_back_at_start_returns_none(self) -> None:
        """Going back at start returns None."""
        state = WizardState()
        result = state.go_back_in_history()
        assert result is None
        assert state.current_step == "basics"

    def test_go_forward_in_history(self) -> None:
        """Going forward moves to next step in history."""
        state = WizardState()
        state.navigate_to("git")
        state.navigate_to("ports")
        state.go_back_in_history()  # At git

        result = state.go_forward_in_history()

        assert result == "ports"
        assert state.current_step == "ports"
        assert state.history_position == 2

    def test_go_forward_at_end_returns_none(self) -> None:
        """Going forward at end returns None."""
        state = WizardState()
        result = state.go_forward_in_history()
        assert result is None
        assert state.current_step == "basics"


class TestConfigManagement:
    """Tests for configuration management methods."""

    def test_update_config(self) -> None:
        """Update config stores values for step."""
        state = WizardState()
        state.update_config("basics", {"language": "python", "name": "myproject"})

        assert state.collected_config["basics"] == {
            "language": "python",
            "name": "myproject",
        }

    def test_update_config_overwrites(self) -> None:
        """Update config overwrites previous values."""
        state = WizardState()
        state.update_config("basics", {"language": "python"})
        state.update_config("basics", {"language": "javascript"})

        assert state.collected_config["basics"]["language"] == "javascript"

    def test_get_step_config(self) -> None:
        """Get step config returns stored values."""
        state = WizardState()
        state.update_config("git", {"auto_commit": True})

        result = state.get_step_config("git")
        assert result == {"auto_commit": True}

    def test_get_step_config_not_found(self) -> None:
        """Get step config returns empty dict for unknown step."""
        state = WizardState()
        result = state.get_step_config("unknown")
        assert result == {}


class TestSerialization:
    """Tests for WizardState serialization."""

    def test_model_dump(self) -> None:
        """WizardState can be serialized to dict."""
        state = WizardState(
            current_step="git",
            completed_steps=["basics"],
            collected_config={"basics": {"language": "python"}},
        )

        data = state.model_dump()

        assert data["current_step"] == "git"
        assert data["completed_steps"] == ["basics"]
        assert data["collected_config"] == {"basics": {"language": "python"}}

    def test_model_json_round_trip(self) -> None:
        """WizardState can be serialized to JSON and back."""
        state = WizardState(
            current_step="ports",
            completed_steps=["basics", "git"],
            collected_config={"basics": {"language": "python"}},
        )

        json_str = state.model_dump_json()
        restored = WizardState.model_validate_json(json_str)

        assert restored.current_step == state.current_step
        assert restored.completed_steps == state.completed_steps
        assert restored.collected_config == state.collected_config
