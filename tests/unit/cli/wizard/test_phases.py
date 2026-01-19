"""Tests for wizard phases configuration step.

Tests the phase selection, configuration, and validate phase special options
for the phases configuration step.
"""

from __future__ import annotations

from unittest.mock import patch

from rich.console import Console

from adw.cli.wizard.phases import (
    AVAILABLE_PHASES,
    DEFAULT_TIMEOUTS,
    TRIAGE_MODES,
    PhasesStepHandler,
    _configure_phase,
    _configure_validate_phase,
    _parse_int,
    _parse_phase_selection,
    _prompt_input_files,
    _prompt_phase_selection,
    run_phases_step,
)
from adw.models.wizard import WizardState


class TestConstants:
    """Tests for module constants."""

    def test_available_phases(self) -> None:
        """Test available phases list."""
        assert AVAILABLE_PHASES == ["plan", "build", "validate", "document"]

    def test_default_timeouts_defined_for_all_phases(self) -> None:
        """Test that default timeouts exist for all phases."""
        for phase in AVAILABLE_PHASES:
            assert phase in DEFAULT_TIMEOUTS

    def test_default_timeout_values(self) -> None:
        """Test specific default timeout values."""
        assert DEFAULT_TIMEOUTS["plan"] == 300
        assert DEFAULT_TIMEOUTS["build"] == 600
        assert DEFAULT_TIMEOUTS["validate"] == 900
        assert DEFAULT_TIMEOUTS["document"] == 300

    def test_triage_modes(self) -> None:
        """Test triage modes list."""
        assert TRIAGE_MODES == ["auto", "manual", "hybrid"]


class TestNoCustomization:
    """Tests for when user declines customization."""

    def test_no_customize_returns_empty_config(self) -> None:
        """Test that declining customization returns empty config."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.phases.Confirm.ask", return_value=False):
            result = run_phases_step(state, console)

        assert result["customized"] is False
        assert result["phases"] == {}


class TestPhaseSelection:
    """Tests for phase selection flow with comma-separated input."""

    def test_select_no_phases_empty_input(self) -> None:
        """Test empty input returns empty list."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask", return_value=""):
            selected = _prompt_phase_selection(console)

        assert selected == []

    def test_select_all_phases_keyword(self) -> None:
        """Test 'all' keyword selects all phases."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask", return_value="all"):
            selected = _prompt_phase_selection(console)

        assert selected == AVAILABLE_PHASES

    def test_select_phases_by_number(self) -> None:
        """Test selecting phases by number (1,3)."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask", return_value="1,3"):
            selected = _prompt_phase_selection(console)

        assert selected == ["plan", "validate"]

    def test_select_phases_by_name(self) -> None:
        """Test selecting phases by name."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask", return_value="plan, validate"):
            selected = _prompt_phase_selection(console)

        assert selected == ["plan", "validate"]

    def test_no_phases_selected_returns_empty_result(self) -> None:
        """Test that empty selection after opting to customize returns empty config."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.phases.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask", return_value=""),
        ):
            result = run_phases_step(state, console)

        assert result["customized"] is False
        assert result["phases"] == {}


class TestParsePhaseSelection:
    """Tests for _parse_phase_selection helper function."""

    def test_empty_input(self) -> None:
        """Test empty input returns empty list."""
        assert _parse_phase_selection("") == []
        assert _parse_phase_selection("   ") == []

    def test_all_keyword(self) -> None:
        """Test 'all' keyword returns all phases."""
        assert _parse_phase_selection("all") == AVAILABLE_PHASES
        assert _parse_phase_selection("ALL") == AVAILABLE_PHASES
        assert _parse_phase_selection("  all  ") == AVAILABLE_PHASES

    def test_numeric_selection(self) -> None:
        """Test selecting by number."""
        assert _parse_phase_selection("1") == ["plan"]
        assert _parse_phase_selection("1,3") == ["plan", "validate"]
        assert _parse_phase_selection("1, 2, 3") == ["plan", "build", "validate"]
        assert _parse_phase_selection("4") == ["document"]

    def test_name_selection(self) -> None:
        """Test selecting by phase name."""
        assert _parse_phase_selection("plan") == ["plan"]
        assert _parse_phase_selection("plan, validate") == ["plan", "validate"]
        assert _parse_phase_selection("PLAN") == ["plan"]

    def test_mixed_selection(self) -> None:
        """Test mixed number and name selection."""
        assert _parse_phase_selection("1, validate") == ["plan", "validate"]
        assert _parse_phase_selection("plan, 4") == ["plan", "document"]

    def test_invalid_entries_ignored(self) -> None:
        """Test that invalid entries are silently ignored."""
        assert _parse_phase_selection("1, invalid, 3") == ["plan", "validate"]
        assert _parse_phase_selection("99") == []
        assert _parse_phase_selection("0") == []

    def test_duplicates_removed(self) -> None:
        """Test that duplicate selections are removed."""
        assert _parse_phase_selection("1, 1, plan") == ["plan"]
        assert _parse_phase_selection("plan, plan") == ["plan"]


class TestBasePhaseConfiguration:
    """Tests for base phase configuration."""

    def test_configure_phase_defaults(self) -> None:
        """Test phase configuration with all defaults."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            # enabled=True, no input files
            mock_confirm.side_effect = [True, False]
            # timeout (default)
            mock_prompt.side_effect = ["300"]

            config = _configure_phase("plan", console)

        assert config["enabled"] is True
        assert config["timeout_seconds"] == 300
        assert config["input_files"] is None

    def test_configure_phase_custom_timeout(self) -> None:
        """Test phase configuration with custom timeout."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            # enabled=False, no input files
            mock_confirm.side_effect = [False, False]
            # timeout=120
            mock_prompt.side_effect = ["120"]

            config = _configure_phase("build", console)

        assert config["enabled"] is False
        assert config["timeout_seconds"] == 120

    def test_configure_phase_uses_phase_default_timeout(self) -> None:
        """Test that phase configuration uses phase-specific default timeout."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False]
            # User just hits enter for timeout (uses default)
            mock_prompt.side_effect = ["600"]

            config = _configure_phase("build", console)

        # Build default is 600
        assert config["timeout_seconds"] == 600


class TestValidatePhaseSpecialOptions:
    """Tests for validate phase special options."""

    def test_validate_phase_includes_special_options(self) -> None:
        """Test that validate phase config includes special options."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            # Base config: enabled=True, no input files
            # Validate special: code_review=True, tests=True
            mock_confirm.side_effect = [
                True,  # enabled
                False,  # input files
                True,  # code_review
                True,  # tests
            ]
            mock_prompt.side_effect = [
                "900",  # timeout
                "300",  # test_timeout
                "5",  # max_iterations
                "auto",  # triage_mode
            ]

            config = _configure_phase("validate", console)

        # Base options
        assert config["enabled"] is True
        assert config["timeout_seconds"] == 900

        # Validate-specific options
        assert config["enable_review"] is True
        assert config["enable_tests"] is True
        assert config["test_timeout_seconds"] == 300
        assert config["max_iterations"] == 5
        assert config["triage_mode"] == "auto"

    def test_validate_phase_custom_special_options(self) -> None:
        """Test validate phase with custom special options."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # enabled
                False,  # input files
                False,  # code_review disabled
                True,  # tests
            ]
            mock_prompt.side_effect = [
                "1800",  # timeout 30 min
                "600",  # test_timeout
                "3",  # max_iterations
                "manual",  # triage_mode
            ]

            config = _configure_phase("validate", console)

        assert config["enable_review"] is False
        assert config["enable_tests"] is True
        assert config["test_timeout_seconds"] == 600
        assert config["max_iterations"] == 3
        assert config["triage_mode"] == "manual"

    def test_configure_validate_phase_directly(self) -> None:
        """Test _configure_validate_phase function directly."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # code_review
                False,  # tests disabled
            ]
            mock_prompt.side_effect = [
                "180",  # test_timeout
                "10",  # max_iterations
                "hybrid",  # triage_mode
            ]

            config = _configure_validate_phase(console)

        assert config["enable_review"] is True
        assert config["enable_tests"] is False
        assert config["test_timeout_seconds"] == 180
        assert config["max_iterations"] == 10
        assert config["triage_mode"] == "hybrid"


class TestInputFileLoop:
    """Tests for input file key=path loop."""

    def test_no_input_files(self) -> None:
        """Test declining to add input files."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask", return_value=False):
            result = _prompt_input_files(console)

        assert result == {}

    def test_single_input_file(self) -> None:
        """Test adding a single input file."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["prd=docs/prd.md", ""]
            result = _prompt_input_files(console)

        assert result == {"prd": "docs/prd.md"}

    def test_multiple_input_files(self) -> None:
        """Test adding multiple input files."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "prd=docs/prd.md",
                "arch=docs/architecture.md",
                "spec=docs/spec.yaml",
                "",  # empty to finish
            ]
            result = _prompt_input_files(console)

        assert result == {
            "prd": "docs/prd.md",
            "arch": "docs/architecture.md",
            "spec": "docs/spec.yaml",
        }

    def test_invalid_format_reprompts(self) -> None:
        """Test that invalid format shows error and reprompts."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "invalid_no_equals",  # invalid
                "prd=docs/prd.md",  # valid
                "",  # finish
            ]
            result = _prompt_input_files(console)

        assert result == {"prd": "docs/prd.md"}
        # Verify it was called 3 times (invalid, valid, empty)
        assert mock_prompt.call_count == 3

    def test_empty_key_or_path_reprompts(self) -> None:
        """Test that empty key or path shows error and reprompts."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "=docs/prd.md",  # empty key
                "prd=",  # empty path
                "prd=docs/prd.md",  # valid
                "",
            ]
            result = _prompt_input_files(console)

        assert result == {"prd": "docs/prd.md"}


class TestParseInt:
    """Tests for _parse_int helper function."""

    def test_parse_valid_int(self) -> None:
        """Test parsing valid integer string."""
        assert _parse_int("42", 0) == 42
        assert _parse_int("300", 0) == 300
        assert _parse_int("0", 100) == 0

    def test_parse_invalid_returns_default(self) -> None:
        """Test that invalid input returns default."""
        assert _parse_int("abc", 100) == 100
        assert _parse_int("", 50) == 50
        assert _parse_int("12.5", 10) == 10


class TestPhasesStepHandler:
    """Tests for PhasesStepHandler class."""

    def test_handler_delegates_to_run_phases_step(self) -> None:
        """Test that handler properly delegates to run_phases_step."""
        handler = PhasesStepHandler()
        state = WizardState()
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask", return_value=False):
            result = handler.execute(state, console)

        assert result["customized"] is False
        assert result["phases"] == {}


class TestFullFlow:
    """Tests for full phases configuration flow."""

    def test_full_flow_customize_single_phase(self) -> None:
        """Test full flow customizing a single non-validate phase."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # customize phases
                True,  # enabled
                False,  # input files
            ]
            mock_prompt.side_effect = [
                "1",  # select plan phase
                "300",  # timeout
            ]

            result = run_phases_step(state, console)

        assert result["customized"] is True
        assert "plan" in result["phases"]
        assert result["phases"]["plan"]["enabled"] is True
        assert result["phases"]["plan"]["timeout_seconds"] == 300

    def test_full_flow_customize_validate_phase(self) -> None:
        """Test full flow customizing only the validate phase."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # customize phases
                True,  # enabled
                False,  # input files
                True,  # code_review
                True,  # tests
            ]
            mock_prompt.side_effect = [
                "3",  # select validate phase
                "900",  # timeout
                "300",  # test_timeout
                "5",  # max_iterations
                "auto",  # triage_mode
            ]

            result = run_phases_step(state, console)

        assert result["customized"] is True
        assert "validate" in result["phases"]
        validate_config = result["phases"]["validate"]
        assert validate_config["enable_review"] is True
        assert validate_config["enable_tests"] is True
        assert validate_config["triage_mode"] == "auto"


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_config_can_be_stored_in_state(self) -> None:
        """Test that phases config can be stored via flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.phases.Confirm.ask", return_value=False):
            config = run_phases_step(state, console)

        # Simulate what flow controller does
        state.update_config("phases", config)
        state.mark_completed("phases")

        # Verify storage
        stored = state.get_step_config("phases")
        assert stored["customized"] is False
        assert "phases" in state.completed_steps


class TestPackageExports:
    """Tests for package exports."""

    def test_phases_step_handler_exported(self) -> None:
        """Test that PhasesStepHandler is exported from package."""
        from adw.cli.wizard import PhasesStepHandler

        assert PhasesStepHandler is not None

    def test_run_phases_step_exported(self) -> None:
        """Test that run_phases_step is exported from package."""
        from adw.cli.wizard import run_phases_step

        assert run_phases_step is not None
