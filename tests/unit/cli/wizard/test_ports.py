"""Tests for wizard port configuration step.

Tests the port validation, range overlap detection, common port conflict
detection, and interactive prompt flow for the ports configuration step.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.console import Console

from adw.cli.wizard.ports import (
    COMMON_PORTS,
    DEFAULT_BACKEND_PORT,
    DEFAULT_FRONTEND_PORT,
    DEFAULT_MAX_CONCURRENT,
    PortsStepHandler,
    check_port_overlap,
    check_range_conflicts,
    is_common_port,
    run_ports_step,
    validate_port,
)
from adw.models.wizard import WizardState


class TestPortValidation:
    """Tests for validate_port function."""

    @pytest.mark.parametrize(
        "port_str,expected_valid,expected_result",
        [
            ("9100", True, 9100),
            ("1", True, 1),
            ("65535", True, 65535),
            ("1024", True, 1024),
            ("80", True, 80),
        ],
    )
    def test_valid_ports(
        self, port_str: str, expected_valid: bool, expected_result: int
    ) -> None:
        """Test validation of valid port numbers."""
        is_valid, result = validate_port(port_str)
        assert is_valid == expected_valid
        assert result == expected_result

    @pytest.mark.parametrize(
        "port_str,expected_error_contains",
        [
            ("0", "between"),
            ("65536", "between"),
            ("-1", "between"),  # -1 parses as integer, fails range check
            ("abc", "number"),
            ("12.5", "number"),
            ("", "number"),
            ("  ", "number"),
        ],
    )
    def test_invalid_ports(self, port_str: str, expected_error_contains: str) -> None:
        """Test validation of invalid port numbers."""
        is_valid, result = validate_port(port_str)
        assert is_valid is False
        assert isinstance(result, str)
        assert expected_error_contains in result.lower()


class TestPortRangeOverlap:
    """Tests for check_port_overlap function."""

    def test_no_overlap_standard_defaults(self) -> None:
        """Test that default ports don't overlap."""
        assert not check_port_overlap(9100, 9200, max_concurrent=10)

    def test_no_overlap_with_gap(self) -> None:
        """Test ranges with gap between them don't overlap."""
        # Backend: 9100-9109, Frontend: 9200-9209
        assert not check_port_overlap(9100, 9200, max_concurrent=10)

    def test_overlap_adjacent_ranges(self) -> None:
        """Test overlap when frontend starts right after backend ends."""
        # Backend: 9100-9109, Frontend: 9109-9118 (overlap at 9109)
        assert check_port_overlap(9100, 9109, max_concurrent=10)

    def test_overlap_contained_range(self) -> None:
        """Test overlap when one range is contained in another."""
        # Backend: 9100-9109, Frontend: 9105-9114
        assert check_port_overlap(9100, 9105, max_concurrent=10)

    def test_overlap_reversed_order(self) -> None:
        """Test overlap detection works regardless of which port is higher."""
        # Frontend before backend: Frontend: 9100-9109, Backend: 9105-9114
        assert check_port_overlap(9105, 9100, max_concurrent=10)

    def test_no_overlap_just_touching(self) -> None:
        """Test no overlap when ranges are exactly adjacent (no actual overlap)."""
        # Backend: 9100-9109, Frontend: 9110-9119 (touching but not overlapping)
        assert not check_port_overlap(9100, 9110, max_concurrent=10)


class TestCommonPortDetection:
    """Tests for common port detection functions."""

    @pytest.mark.parametrize(
        "port,expected",
        [
            (3000, True),
            (3001, True),
            (5000, True),
            (8000, True),
            (8080, True),
            (8443, True),
            (8888, True),
            (9100, False),
            (9200, False),
            (80, False),
            (443, False),
        ],
    )
    def test_is_common_port(self, port: int, expected: bool) -> None:
        """Test is_common_port detection."""
        assert is_common_port(port) == expected

    def test_check_range_conflicts_with_conflicts(self) -> None:
        """Test range conflict detection finds common ports in range."""
        # Range 2995-3004 includes 3000 and 3001
        conflicts = check_range_conflicts(2995, max_concurrent=10)
        assert 3000 in conflicts
        assert 3001 in conflicts

    def test_check_range_conflicts_no_conflicts(self) -> None:
        """Test range conflict detection returns empty for safe range."""
        # Range 9100-9109 has no common ports
        conflicts = check_range_conflicts(9100, max_concurrent=10)
        assert len(conflicts) == 0

    def test_check_range_conflicts_sorted_output(self) -> None:
        """Test that conflicts are returned sorted."""
        conflicts = check_range_conflicts(2995, max_concurrent=10)
        assert conflicts == sorted(conflicts)

    def test_common_ports_set_completeness(self) -> None:
        """Test that COMMON_PORTS contains expected ports."""
        expected = {3000, 3001, 5000, 8000, 8080, 8443, 8888}
        assert expected == COMMON_PORTS


class TestRunPortsStepDefaults:
    """Tests for run_ports_step when using defaults."""

    def test_decline_configuration_uses_defaults(self) -> None:
        """Test that declining port configuration uses default values."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.ports.Confirm.ask", return_value=False):
            result = run_ports_step(state, console)

        assert result["port_config_custom"] is False
        assert result["backend_port_start"] == DEFAULT_BACKEND_PORT
        assert result["frontend_port_start"] == DEFAULT_FRONTEND_PORT


class TestRunPortsStepCustomConfiguration:
    """Tests for run_ports_step with custom configuration."""

    def test_accept_configuration_with_valid_ports(self) -> None:
        """Test custom port configuration with valid ports."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.ports.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.ports.Prompt.ask") as mock_prompt,
        ):
            # Backend port, frontend port
            mock_prompt.side_effect = ["9500", "9600"]
            result = run_ports_step(state, console)

        assert result["port_config_custom"] is True
        assert result["backend_port_start"] == 9500
        assert result["frontend_port_start"] == 9600

    def test_invalid_port_reprompts(self) -> None:
        """Test that invalid port input reprompts user."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.ports.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.ports.Prompt.ask") as mock_prompt,
        ):
            # First invalid, then valid for both backend and frontend
            mock_prompt.side_effect = ["abc", "9500", "9600"]
            result = run_ports_step(state, console)

        assert result["backend_port_start"] == 9500
        # Verify prompt was called at least 3 times (invalid + 2 valid)
        assert mock_prompt.call_count >= 3

    def test_overlap_triggers_reprompt(self) -> None:
        """Test that overlapping ranges trigger reprompt for frontend."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.ports.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.ports.Prompt.ask") as mock_prompt,
        ):
            # Backend 9100, Frontend 9105 (overlaps), then adjusted 9200
            mock_prompt.side_effect = ["9100", "9105", "9200"]
            result = run_ports_step(state, console)

        assert result["backend_port_start"] == 9100
        # Frontend should be the adjusted value after overlap warning
        assert result["frontend_port_start"] == 9200
        # Should have prompted 3 times: backend, overlapping frontend, adjusted frontend
        assert mock_prompt.call_count == 3

    def test_overlap_loops_until_valid(self) -> None:
        """Test that overlap check loops until user provides non-overlapping port."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.ports.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.ports.Prompt.ask") as mock_prompt,
        ):
            # Backend 9100, then three overlapping frontend values, finally valid
            # With DEFAULT_MAX_CONCURRENT=15, overlap occurs when frontend < 9115
            mock_prompt.side_effect = ["9100", "9105", "9106", "9110", "9200"]
            result = run_ports_step(state, console)

        assert result["backend_port_start"] == 9100
        # Frontend should be the final non-overlapping value
        assert result["frontend_port_start"] == 9200
        # Should have prompted 5 times: backend + 4 frontend attempts
        assert mock_prompt.call_count == 5


class TestPortsStepHandler:
    """Tests for PortsStepHandler class."""

    def test_handler_execute_delegates_to_run_ports_step(self) -> None:
        """Test handler execute method delegates correctly."""
        handler = PortsStepHandler()
        state = WizardState()
        console = Console(force_terminal=True)

        with patch("adw.cli.wizard.ports.Confirm.ask", return_value=False):
            result = handler.execute(state, console)

        assert result["port_config_custom"] is False
        assert result["backend_port_start"] == DEFAULT_BACKEND_PORT
        assert result["frontend_port_start"] == DEFAULT_FRONTEND_PORT


class TestStateIntegration:
    """Tests for integration with wizard state."""

    def test_config_stored_via_flow_controller_pattern(self) -> None:
        """Test that config can be stored using flow controller pattern."""
        console = Console(force_terminal=True)
        state = WizardState()

        with patch("adw.cli.wizard.ports.Confirm.ask", return_value=False):
            config = run_ports_step(state, console)

        # Simulate what flow controller does
        state.update_config("ports", config)
        state.mark_completed("ports")

        # Verify storage
        stored = state.get_step_config("ports")
        assert stored["port_config_custom"] is False
        assert stored["backend_port_start"] == DEFAULT_BACKEND_PORT
        assert "ports" in state.completed_steps

    def test_full_flow_returns_complete_config(self) -> None:
        """Test that full flow returns all expected configuration keys."""
        console = Console(force_terminal=True)
        state = WizardState()

        with (
            patch("adw.cli.wizard.ports.Confirm.ask", return_value=True),
            patch("adw.cli.wizard.ports.Prompt.ask") as mock_prompt,
        ):
            mock_prompt.side_effect = ["9300", "9400"]
            result = run_ports_step(state, console)

        # Verify all keys present
        assert "port_config_custom" in result
        assert "backend_port_start" in result
        assert "frontend_port_start" in result

        # Verify values
        assert result["port_config_custom"] is True
        assert result["backend_port_start"] == 9300
        assert result["frontend_port_start"] == 9400


class TestConstants:
    """Tests for module constants."""

    def test_default_ports_match_worktree_module(self) -> None:
        """Test that default port values are sensible."""
        # Defaults should match worktree/ports.py conventions
        assert DEFAULT_BACKEND_PORT == 9100
        assert DEFAULT_FRONTEND_PORT == 9200

    def test_max_concurrent_default(self) -> None:
        """Test default max_concurrent value matches worktree module."""
        # Should match the canonical DEFAULT_MAX_CONCURRENT from worktree/ports.py
        assert DEFAULT_MAX_CONCURRENT == 15

    def test_default_ranges_dont_overlap(self) -> None:
        """Test that default port ranges don't overlap."""
        assert not check_port_overlap(
            DEFAULT_BACKEND_PORT,
            DEFAULT_FRONTEND_PORT,
            DEFAULT_MAX_CONCURRENT,
        )
