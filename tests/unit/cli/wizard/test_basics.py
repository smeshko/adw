"""Tests for wizard basics configuration step.

Tests the language detection, test command detection, and interactive
prompt flow for the basics configuration step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from adw.cli.wizard.basics import (
    LANGUAGE_MARKERS,
    SUPPORTED_LANGUAGES,
    SUPPORTED_PLATFORMS,
    BasicsStepHandler,
    detect_language,
    detect_test_command,
    run_basics_step,
)
from adw.models.wizard import WizardState


class TestLanguageDetection:
    """Tests for detect_language function."""

    @pytest.mark.parametrize(
        "marker_file,expected_language",
        [
            ("pyproject.toml", "python"),
            ("setup.py", "python"),
            ("setup.cfg", "python"),
            ("package.json", "javascript"),
            ("go.mod", "go"),
            ("Cargo.toml", "rust"),
            ("pom.xml", "java"),
            ("build.gradle", "java"),
            ("build.gradle.kts", "java"),
            ("Gemfile", "ruby"),
            ("composer.json", "php"),
        ],
    )
    def test_detect_language_from_marker(
        self, marker_file: str, expected_language: str, tmp_path: Path
    ) -> None:
        """Test language detection from various marker files."""
        (tmp_path / marker_file).touch()
        assert detect_language(tmp_path) == expected_language

    def test_detect_language_unknown_when_no_markers(self, tmp_path: Path) -> None:
        """Test returns 'unknown' when no marker files exist."""
        assert detect_language(tmp_path) == "unknown"

    def test_detect_language_priority_first_match(self, tmp_path: Path) -> None:
        """Test that first matching language wins when multiple markers exist.

        Python markers come before JavaScript in LANGUAGE_MARKERS dict,
        and Python dicts maintain insertion order (3.7+), so Python wins.
        """
        # Create multiple markers
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()

        # Python should be detected first (order in LANGUAGE_MARKERS dict)
        result = detect_language(tmp_path)
        assert result == "python"  # First language in LANGUAGE_MARKERS wins


class TestTestCommandDetection:
    """Tests for detect_test_command function."""

    @pytest.mark.parametrize(
        "language,expected_command",
        [
            ("python", "pytest"),
            ("javascript", "npm test"),
            ("go", "go test ./..."),
            ("rust", "cargo test"),
            ("java", "./gradlew test"),
            ("ruby", "bundle exec rspec"),
            ("php", "./vendor/bin/phpunit"),
        ],
    )
    def test_detect_test_command_for_known_language(
        self, language: str, expected_command: str
    ) -> None:
        """Test test command detection for all supported languages."""
        assert detect_test_command(language) == expected_command

    def test_detect_test_command_unknown_returns_empty(self) -> None:
        """Test returns empty string for unknown language."""
        assert detect_test_command("unknown") == ""

    def test_detect_test_command_custom_language_returns_empty(self) -> None:
        """Test returns empty string for custom/unsupported languages."""
        assert detect_test_command("kotlin") == ""
        assert detect_test_command("scala") == ""
        assert detect_test_command("my-custom-lang") == ""


class TestPromptLanguage:
    """Tests for language prompting flow."""

    def test_language_confirmed_uses_detected(self) -> None:
        """Test that confirmed language detection uses the detected value."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True) as mock_confirm,
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "pytest", ""]  # platform, test, build
            result = run_basics_step(state, console)

            # Confirm was called for language confirmation
            mock_confirm.assert_called_once()
            assert result["language"] == "python"

    def test_language_not_confirmed_shows_selection(self) -> None:
        """Test that rejecting detection shows language selection."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=False),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # First call: language selection, then platform, test_cmd, build_cmd
            mock_prompt.side_effect = ["javascript", "api", "npm test", "npm build"]
            result = run_basics_step(state, console)

            assert result["language"] == "javascript"

    def test_other_language_prompts_for_custom_name(self) -> None:
        """Test that selecting 'other' prompts for custom language name."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="unknown"),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # First prompt: language selection returns "other"
            # Second prompt: custom language name
            # Third: platform, Fourth: test, Fifth: build
            mock_prompt.side_effect = ["other", "Kotlin", "cli", "", ""]
            result = run_basics_step(state, console)

            assert result["language"] == "kotlin"  # Normalized to lowercase

    def test_other_language_rejects_empty_string(self) -> None:
        """Test that selecting 'other' and entering empty string re-prompts."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="unknown"),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # Simulate: select "other", enter "" (rejected), enter "  " (rejected), enter "swift"
            mock_prompt.side_effect = ["other", "", "  ", "swift", "cli", "", ""]
            result = run_basics_step(state, console)

            assert result["language"] == "swift"
            # Verify prompt was called multiple times for language entry
            assert mock_prompt.call_count >= 4


class TestPromptPlatform:
    """Tests for platform prompting flow."""

    def test_platform_selection_returns_choice(self) -> None:
        """Test basic platform selection."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["web", "pytest", ""]  # platform, test, build
            result = run_basics_step(state, console)

            assert result["platform"] == "web"

    def test_other_platform_prompts_for_custom_name(self) -> None:
        """Test that selecting 'other' prompts for custom platform name."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # platform "other", custom name, test, build
            mock_prompt.side_effect = ["other", "Mobile App", "pytest", ""]
            result = run_basics_step(state, console)

            assert result["platform"] == "mobile app"  # Normalized to lowercase

    def test_other_platform_rejects_empty_string(self) -> None:
        """Test that selecting 'other' platform and entering empty string re-prompts."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # platform "other", enter "" (rejected), enter "embedded"
            mock_prompt.side_effect = ["other", "", "embedded", "pytest", ""]
            result = run_basics_step(state, console)

            assert result["platform"] == "embedded"


class TestPromptCommands:
    """Tests for test and build command prompts."""

    def test_test_command_uses_default_from_detection(self) -> None:
        """Test that detected test command is used as default."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # User accepts all defaults
            mock_prompt.side_effect = ["cli", "pytest", ""]
            result = run_basics_step(state, console)

            assert result["test_command"] == "pytest"

    def test_test_command_custom_override(self) -> None:
        """Test that user can override detected test command."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "uv run pytest -v", ""]
            result = run_basics_step(state, console)

            assert result["test_command"] == "uv run pytest -v"

    def test_build_command_optional_can_be_skipped(self) -> None:
        """Test that build command can be skipped (empty)."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "pytest", ""]  # Empty build
            result = run_basics_step(state, console)

            assert result["build_command"] == ""

    def test_build_command_custom_value(self) -> None:
        """Test that user can specify a build command."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="javascript"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["web", "npm test", "npm run build"]
            result = run_basics_step(state, console)

            assert result["build_command"] == "npm run build"


class TestBasicsStepHandler:
    """Tests for BasicsStepHandler class."""

    def test_handler_uses_project_root(self, tmp_path: Path) -> None:
        """Test handler uses provided project root."""
        (tmp_path / "go.mod").touch()
        handler = BasicsStepHandler(project_root=tmp_path)
        state = WizardState()
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "go test ./...", ""]
            result = handler.execute(state, console)

            assert result["language"] == "go"

    def test_handler_defaults_to_cwd(self) -> None:
        """Test handler defaults to current working directory."""
        handler = BasicsStepHandler()
        assert handler.project_root == Path.cwd()


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_full_flow_returns_complete_config(self) -> None:
        """Test that full flow returns all expected configuration keys."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="rust"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["api", "cargo test", "cargo build --release"]
            result = run_basics_step(state, console)

            # Verify all keys present
            assert "language" in result
            assert "platform" in result
            assert "test_command" in result
            assert "build_command" in result

            # Verify values
            assert result["language"] == "rust"
            assert result["platform"] == "api"
            assert result["test_command"] == "cargo test"
            assert result["build_command"] == "cargo build --release"

    def test_config_stored_via_flow_controller_pattern(self) -> None:
        """Test that config can be stored using flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.basics.detect_language", return_value="python"),
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "pytest", ""]
            config = run_basics_step(state, console)

            # Simulate what flow controller does
            state.update_config("basics", config)
            state.mark_completed("basics")

            # Verify storage
            stored = state.get_step_config("basics")
            assert stored["language"] == "python"
            assert "basics" in state.completed_steps


class TestConstants:
    """Tests for module constants."""

    def test_supported_languages_includes_other(self) -> None:
        """Test that 'other' is in supported languages."""
        assert "other" in SUPPORTED_LANGUAGES

    def test_supported_platforms_includes_other(self) -> None:
        """Test that 'other' is in supported platforms."""
        assert "other" in SUPPORTED_PLATFORMS

    def test_language_markers_covers_major_languages(self) -> None:
        """Test that all major languages have markers defined."""
        expected = {"python", "javascript", "go", "rust", "java", "ruby", "php"}
        actual = set(LANGUAGE_MARKERS.keys())
        assert expected == actual
