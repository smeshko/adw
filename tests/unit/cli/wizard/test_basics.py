"""Tests for wizard basics configuration step.

Tests the language detection, test command detection, and interactive
prompt flow for the basics configuration step.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console
from rich.text import Text

from adw.cli.wizard.basics import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_PLATFORMS,
    run_basics_step,
)
from adw.config.detector import ProjectTypeDetector


class TestDetection:
    """The wizard detects what ProjectTypeDetector detects."""

    @pytest.mark.parametrize(
        ("marker", "language"),
        [
            ("requirements.txt", "python"),
            ("setup.cfg", "python"),
            ("package.json", "javascript"),
            ("build.gradle", "java"),
            ("build.gradle.kts", "java"),
            ("composer.json", "php"),
        ],
    )
    def test_detected_defaults_match_project_type_detector(
        self, marker: str, language: str
    ) -> None:
        """Accepting every default yields the detector's language and test command."""
        (Path.cwd() / marker).touch()

        with (
            patch(
                "adw.cli.wizard.basics.Confirm.ask", return_value=True
            ) as mock_confirm,
            patch(
                "adw.cli.wizard.basics.Prompt.ask",
                side_effect=lambda *_, **kw: kw["default"],
            ),
        ):
            result = run_basics_step(Console(force_terminal=True), Path.cwd())

        question = Text.from_markup(mock_confirm.call_args.args[0]).plain
        assert mock_confirm.call_count == 1
        assert f"Language detected: {language}" in question
        expected = ProjectTypeDetector().get_defaults(language)
        assert result["language"] == expected["language"]
        assert result["test_command"] == expected["test_command"]

    def test_chosen_language_sets_test_command_default(self) -> None:
        """Rejecting the detection offers the chosen language's test command."""
        (Path.cwd() / "package.json").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=False),
            patch(
                "adw.cli.wizard.basics.Prompt.ask",
                side_effect=lambda q, **kw: "go" if q == "Language" else kw["default"],
            ),
        ):
            result = run_basics_step(Console(force_terminal=True), Path.cwd())

        assert result["language"] == "go"
        assert result["test_command"] == "go test ./..."


class TestPromptLanguage:
    """Tests for language prompting flow."""

    def test_language_confirmed_uses_detected(self) -> None:
        """Test that confirmed language detection uses the detected value."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch(
                "adw.cli.wizard.basics.Confirm.ask", return_value=True
            ) as mock_confirm,
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "pytest", ""]  # platform, test, build
            result = run_basics_step(console, Path.cwd())

            # Confirm was called for language confirmation
            mock_confirm.assert_called_once()
            assert result["language"] == "python"
            assert result["project_name"] == Path.cwd().name

    def test_language_not_confirmed_shows_selection(self) -> None:
        """Test that rejecting detection shows language selection."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=False),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # First call: language selection, then platform, test_cmd, build_cmd
            mock_prompt.side_effect = ["javascript", "api", "npm test", "npm build"]
            result = run_basics_step(console, Path.cwd())

            assert result["language"] == "javascript"

    def test_custom_language_direct_entry(self) -> None:
        """Test that typing a custom language directly works (no 'other' needed)."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # Direct entry: "kotlin" (custom language), "cli" (platform), test, build
            mock_prompt.side_effect = ["Kotlin", "cli", "", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["language"] == "kotlin"  # Normalized to lowercase

    def test_language_rejects_empty_string(self) -> None:
        """Test that empty language input re-prompts."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # Simulate: enter "" (rejected), enter "swift"
            mock_prompt.side_effect = ["", "swift", "cli", "", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["language"] == "swift"

    def test_language_selection_by_number(self) -> None:
        """Test that selecting a language by number works."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # Select "1" (python), platform, test, build
            mock_prompt.side_effect = ["1", "cli", "", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["language"] == "python"


class TestPromptPlatform:
    """Tests for platform prompting flow."""

    def test_platform_selection_returns_choice(self) -> None:
        """Test basic platform selection."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["web", "pytest", ""]  # platform, test, build
            result = run_basics_step(console, Path.cwd())

            assert result["platform"] == "web"

    def test_custom_platform_direct_entry(self) -> None:
        """Test that typing a custom platform directly works (no 'other' needed)."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # Direct entry: "Mobile App" (custom platform), test, build
            mock_prompt.side_effect = ["Mobile App", "pytest", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["platform"] == "mobile app"  # Normalized to lowercase

    def test_platform_selection_by_number(self) -> None:
        """Test that selecting a platform by number works."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # Select "2" for web platform, test, build
            mock_prompt.side_effect = ["2", "pytest", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["platform"] == "web"


class TestPromptCommands:
    """Tests for test and build command prompts."""

    def test_test_command_uses_default_from_detection(self) -> None:
        """Test that detected test command is used as default."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            # User accepts all defaults
            mock_prompt.side_effect = ["cli", "pytest", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["test_command"] == "pytest"

    def test_test_command_custom_override(self) -> None:
        """Test that user can override detected test command."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "uv run pytest -v", ""]
            result = run_basics_step(console, Path.cwd())

            assert result["test_command"] == "uv run pytest -v"

    def test_build_command_optional_can_be_skipped(self) -> None:
        """Test that build command can be skipped (empty)."""
        console = Console(force_terminal=True)

        (Path.cwd() / "pyproject.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["cli", "pytest", ""]  # Empty build
            result = run_basics_step(console, Path.cwd())

            assert result["build_command"] == ""

    def test_build_command_custom_value(self) -> None:
        """Test that user can specify a build command."""
        console = Console(force_terminal=True)

        (Path.cwd() / "package.json").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["web", "npm test", "npm run build"]
            result = run_basics_step(console, Path.cwd())

            assert result["build_command"] == "npm run build"


class TestFullFlow:
    """Tests for the whole basics step."""

    def test_full_flow_returns_complete_config(self) -> None:
        """Test that full flow returns all expected configuration keys."""
        console = Console(force_terminal=True)

        (Path.cwd() / "Cargo.toml").touch()

        with (
            patch("adw.cli.wizard.basics.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.basics.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["api", "cargo test", "cargo build --release"]
            result = run_basics_step(console, Path.cwd())

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


class TestConstants:
    """Tests for module constants."""

    def test_supported_languages_includes_other(self) -> None:
        """Test that 'other' is in supported languages."""
        assert "other" in SUPPORTED_LANGUAGES

    def test_supported_platforms_includes_other(self) -> None:
        """Test that 'other' is in supported platforms."""
        assert "other" in SUPPORTED_PLATFORMS
