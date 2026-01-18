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
    REVIEW_FOCUS_AREAS,
    TRIAGE_MODES,
    PhasesStepHandler,
    _configure_phase,
    _configure_validate_phase,
    _parse_int,
    _prompt_input_files,
    _prompt_phase_selection,
    _prompt_review_focus,
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

    def test_review_focus_areas(self) -> None:
        """Test review focus areas list."""
        assert REVIEW_FOCUS_AREAS == ["security", "error_handling", "edge_cases"]


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
    """Tests for phase selection flow."""

    def test_select_no_phases(self) -> None:
        """Test selecting no phases returns empty list."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            # All phases declined
            mock_confirm.side_effect = [False, False, False, False]
            selected = _prompt_phase_selection(console)

        assert selected == []

    def test_select_all_phases(self) -> None:
        """Test selecting all phases."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [True, True, True, True]
            selected = _prompt_phase_selection(console)

        assert selected == AVAILABLE_PHASES

    def test_select_some_phases(self) -> None:
        """Test selecting some phases."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            # Select plan and validate only
            mock_confirm.side_effect = [True, False, True, False]
            selected = _prompt_phase_selection(console)

        assert selected == ["plan", "validate"]

    def test_no_phases_selected_returns_empty_result(self) -> None:
        """Test that selecting no phases after opting to customize returns empty config."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            # First: yes to customize, then no to all phases
            mock_confirm.side_effect = [True, False, False, False, False]
            result = run_phases_step(state, console)

        assert result["customized"] is False
        assert result["phases"] == {}


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
            # timeout (default), pre_hook (none), post_hook (none)
            mock_prompt.side_effect = ["300", "", ""]

            config = _configure_phase("plan", console)

        assert config["enabled"] is True
        assert config["timeout"] == 300
        assert config["pre_hook"] is None
        assert config["post_hook"] is None
        assert config["input_files"] is None

    def test_configure_phase_custom_values(self) -> None:
        """Test phase configuration with custom values."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            # enabled=False, no input files
            mock_confirm.side_effect = [False, False]
            # timeout=120, pre_hook, post_hook
            mock_prompt.side_effect = ["120", "./pre.sh", "./post.sh"]

            config = _configure_phase("build", console)

        assert config["enabled"] is False
        assert config["timeout"] == 120
        assert config["pre_hook"] == "./pre.sh"
        assert config["post_hook"] == "./post.sh"

    def test_configure_phase_uses_phase_default_timeout(self) -> None:
        """Test that phase configuration uses phase-specific default timeout."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [True, False]
            # User just hits enter for timeout (uses default)
            mock_prompt.side_effect = ["600", "", ""]

            config = _configure_phase("build", console)

        # Build default is 600
        assert config["timeout"] == 600


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
            # Validate special: code_review=True, tests=True, focus=all
            mock_confirm.side_effect = [
                True,  # enabled
                False,  # input files
                True,  # code_review
                True,  # tests
                True,  # security focus
                True,  # error_handling focus
                True,  # edge_cases focus
            ]
            mock_prompt.side_effect = [
                "900",  # timeout
                "",  # pre_hook
                "",  # post_hook
                "300",  # test_timeout
                "5",  # max_iterations
                "auto",  # triage_mode
            ]

            config = _configure_phase("validate", console)

        # Base options
        assert config["enabled"] is True
        assert config["timeout"] == 900

        # Validate-specific options
        assert config["code_review"] is True
        assert config["tests"] is True
        assert config["test_timeout"] == 300
        assert config["max_iterations"] == 5
        assert config["triage_mode"] == "auto"
        assert config["review_focus"] == ["security", "error_handling", "edge_cases"]

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
                True,  # security focus only
                False,  # error_handling
                False,  # edge_cases
            ]
            mock_prompt.side_effect = [
                "1800",  # timeout 30 min
                "",  # pre_hook
                "",  # post_hook
                "600",  # test_timeout
                "3",  # max_iterations
                "manual",  # triage_mode
            ]

            config = _configure_phase("validate", console)

        assert config["code_review"] is False
        assert config["tests"] is True
        assert config["test_timeout"] == 600
        assert config["max_iterations"] == 3
        assert config["triage_mode"] == "manual"
        assert config["review_focus"] == ["security"]

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
                False,  # no security focus
                True,  # error_handling
                False,  # no edge_cases
            ]
            mock_prompt.side_effect = [
                "180",  # test_timeout
                "10",  # max_iterations
                "hybrid",  # triage_mode
            ]

            config = _configure_validate_phase(console)

        assert config["code_review"] is True
        assert config["tests"] is False
        assert config["test_timeout"] == 180
        assert config["max_iterations"] == 10
        assert config["triage_mode"] == "hybrid"
        assert config["review_focus"] == ["error_handling"]


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


class TestReviewFocus:
    """Tests for review focus selection."""

    def test_select_all_focus_areas(self) -> None:
        """Test selecting all focus areas."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [True, True, True]
            result = _prompt_review_focus(console)

        assert result == ["security", "error_handling", "edge_cases"]

    def test_select_no_focus_areas(self) -> None:
        """Test selecting no focus areas."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [False, False, False]
            result = _prompt_review_focus(console)

        assert result == []

    def test_select_some_focus_areas(self) -> None:
        """Test selecting some focus areas."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = [True, False, True]
            result = _prompt_review_focus(console)

        assert result == ["security", "edge_cases"]


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
                True,  # plan
                False,  # build
                False,  # validate
                False,  # document
                True,  # enabled
                False,  # input files
            ]
            mock_prompt.side_effect = [
                "300",  # timeout
                "",  # pre_hook
                "",  # post_hook
            ]

            result = run_phases_step(state, console)

        assert result["customized"] is True
        assert "plan" in result["phases"]
        assert result["phases"]["plan"]["enabled"] is True
        assert result["phases"]["plan"]["timeout"] == 300

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
                False,  # plan
                False,  # build
                True,  # validate
                False,  # document
                True,  # enabled
                False,  # input files
                True,  # code_review
                True,  # tests
                True,  # security
                True,  # error_handling
                True,  # edge_cases
            ]
            mock_prompt.side_effect = [
                "900",  # timeout
                "",  # pre_hook
                "",  # post_hook
                "300",  # test_timeout
                "5",  # max_iterations
                "auto",  # triage_mode
            ]

            result = run_phases_step(state, console)

        assert result["customized"] is True
        assert "validate" in result["phases"]
        validate_config = result["phases"]["validate"]
        assert validate_config["code_review"] is True
        assert validate_config["tests"] is True
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
