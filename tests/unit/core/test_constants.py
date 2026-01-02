"""Tests for core constants.

This module tests the PHASE_SEQUENCE constant that defines the fixed
order of phase execution in the ADW pipeline.
"""



class TestPhaseSequence:
    """Tests for PHASE_SEQUENCE constant."""

    def test_phase_sequence_order(self) -> None:
        """Test that phase sequence is in correct order.

        The sequence must be: Plan → Build → Verify → Validate → Document
        """
        from adw.core.constants import PHASE_SEQUENCE

        assert PHASE_SEQUENCE == ("plan", "build", "verify", "validate", "document")

    def test_phase_sequence_immutable(self) -> None:
        """Test that phase sequence cannot be modified.

        PHASE_SEQUENCE must be a tuple to prevent accidental modification.
        """
        from adw.core.constants import PHASE_SEQUENCE

        assert isinstance(PHASE_SEQUENCE, tuple)

    def test_phase_sequence_length(self) -> None:
        """Test that phase sequence has exactly 5 phases."""
        from adw.core.constants import PHASE_SEQUENCE

        assert len(PHASE_SEQUENCE) == 5

    def test_phase_sequence_no_duplicates(self) -> None:
        """Test that phase sequence has no duplicate phases."""
        from adw.core.constants import PHASE_SEQUENCE

        assert len(PHASE_SEQUENCE) == len(set(PHASE_SEQUENCE))

    def test_phase_sequence_all_lowercase(self) -> None:
        """Test that all phase names are lowercase."""
        from adw.core.constants import PHASE_SEQUENCE

        for phase in PHASE_SEQUENCE:
            assert phase == phase.lower(), f"Phase '{phase}' should be lowercase"

    def test_phase_sequence_all_strings(self) -> None:
        """Test that all phases are strings."""
        from adw.core.constants import PHASE_SEQUENCE

        for phase in PHASE_SEQUENCE:
            assert isinstance(phase, str), f"Phase {phase!r} should be a string"
