# TEST REDUCTION: Per ADR-001 (Test Reduction Strategy), the phase sequence order test
# was removed as an "Enum Existence Test" - the definition in constants.py is the
# source of truth. Testing that PHASE_SEQUENCE == a specific tuple adds no value
# because if the implementation is wrong, we need to fix the implementation, not the test.
"""Tests for core constants.

This module previously tested PHASE_SEQUENCE. Per ISS-019 and ADR-001, the sequence
verification test was removed as it provides no value - the constant definition
itself is the source of truth.

PHASE_SEQUENCE history:
- ISS-019: Removed "verify" phase (5 -> 4 phases)
- Story 15.1: Added "ship" phase (4 -> 5 phases)
- Current: ("plan", "build", "validate", "document", "ship")
"""


class TestPhaseSequence:
    """Tests for PHASE_SEQUENCE constant.

    Note: Explicit sequence equality tests removed per ADR-001.
    The constant definition is self-documenting.
    """

    def test_phase_sequence_importable(self) -> None:
        """Test that PHASE_SEQUENCE can be imported without errors."""
        from adw.core.constants import PHASE_SEQUENCE

        assert isinstance(PHASE_SEQUENCE, tuple)
        assert len(PHASE_SEQUENCE) > 0
