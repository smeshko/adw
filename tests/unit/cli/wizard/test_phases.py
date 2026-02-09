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
    _configure_document_phase,
    _configure_phase,
    _configure_validate_phase,
    _parse_int,
    _parse_phase_selection,
    _prompt_doc_mappings,
    _prompt_input_files,
    _prompt_phase_selection,
    run_phases_step,
)
from adw.models.wizard import WizardState


class TestConstants:
    """Tests for module constants."""

    def test_available_phases(self) -> None:
        """Test available phases list includes ship."""
        assert AVAILABLE_PHASES == ["plan", "build", "validate", "document", "ship"]

    def test_default_timeouts_defined_for_all_phases(self) -> None:
        """Test that default timeouts exist for all phases."""
        for phase in AVAILABLE_PHASES:
            assert phase in DEFAULT_TIMEOUTS

    def test_default_timeout_values(self) -> None:
        """Test specific default timeout values (updated per AC8)."""
        assert DEFAULT_TIMEOUTS["plan"] == 900  # 15 minutes
        assert DEFAULT_TIMEOUTS["build"] == 1800  # 30 minutes
        assert DEFAULT_TIMEOUTS["validate"] == 900  # 15 minutes
        assert DEFAULT_TIMEOUTS["document"] == 900  # 15 minutes
        assert DEFAULT_TIMEOUTS["ship"] == 1200  # 20 minutes

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

    def test_invalid_only_input_reprompts(self) -> None:
        """Test that entering only invalid entries reprompts until valid."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt:
            # First invalid, then valid
            mock_prompt.side_effect = ["invalid, foo", "1,3"]
            selected = _prompt_phase_selection(console)

        assert selected == ["plan", "validate"]
        assert mock_prompt.call_count == 2

    def test_mixed_valid_invalid_shows_feedback(self) -> None:
        """Test that mixed input returns valid phases (invalid shown as feedback)."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask", return_value="1, invalid, 3"):
            selected = _prompt_phase_selection(console)

        assert selected == ["plan", "validate"]


class TestParsePhaseSelection:
    """Tests for _parse_phase_selection helper function."""

    def test_empty_input(self) -> None:
        """Test empty input returns empty lists."""
        assert _parse_phase_selection("") == ([], [])
        assert _parse_phase_selection("   ") == ([], [])

    def test_all_keyword(self) -> None:
        """Test 'all' keyword returns all phases."""
        assert _parse_phase_selection("all") == (AVAILABLE_PHASES, [])
        assert _parse_phase_selection("ALL") == (AVAILABLE_PHASES, [])
        assert _parse_phase_selection("  all  ") == (AVAILABLE_PHASES, [])

    def test_numeric_selection(self) -> None:
        """Test selecting by number."""
        assert _parse_phase_selection("1") == (["plan"], [])
        assert _parse_phase_selection("1,3") == (["plan", "validate"], [])
        assert _parse_phase_selection("1, 2, 3") == (["plan", "build", "validate"], [])
        assert _parse_phase_selection("4") == (["document"], [])

    def test_name_selection(self) -> None:
        """Test selecting by phase name."""
        assert _parse_phase_selection("plan") == (["plan"], [])
        assert _parse_phase_selection("plan, validate") == (["plan", "validate"], [])
        assert _parse_phase_selection("PLAN") == (["plan"], [])

    def test_mixed_selection(self) -> None:
        """Test mixed number and name selection."""
        assert _parse_phase_selection("1, validate") == (["plan", "validate"], [])
        assert _parse_phase_selection("plan, 4") == (["plan", "document"], [])

    def test_invalid_entries_returned(self) -> None:
        """Test that invalid entries are returned separately."""
        selected, invalid = _parse_phase_selection("1, invalid, 3")
        assert selected == ["plan", "validate"]
        assert invalid == ["invalid"]

        selected, invalid = _parse_phase_selection("99")
        assert selected == []
        assert invalid == ["99"]

        selected, invalid = _parse_phase_selection("0")
        assert selected == []
        assert invalid == ["0"]

    def test_duplicates_removed(self) -> None:
        """Test that duplicate selections are removed."""
        assert _parse_phase_selection("1, 1, plan") == (["plan"], [])
        assert _parse_phase_selection("plan, plan") == (["plan"], [])

    def test_multiple_invalid_entries(self) -> None:
        """Test multiple invalid entries are all returned."""
        selected, invalid = _parse_phase_selection("foo, bar, baz")
        assert selected == []
        assert invalid == ["foo", "bar", "baz"]

    def test_mixed_valid_and_invalid(self) -> None:
        """Test mix of valid and invalid entries."""
        selected, invalid = _parse_phase_selection("1, foo, validate, bar")
        assert selected == ["plan", "validate"]
        assert invalid == ["foo", "bar"]


class TestBasePhaseConfiguration:
    """Tests for base phase configuration."""

    def test_configure_phase_defaults(self) -> None:
        """Test phase configuration with all defaults."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            # enabled=True
            mock_confirm.return_value = True
            # timeout, model override, temperature override
            mock_prompt.side_effect = ["300", "", ""]

            config = _configure_phase("plan", console)

        assert config["enabled"] is True
        assert config["timeout_seconds"] == 300
        assert config["input_files"] is None
        assert "llm" not in config  # No LLM settings when both empty

    def test_configure_phase_custom_timeout(self) -> None:
        """Test phase configuration with custom timeout."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            # enabled=False
            mock_confirm.return_value = False
            # timeout=120, model override, temperature override
            mock_prompt.side_effect = ["120", "", ""]

            config = _configure_phase("build", console)

        assert config["enabled"] is False
        assert config["timeout_seconds"] == 120

    def test_configure_phase_uses_phase_default_timeout(self) -> None:
        """Test that phase configuration uses phase-specific default timeout."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            mock_confirm.return_value = True
            # User just hits enter for timeout (uses default), skip LLM
            mock_prompt.side_effect = ["600", "", ""]

            config = _configure_phase("build", console)

        # Build default is 600
        assert config["timeout_seconds"] == 600

    def test_configure_phase_with_llm_settings(self) -> None:
        """Test phase configuration with LLM model and temperature."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            mock_confirm.return_value = True
            # timeout, model override, temperature override
            mock_prompt.side_effect = ["300", "claude-3-opus", "0.3"]

            config = _configure_phase("build", console)

        assert config["llm"] == {"model": "claude-3-opus", "temperature": 0.3}


class TestValidatePhaseSpecialOptions:
    """Tests for validate phase special options."""

    def test_validate_phase_includes_special_options(self) -> None:
        """Test that validate phase config includes special options."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            # Base config: enabled=True
            # Validate special: code_review=True, tests=True, no linters
            mock_confirm.side_effect = [
                True,  # enabled
                True,  # code_review
                True,  # tests
                False,  # add linter commands
            ]
            mock_prompt.side_effect = [
                "900",  # timeout
                "",  # model override (skip)
                "",  # temperature override (skip)
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
        assert config["max_iterations"] == 5
        assert config["triage_mode"] == "auto"
        assert "linter_commands" not in config  # Not added when declined

    def test_validate_phase_custom_special_options(self) -> None:
        """Test validate phase with custom special options."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            mock_confirm.side_effect = [
                True,  # enabled
                False,  # code_review disabled
                True,  # tests
                False,  # add linter commands
            ]
            mock_prompt.side_effect = [
                "1800",  # timeout 30 min
                "",  # model override (skip)
                "",  # temperature override (skip)
                "3",  # max_iterations
                "manual",  # triage_mode
            ]

            config = _configure_phase("validate", console)

        assert config["enable_review"] is False
        assert config["enable_tests"] is True
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
                False,  # add linter commands
            ]
            mock_prompt.side_effect = [
                "10",  # max_iterations
                "hybrid",  # triage_mode
            ]

            config = _configure_validate_phase(console)

        assert config["enable_review"] is True
        assert config["enable_tests"] is False
        assert config["max_iterations"] == 10
        assert config["triage_mode"] == "hybrid"

    def test_validate_phase_with_linter_commands(self) -> None:
        """Test validate phase with linter commands added."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_confirm.side_effect = [
                True,  # code_review
                True,  # tests
                True,  # add linter commands
            ]
            mock_prompt.side_effect = [
                "5",  # max_iterations
                "auto",  # triage_mode
                "ruff check .",  # first linter
                "mypy src/",  # second linter
                "",  # done adding linters
            ]

            config = _configure_validate_phase(console)

        assert config["linter_commands"] == ["ruff check .", "mypy src/"]


class TestInputFileLoop:
    """Tests for input file key=path loop."""

    def test_no_input_files(self) -> None:
        """Test declining to add input files."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False):
            result = _prompt_input_files(console)

        assert result == {}

    def test_single_input_file(self) -> None:
        """Test adding a single input file."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["prd=docs/prd.md", ""]
            result = _prompt_input_files(console)

        assert result == {"prd": "docs/prd.md"}

    def test_multiple_input_files(self) -> None:
        """Test adding multiple input files."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=True),
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
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=True),
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
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=True),
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


class TestDocumentPhaseSpecialOptions:
    """Tests for document phase special options (doc_mappings)."""

    def test_document_phase_no_mappings(self) -> None:
        """Test document phase config when declining to add mappings."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Confirm.ask", return_value=False):
            config = _configure_document_phase(console)

        assert config == {}

    def test_document_phase_with_mappings(self) -> None:
        """Test document phase config with doc_mappings."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "src/core/**/*.py=docs/architecture",
                "src/cli/**/*.py=docs/cli",
                "",  # finish
            ]
            config = _configure_document_phase(console)

        assert "doc_mappings" in config
        assert len(config["doc_mappings"]) == 2
        assert config["doc_mappings"][0]["source_pattern"] == "src/core/**/*.py"
        assert config["doc_mappings"][0]["docs_dir"] == "docs/architecture"
        assert config["doc_mappings"][1]["source_pattern"] == "src/cli/**/*.py"
        assert config["doc_mappings"][1]["docs_dir"] == "docs/cli"

    def test_document_phase_included_in_full_config(self) -> None:
        """Test that document phase includes special options in full config."""
        console = Console(force_terminal=True)

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            # Base config: enabled=True
            # Document special: add_mappings=True
            mock_confirm.side_effect = [
                True,  # enabled
                True,  # add doc_mappings
            ]
            mock_prompt.side_effect = [
                "300",  # timeout
                "",  # model override (skip)
                "",  # temperature override (skip)
                "src/**/*.py=docs/src",  # mapping
                "",  # finish mappings
            ]

            config = _configure_phase("document", console)

        # Base options
        assert config["enabled"] is True
        assert config["timeout_seconds"] == 300

        # Document-specific options
        assert "doc_mappings" in config
        assert len(config["doc_mappings"]) == 1


class TestPromptDocMappings:
    """Tests for _prompt_doc_mappings helper function."""

    def test_single_mapping(self) -> None:
        """Test adding a single doc mapping."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["src/**/*.py=docs/src", ""]
            result = _prompt_doc_mappings(console)

        assert len(result) == 1
        assert result[0]["source_pattern"] == "src/**/*.py"
        assert result[0]["docs_dir"] == "docs/src"

    def test_multiple_mappings(self) -> None:
        """Test adding multiple doc mappings."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = [
                "src/core/**/*.py=docs/architecture",
                "src/cli/**/*.py=docs/cli",
                "src/models/**/*.py=docs/models",
                "",
            ]
            result = _prompt_doc_mappings(console)

        assert len(result) == 3
        assert result[0]["source_pattern"] == "src/core/**/*.py"
        assert result[1]["docs_dir"] == "docs/cli"
        assert result[2]["source_pattern"] == "src/models/**/*.py"

    def test_invalid_format_reprompts(self) -> None:
        """Test that invalid format shows error and reprompts."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = [
                "no_equals_sign",  # invalid
                "src/**/*.py=docs/src",  # valid
                "",
            ]
            result = _prompt_doc_mappings(console)

        assert len(result) == 1
        assert mock_prompt.call_count == 3

    def test_empty_pattern_or_dir_reprompts(self) -> None:
        """Test that empty pattern or dir shows error and reprompts."""
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = [
                "=docs/src",  # empty pattern
                "src/**/*.py=",  # empty dir
                "src/**/*.py=docs/src",  # valid
                "",
            ]
            result = _prompt_doc_mappings(console)

        assert len(result) == 1
        assert result[0]["source_pattern"] == "src/**/*.py"


class TestFullFlow:
    """Tests for full phases configuration flow."""

    def test_full_flow_customize_single_phase(self) -> None:
        """Test full flow customizing a single non-validate phase."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.phases.Confirm.ask") as mock_confirm,
            patch("adw.cli.wizard.phases.Prompt.ask") as mock_prompt,
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            mock_confirm.side_effect = [
                True,  # customize phases
                True,  # enabled
            ]
            mock_prompt.side_effect = [
                "1",  # select plan phase
                "300",  # timeout
                "",  # model override (skip)
                "",  # temperature override (skip)
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
            patch("adw.cli.wizard.phases.nav_confirm_ask", return_value=False),
        ):
            mock_confirm.side_effect = [
                True,  # customize phases
                True,  # enabled
                True,  # code_review
                True,  # tests
                False,  # add linter commands
            ]
            mock_prompt.side_effect = [
                "3",  # select validate phase
                "900",  # timeout
                "",  # model override (skip)
                "",  # temperature override (skip)
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
        assert "linter_commands" not in validate_config


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
