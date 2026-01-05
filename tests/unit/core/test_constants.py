# TEST REDUCTION: Removed 5 trivial constant tests (immutable, length, no_duplicates,
# all_lowercase, all_strings). Kept only test_phase_sequence_order which verifies
# business-critical phase ordering. The removed tests added no value - if the order
# assertion passes, the constant is correct; type/format properties are implementation details.
"""Tests for core constants.

This module tests the PHASE_SEQUENCE constant that defines the fixed
order of phase execution in the ADW pipeline.
"""


class TestPhaseSequence:
    """Tests for PHASE_SEQUENCE constant."""

    def test_phase_sequence_order(self) -> None:
        """Test that phase sequence is in correct order.

        The sequence must be: Plan -> Build -> Verify -> Validate -> Document
        """
        from adw.core.constants import PHASE_SEQUENCE

        assert PHASE_SEQUENCE == ("plan", "build", "verify", "validate", "document")
